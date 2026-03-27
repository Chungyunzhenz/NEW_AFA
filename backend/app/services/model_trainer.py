"""Model training logic for Prophet, SARIMA, and XGBoost.

Trains individual time-series models, serialises them to disk under the
``trained_models/`` directory, and registers model metadata (artifact path,
evaluation metrics) in the ``model_registry`` database table.

Usage::

    from app.database import SessionLocal
    from app.services.model_trainer import ModelTrainer

    trainer = ModelTrainer()
    result = trainer.train_single_model(
        model_type="prophet",
        train_df=train_df,
        val_df=val_df,
        crop_config=crop_cfg,
        target_metric="price_avg",
        region_info={"region_type": "national", "region_id": 0},
        db=db,
    )
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import pickle
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ..config import settings
from ..models.model_registry import ModelRegistry
from .model_evaluator import EvaluationMetrics, ModelEvaluator

logger = logging.getLogger(__name__)

# Suppress verbose library output during training.
warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MODEL_TYPES = ("prophet", "sarima", "xgboost", "lightgbm")
ARTIFACT_DIR = Path(settings.MODEL_DIR)


def _ensure_artifact_dir() -> Path:
    """Create the artifact directory tree if it does not exist."""
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_DIR


# ---------------------------------------------------------------------------
# Individual model helpers
# ---------------------------------------------------------------------------

def _train_prophet(
    train_df: pd.DataFrame,
    config: Dict[str, Any],
    target_metric: str,
) -> Any:
    """Fit a Prophet model on *train_df* (columns ``ds``, ``y``, and optional
    regressors).

    Returns the fitted model object.
    """
    from prophet import Prophet  # lazy import — heavy dependency

    seasonality_mode = config.get("seasonality", {}).get(
        "seasonality_mode", "additive"
    )
    prophet_cfg = config.get("prophet_config", {})

    model = Prophet(
        yearly_seasonality=prophet_cfg.get("yearly_seasonality", True),
        weekly_seasonality=prophet_cfg.get("weekly_seasonality", False),
        daily_seasonality=False,
        seasonality_mode=seasonality_mode,
        changepoint_prior_scale=prophet_cfg.get("changepoint_prior_scale", 0.05),
    )

    # Only use key weather/typhoon regressors (not all columns).
    # Too many regressors cause Prophet to output flat predictions.
    allowed_regressors = {
        "temp_avg", "rainfall_mm", "is_typhoon_month",
        "typhoon_intensity_max", "post_typhoon_1m",
    }
    regressor_cols = [
        c for c in train_df.columns
        if c in allowed_regressors and train_df[c].notna().any()
    ]
    for col in regressor_cols:
        model.add_regressor(col)

    with _suppress_stdout():
        model.fit(train_df[["ds", "y"] + regressor_cols])

    return model


def _predict_prophet(
    model: Any,
    future_df: pd.DataFrame,
) -> pd.DataFrame:
    """Generate predictions from a fitted Prophet model.

    Returns a DataFrame with ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
    """
    forecast = model.predict(future_df)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()


def _train_sarima(
    train_df: pd.DataFrame,
    config: Dict[str, Any],
    target_metric: str,
) -> Any:
    """Fit a SARIMA model using auto-order selection via pmdarima.

    Returns the fitted model object.
    """
    import pmdarima as pm  # lazy import

    sarima_cfg = config.get("sarima_config", {})
    seasonal_period = sarima_cfg.get("seasonal_period", 12)
    max_p = sarima_cfg.get("max_p", 3)
    max_q = sarima_cfg.get("max_q", 3)
    max_d = sarima_cfg.get("max_d", 2)

    y = train_df["y"].values

    model = pm.auto_arima(
        y,
        seasonal=True,
        m=seasonal_period,
        max_p=max_p,
        max_d=max_d,
        max_q=max_q,
        max_P=2,
        max_D=1,
        max_Q=2,
        stepwise=True,
        suppress_warnings=True,
        error_action="ignore",
        trace=False,
    )
    return model


def _predict_sarima(
    model: Any,
    n_periods: int,
    future_dates: pd.DatetimeIndex,
) -> pd.DataFrame:
    """Generate predictions from a fitted SARIMA model.

    Returns a DataFrame with ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
    """
    forecast, conf_int = model.predict(
        n_periods=n_periods, return_conf_int=True, alpha=0.1
    )
    return pd.DataFrame(
        {
            "ds": future_dates[:n_periods],
            "yhat": forecast,
            "yhat_lower": conf_int[:, 0],
            "yhat_upper": conf_int[:, 1],
        }
    )


def _build_xgb_features(
    df: pd.DataFrame,
    config: Dict[str, Any],
) -> pd.DataFrame:
    """Create lag / rolling / calendar features for XGBoost.

    Operates on a copy so the original DataFrame is not mutated.
    """
    xgb_cfg = config.get("xgboost_config", {})
    lag_features: List[int] = xgb_cfg.get("lag_features", [1, 2, 3, 12])
    rolling_windows: List[int] = xgb_cfg.get("rolling_windows", [3, 6, 12])

    out = df.copy()

    # Lag features
    for lag in lag_features:
        out[f"lag_{lag}"] = out["y"].shift(lag)

    # Rolling statistics
    for win in rolling_windows:
        out[f"roll_mean_{win}"] = out["y"].shift(1).rolling(window=win, min_periods=1).mean()
        out[f"roll_std_{win}"] = out["y"].shift(1).rolling(window=win, min_periods=1).std()

    # Calendar features
    if "ds" in out.columns:
        ds = pd.to_datetime(out["ds"])
        out["month"] = ds.dt.month
        out["quarter"] = ds.dt.quarter
        out["year"] = ds.dt.year

        # Seasonal sine / cosine encoding
        if xgb_cfg.get("custom_seasonal_features", False):
            out["month_sin"] = np.sin(2 * np.pi * ds.dt.month / 12)
            out["month_cos"] = np.cos(2 * np.pi * ds.dt.month / 12)

    return out


def _train_xgboost(
    train_df: pd.DataFrame,
    config: Dict[str, Any],
    target_metric: str,
) -> Tuple[Any, List[str]]:
    """Fit an XGBRegressor on the feature-engineered training data.

    Returns ``(fitted_model, feature_columns)``.
    """
    import xgboost as xgb  # lazy import

    featured = _build_xgb_features(train_df, config)

    # Identify feature columns (everything except ds, y, and any all-NaN cols).
    exclude = {"ds", "y"}
    feature_cols = [
        c for c in featured.columns
        if c not in exclude and featured[c].notna().any()
    ]

    # Drop rows with NaN in feature columns (early rows affected by lags).
    clean = featured.dropna(subset=feature_cols + ["y"])

    X = clean[feature_cols].values
    y = clean["y"].values

    model = xgb.XGBRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        verbosity=0,
    )
    model.fit(X, y)
    return model, feature_cols


def _predict_xgboost(
    model: Any,
    feature_cols: List[str],
    full_history_df: pd.DataFrame,
    n_periods: int,
    future_dates: pd.DatetimeIndex,
    config: Dict[str, Any],
) -> pd.DataFrame:
    """Generate multi-step-ahead predictions from a fitted XGBRegressor.

    Uses an iterative (recursive) strategy: each predicted value is fed back
    as a lag feature for the next step.

    Returns a DataFrame with ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
    """
    history = full_history_df.copy()
    predictions: List[float] = []

    for step in range(n_periods):
        future_row_ds = future_dates[step] if step < len(future_dates) else None
        # Append a placeholder row for the next period.
        new_row = pd.DataFrame({"ds": [future_row_ds], "y": [np.nan]})
        history = pd.concat([history, new_row], ignore_index=True)

        featured = _build_xgb_features(history, config)
        last_row = featured.iloc[[-1]]

        # Ensure required columns exist (fill missing with 0).
        for col in feature_cols:
            if col not in last_row.columns:
                last_row[col] = 0.0

        X = last_row[feature_cols].fillna(0).values
        pred = float(model.predict(X)[0])
        predictions.append(pred)

        # Feed back the predicted value for subsequent lags.
        history.iloc[-1, history.columns.get_loc("y")] = pred

    yhat = np.array(predictions)

    # Approximate confidence intervals using residual-based heuristic.
    # With no bootstrapping in XGBoost we use +/-15% of the absolute
    # predicted value, floored at a small positive value.
    margin = np.maximum(np.abs(yhat) * 0.15, 1.0)

    return pd.DataFrame(
        {
            "ds": future_dates[:n_periods],
            "yhat": yhat,
            "yhat_lower": yhat - margin,
            "yhat_upper": yhat + margin,
        }
    )


def _train_lightgbm(
    train_df: pd.DataFrame,
    config: Dict[str, Any],
    target_metric: str,
) -> Tuple[Any, List[str]]:
    """Fit a LightGBM regressor. Uses the same features as XGBoost."""
    import lightgbm as lgb

    featured = _build_xgb_features(train_df, config)
    exclude = {"ds", "y"}
    feature_cols = [
        c for c in featured.columns
        if c not in exclude and featured[c].notna().any()
    ]
    clean = featured.dropna(subset=feature_cols + ["y"])

    X = clean[feature_cols].values
    y = clean["y"].values

    model = lgb.LGBMRegressor(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        verbosity=-1,
    )
    model.fit(X, y)
    return model, feature_cols


def _predict_lightgbm(
    model: Any,
    feature_cols: List[str],
    full_history_df: pd.DataFrame,
    n_periods: int,
    future_dates: pd.DatetimeIndex,
    config: Dict[str, Any],
) -> pd.DataFrame:
    """Generate predictions from LightGBM. Same recursive strategy as XGBoost."""
    return _predict_xgboost(model, feature_cols, full_history_df, n_periods, future_dates, config)


# ---------------------------------------------------------------------------
# Stdout suppression context manager (for Prophet)
# ---------------------------------------------------------------------------
import contextlib
import io


@contextlib.contextmanager
def _suppress_stdout():
    """Temporarily suppress stdout (Prophet logs to stdout by default)."""
    new_out = io.StringIO()
    with contextlib.redirect_stdout(new_out):
        yield


# ---------------------------------------------------------------------------
# Main trainer class
# ---------------------------------------------------------------------------

class ModelTrainer:
    """Train individual forecasting models and persist artifacts."""

    def __init__(self) -> None:
        self.evaluator = ModelEvaluator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def train_single_model(
        self,
        model_type: str,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        crop_config: Dict[str, Any],
        target_metric: str,
        region_info: Dict[str, Any],
        db: Session,
        crop_id: Optional[int] = None,
        forecast_horizon: int = 6,
    ) -> Dict[str, Any]:
        """Train one model, evaluate it, save artifact, and register in DB.

        Parameters
        ----------
        model_type:
            One of ``"prophet"``, ``"sarima"``, ``"xgboost"``.
        train_df:
            Training DataFrame with at least ``ds`` and ``y`` columns.
        val_df:
            Validation DataFrame with ``ds`` and ``y``.
        crop_config:
            The crop configuration dict (loaded from JSON).
        target_metric:
            ``"price_avg"`` or ``"volume"``.
        region_info:
            ``{"region_type": str, "region_id": int}``.
        db:
            Active SQLAlchemy session.
        crop_id:
            The ``crops.id`` to associate with the model registry row.
        forecast_horizon:
            Number of future periods to forecast (months).

        Returns
        -------
        dict
            ``{"model_type", "metrics", "predictions", "artifact_path",
            "model_object", "feature_cols"}``
        """
        model_type = model_type.lower().strip()
        if model_type not in MODEL_TYPES:
            raise ValueError(
                f"Unknown model_type '{model_type}'. Must be one of {MODEL_TYPES}."
            )

        logger.info(
            "Training %s for crop_id=%s, metric=%s, region=%s ...",
            model_type,
            crop_id,
            target_metric,
            region_info,
        )

        result: Dict[str, Any] = {
            "model_type": model_type,
            "metrics": None,
            "predictions": None,
            "artifact_path": None,
            "model_object": None,
            "feature_cols": None,
        }

        try:
            # ---- Train ----
            model_obj = None
            feature_cols: Optional[List[str]] = None

            if model_type == "prophet":
                model_obj = _train_prophet(train_df, crop_config, target_metric)
            elif model_type == "sarima":
                model_obj = _train_sarima(train_df, crop_config, target_metric)
            elif model_type == "xgboost":
                model_obj, feature_cols = _train_xgboost(
                    train_df, crop_config, target_metric
                )
            elif model_type == "lightgbm":
                model_obj, feature_cols = _train_lightgbm(
                    train_df, crop_config, target_metric
                )

            result["model_object"] = model_obj
            result["feature_cols"] = feature_cols

            # ---- Evaluate on validation set ----
            metrics = self._evaluate_model(
                model_type, model_obj, feature_cols, train_df, val_df,
                crop_config, target_metric,
            )
            result["metrics"] = metrics

            # ---- Generate future predictions ----
            full_df = pd.concat([train_df, val_df], ignore_index=True)
            predictions = self._generate_predictions(
                model_type, model_obj, feature_cols, full_df,
                crop_config, forecast_horizon,
            )
            result["predictions"] = predictions

            # ---- Extract feature importance (XGBoost) ----
            feature_importance_json = None
            if model_type in ("xgboost", "lightgbm") and hasattr(model_obj, 'feature_importances_'):
                fi = dict(zip(feature_cols, model_obj.feature_importances_.tolist()))
                # Sort and keep top 20
                fi_sorted = dict(sorted(fi.items(), key=lambda x: x[1], reverse=True)[:20])
                feature_importance_json = json.dumps(fi_sorted)

            # ---- Save artifact ----
            artifact_path = self._save_artifact(
                model_type, model_obj, feature_cols, crop_config,
                crop_id, target_metric, region_info,
            )
            result["artifact_path"] = artifact_path

            # ---- Register in DB ----
            self._register_model(
                db=db,
                crop_id=crop_id,
                region_info=region_info,
                target_metric=target_metric,
                model_type=model_type,
                artifact_path=artifact_path,
                metrics=metrics,
                training_rows=len(train_df),
                feature_importance_json=feature_importance_json,
            )

            logger.info(
                "Training complete for %s: MAE=%.4f, RMSE=%.4f, MAPE=%.2f%%.",
                model_type,
                metrics.mae,
                metrics.rmse,
                metrics.mape,
            )

        except Exception:
            logger.exception("Failed to train %s model.", model_type)

        return result

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------
    def _evaluate_model(
        self,
        model_type: str,
        model_obj: Any,
        feature_cols: Optional[List[str]],
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        crop_config: Dict[str, Any],
        target_metric: str,
    ) -> EvaluationMetrics:
        """Produce predictions on *val_df* and compute metrics."""
        y_true = val_df["y"].values
        n_val = len(val_df)
        val_dates = pd.to_datetime(val_df["ds"])

        if model_type == "prophet":
            future_df = val_df.copy()
            pred_df = _predict_prophet(model_obj, future_df)
            y_pred = pred_df["yhat"].values[:n_val]

        elif model_type == "sarima":
            forecast, _ = model_obj.predict(
                n_periods=n_val, return_conf_int=True, alpha=0.1
            )
            y_pred = forecast[:n_val]

        elif model_type == "xgboost":
            pred_df = _predict_xgboost(
                model_obj, feature_cols, train_df, n_val,
                pd.DatetimeIndex(val_dates), crop_config,
            )
            y_pred = pred_df["yhat"].values[:n_val]

        elif model_type == "lightgbm":
            pred_df = _predict_lightgbm(
                model_obj, feature_cols, train_df, n_val,
                pd.DatetimeIndex(val_dates), crop_config,
            )
            y_pred = pred_df["yhat"].values[:n_val]
        else:
            raise ValueError(f"Unknown model_type: {model_type}")

        return self.evaluator.compute_metrics(y_true, y_pred)

    # ------------------------------------------------------------------
    # Prediction generation
    # ------------------------------------------------------------------
    def _generate_predictions(
        self,
        model_type: str,
        model_obj: Any,
        feature_cols: Optional[List[str]],
        full_df: pd.DataFrame,
        crop_config: Dict[str, Any],
        horizon: int,
    ) -> pd.DataFrame:
        """Generate *horizon* months of future predictions."""
        last_date = pd.to_datetime(full_df["ds"]).max()
        future_dates = pd.date_range(
            start=last_date + pd.DateOffset(months=1),
            periods=horizon,
            freq="MS",
        )

        if model_type == "prophet":
            future_df = pd.DataFrame({"ds": future_dates})
            # Fill regressor columns with historical same-month averages
            # instead of last known value (which causes flat predictions).
            allowed_regressors = {
                "temp_avg", "rainfall_mm", "is_typhoon_month",
                "typhoon_intensity_max", "post_typhoon_1m",
            }
            regressor_cols = [
                c for c in full_df.columns if c in allowed_regressors
            ]
            if regressor_cols:
                hist = full_df.copy()
                hist["_month"] = pd.to_datetime(hist["ds"]).dt.month
                monthly_avg = hist.groupby("_month")[regressor_cols].mean()
                for col in regressor_cols:
                    future_df[col] = [
                        monthly_avg.loc[d.month, col]
                        if d.month in monthly_avg.index else 0.0
                        for d in future_dates
                    ]

            return _predict_prophet(model_obj, future_df)

        elif model_type == "sarima":
            return _predict_sarima(model_obj, horizon, future_dates)

        elif model_type == "xgboost":
            return _predict_xgboost(
                model_obj, feature_cols, full_df, horizon,
                future_dates, crop_config,
            )

        elif model_type == "lightgbm":
            return _predict_lightgbm(
                model_obj, feature_cols, full_df, horizon,
                future_dates, crop_config,
            )

        raise ValueError(f"Unknown model_type: {model_type}")

    # ------------------------------------------------------------------
    # Artifact persistence
    # ------------------------------------------------------------------
    @staticmethod
    def _save_artifact(
        model_type: str,
        model_obj: Any,
        feature_cols: Optional[List[str]],
        crop_config: Dict[str, Any],
        crop_id: Optional[int],
        target_metric: str,
        region_info: Dict[str, Any],
    ) -> str:
        """Serialise the model to disk and return the relative artifact path."""
        _ensure_artifact_dir()

        crop_key = crop_config.get("crop_key", str(crop_id))
        region_type = region_info.get("region_type", "unknown")
        region_id = region_info.get("region_id", 0)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        filename = (
            f"{crop_key}_{target_metric}_{region_type}_{region_id}"
            f"_{model_type}_{timestamp}.pkl"
        )
        filepath = ARTIFACT_DIR / filename

        payload = {
            "model_type": model_type,
            "model_object": model_obj,
            "feature_cols": feature_cols,
            "crop_config_key": crop_key,
            "target_metric": target_metric,
            "region_info": region_info,
            "saved_at": timestamp,
        }

        with open(filepath, "wb") as f:
            pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

        rel_path = str(filepath)
        logger.info("Saved model artifact: %s", rel_path)
        return rel_path

    @staticmethod
    def load_artifact(artifact_path: str) -> Dict[str, Any]:
        """Load a previously saved model artifact from disk."""
        with open(artifact_path, "rb") as f:
            payload = pickle.load(f)
        logger.info("Loaded model artifact: %s", artifact_path)
        return payload

    # ------------------------------------------------------------------
    # Model registry
    # ------------------------------------------------------------------
    @staticmethod
    def _register_model(
        db: Session,
        crop_id: Optional[int],
        region_info: Dict[str, Any],
        target_metric: str,
        model_type: str,
        artifact_path: str,
        metrics: EvaluationMetrics,
        training_rows: int,
        feature_importance_json: Optional[str] = None,
    ) -> ModelRegistry:
        """Upsert a model-registry row: deactivate previous entries for the
        same (crop_id, region, metric, model_type) and insert a new active
        record.
        """
        region_type = region_info.get("region_type", "unknown")
        region_id = region_info.get("region_id", 0)

        # Deactivate previous versions.
        db.query(ModelRegistry).filter(
            ModelRegistry.crop_id == crop_id,
            ModelRegistry.region_type == region_type,
            ModelRegistry.region_id == region_id,
            ModelRegistry.target_metric == target_metric,
            ModelRegistry.model_type == model_type,
            ModelRegistry.is_active == True,  # noqa: E712
        ).update({"is_active": False}, synchronize_session="fetch")

        entry = ModelRegistry(
            crop_id=crop_id,
            region_type=region_type,
            region_id=region_id,
            target_metric=target_metric,
            model_type=model_type,
            artifact_path=artifact_path,
            mse=metrics.mse,
            mae=metrics.mae,
            rmse=metrics.rmse,
            r_squared=metrics.r_squared,
            mape=metrics.mape,
            trained_at=datetime.utcnow(),
            training_rows=training_rows,
            is_active=True,
            feature_importance_json=feature_importance_json,
        )
        db.add(entry)
        db.flush()

        logger.info(
            "Registered model: %s (crop_id=%s, metric=%s, region=%s/%s) -> id=%d",
            model_type,
            crop_id,
            target_metric,
            region_type,
            region_id,
            entry.id,
        )
        return entry
