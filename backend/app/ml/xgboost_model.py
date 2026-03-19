"""
xgboost_model.py - XGBoost wrapper for the Taiwan Agricultural Product
Prediction System.

Inherits from ``BasePredictor``.  Integrates tightly with
``feature_engineering.py`` to build a rich feature matrix from monthly
time-series data.  Confidence intervals are estimated via quantile
regression (two auxiliary models for the lower and upper bounds).
"""

from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import numpy as np
import logging

from .base_model import BasePredictor
from .feature_engineering import (
    build_features,
    build_future_features,
    get_feature_columns,
)

logger = logging.getLogger(__name__)


class XGBoostPredictor(BasePredictor):
    """XGBoost-based time-series forecaster with quantile confidence bands.

    Configuration keys read from ``crop_config``:

    - ``lag_features`` : list[int]   (default ``[1, 2, 3, 6, 12]``)
    - ``rolling_windows`` : list[int]  (default ``[3, 6, 12]``)
    - ``peak_months`` : list[int]
    - ``xgb_params`` : dict  — raw XGBoost parameters forwarded to
      ``xgb.XGBRegressor`` (e.g. ``learning_rate``, ``max_depth``, etc.)
    - ``n_estimators`` : int  (default 500)
    - ``early_stopping_rounds`` : int  (default 30)
    - ``confidence_level`` : float  (default 0.80)
    - ``n_bootstrap`` : int  (default 100) — bootstrap iterations for
      interval estimation when quantile regression is unavailable.
    """

    def __init__(
        self,
        crop_config: Dict[str, Any],
        target_metric: str = "avg_price",
    ) -> None:
        super().__init__(crop_config, target_metric)
        self._model_lower: Any = None
        self._model_upper: Any = None
        self._feature_cols: List[str] = []
        self.feature_importance: Optional[pd.DataFrame] = None
        self._weather_df: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    def get_model_type(self) -> str:
        return "xgboost"

    def fit(
        self,
        train_df: pd.DataFrame,
        weather_df: Optional[pd.DataFrame] = None,
    ) -> None:
        """Build features and train XGBoost (median + quantile models).

        Parameters
        ----------
        train_df : pd.DataFrame
            Must contain ``ds`` (datetime) and ``y`` (numeric).
        weather_df : pd.DataFrame, optional
            Monthly weather data to merge during feature engineering.
        """
        try:
            import xgboost as xgb
        except ImportError:
            raise ImportError(
                "xgboost is not installed.  "
                "Install it with: pip install xgboost"
            )

        cfg = self.crop_config
        self._weather_df = weather_df

        # --- Feature engineering ---
        df = train_df[["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds").reset_index(drop=True)

        featured = build_features(
            df,
            crop_config=cfg,
            weather_df=weather_df,
            drop_na=True,
        )

        if featured.empty:
            raise ValueError(
                "Feature-engineered DataFrame is empty. "
                "Check that the input has enough rows to satisfy lag requirements."
            )

        self._feature_cols = get_feature_columns(featured)
        X = featured[self._feature_cols].values
        y = featured["y"].values.astype(float)

        # --- Shared hyper-parameters ---
        n_estimators: int = cfg.get("n_estimators", 500)
        early_stopping: int = cfg.get("early_stopping_rounds", 30)
        xgb_params: Dict[str, Any] = cfg.get("xgb_params", {})

        base_params: Dict[str, Any] = {
            "n_estimators": n_estimators,
            "learning_rate": xgb_params.get("learning_rate", 0.05),
            "max_depth": xgb_params.get("max_depth", 6),
            "subsample": xgb_params.get("subsample", 0.8),
            "colsample_bytree": xgb_params.get("colsample_bytree", 0.8),
            "min_child_weight": xgb_params.get("min_child_weight", 3),
            "gamma": xgb_params.get("gamma", 0.0),
            "reg_alpha": xgb_params.get("reg_alpha", 0.1),
            "reg_lambda": xgb_params.get("reg_lambda", 1.0),
            "random_state": xgb_params.get("random_state", 42),
            "verbosity": 0,
        }

        # --- Time-series-aware validation split for early stopping ---
        X_train, X_val, y_train, y_val = self._ts_train_val_split(X, y)

        eval_set: Optional[List[Tuple[np.ndarray, np.ndarray]]] = None
        fit_kwargs: Dict[str, Any] = {}
        if X_val is not None:
            eval_set = [(X_val, y_val)]
            fit_kwargs["eval_set"] = eval_set
            fit_kwargs["verbose"] = False

        # --- 1) Median model (squared error) ---
        logger.info("Training XGBoost median model (%d features)...", len(self._feature_cols))
        self.model = xgb.XGBRegressor(
            objective="reg:squarederror",
            early_stopping_rounds=early_stopping if eval_set else None,
            **base_params,
        )
        self.model.fit(X_train, y_train, **fit_kwargs)

        # --- 2) Quantile models for confidence bands ---
        confidence: float = cfg.get("confidence_level", 0.80)
        alpha_lower = (1.0 - confidence) / 2.0
        alpha_upper = 1.0 - alpha_lower

        logger.info(
            "Training quantile models (alpha_lower=%.3f, alpha_upper=%.3f)...",
            alpha_lower,
            alpha_upper,
        )

        try:
            self._model_lower = xgb.XGBRegressor(
                objective="reg:quantileerror",
                quantile_alpha=alpha_lower,
                early_stopping_rounds=early_stopping if eval_set else None,
                **base_params,
            )
            self._model_lower.fit(X_train, y_train, **fit_kwargs)

            self._model_upper = xgb.XGBRegressor(
                objective="reg:quantileerror",
                quantile_alpha=alpha_upper,
                early_stopping_rounds=early_stopping if eval_set else None,
                **base_params,
            )
            self._model_upper.fit(X_train, y_train, **fit_kwargs)
        except Exception:
            # Older XGBoost versions may not support quantile regression.
            # Fall back to bootstrap intervals in predict().
            logger.warning(
                "Quantile regression not available; confidence intervals "
                "will be estimated via bootstrap residuals.",
                exc_info=True,
            )
            self._model_lower = None
            self._model_upper = None

        # --- Feature importance ---
        importance = self.model.feature_importances_
        self.feature_importance = (
            pd.DataFrame(
                {"feature": self._feature_cols, "importance": importance}
            )
            .sort_values("importance", ascending=False)
            .reset_index(drop=True)
        )

        self.is_fitted = True
        self.training_end_date = pd.to_datetime(df["ds"]).max()
        self.training_history = df.copy()

        logger.info(
            "XGBoost fitted on %d rows (features=%d). "
            "Top-3 features: %s",
            len(featured),
            len(self._feature_cols),
            ", ".join(self.feature_importance["feature"].head(3).tolist()),
        )

    def predict(self, horizon_months: int) -> pd.DataFrame:
        """Auto-regressive multi-step forecast.

        For each future month the model predicts ``yhat`` using the
        features available up to that point, then feeds the prediction
        back as the ``y`` value for subsequent lag calculations.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")
        if self.training_history is None:
            raise RuntimeError("Training history is missing.")

        history = self.training_history.copy()
        results: List[Dict[str, Any]] = []

        for step in range(horizon_months):
            # Build features for the next single month
            future = build_future_features(
                history,
                horizon_months=1,
                crop_config=self.crop_config,
                weather_df=self._weather_df,
            )

            # Ensure all expected feature columns exist
            for col in self._feature_cols:
                if col not in future.columns:
                    future[col] = 0.0

            X_future = future[self._feature_cols].values

            # Fill any remaining NaN with 0 (edge case for early lags)
            X_future = np.nan_to_num(X_future, nan=0.0)

            yhat = float(self.model.predict(X_future)[0])

            # Confidence bounds
            if self._model_lower is not None and self._model_upper is not None:
                yhat_lower = float(self._model_lower.predict(X_future)[0])
                yhat_upper = float(self._model_upper.predict(X_future)[0])
            else:
                yhat_lower, yhat_upper = self._bootstrap_interval(X_future, yhat)

            # Ensure ordering: lower <= yhat <= upper
            yhat_lower = min(yhat_lower, yhat)
            yhat_upper = max(yhat_upper, yhat)

            next_date = history["ds"].max() + pd.DateOffset(months=1)
            results.append(
                {
                    "ds": next_date,
                    "yhat": yhat,
                    "yhat_lower": yhat_lower,
                    "yhat_upper": yhat_upper,
                }
            )

            # Append prediction to history for the next step's lag features
            new_row = pd.DataFrame({"ds": [next_date], "y": [yhat]})
            history = pd.concat([history, new_row], ignore_index=True)

        return pd.DataFrame(results)

    # ------------------------------------------------------------------
    # Feature importance
    # ------------------------------------------------------------------

    def get_feature_importance(self, top_n: int = 20) -> Optional[pd.DataFrame]:
        """Return the top-N features by importance."""
        if self.feature_importance is None:
            return None
        return self.feature_importance.head(top_n).copy()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _ts_train_val_split(
        X: np.ndarray,
        y: np.ndarray,
        val_ratio: float = 0.15,
        min_val_size: int = 3,
    ) -> Tuple[np.ndarray, Optional[np.ndarray], np.ndarray, Optional[np.ndarray]]:
        """Time-ordered split for early stopping validation.

        Returns ``(X_train, X_val, y_train, y_val)``.  If the dataset is
        too small for a meaningful validation set, ``X_val`` and ``y_val``
        are ``None``.
        """
        n = len(y)
        val_size = max(int(n * val_ratio), min_val_size)

        if n <= val_size + min_val_size:
            # Not enough data for a separate validation set.
            return X, None, y, None

        split = n - val_size
        return X[:split], X[split:], y[:split], y[split:]

    def _bootstrap_interval(
        self,
        X: np.ndarray,
        yhat: float,
    ) -> Tuple[float, float]:
        """Estimate confidence interval via bootstrap residuals.

        Used as a fallback when quantile regression is not available.
        """
        if self.training_history is None or self.model is None:
            half_width = abs(yhat) * 0.1
            return yhat - half_width, yhat + half_width

        # Compute in-sample residuals
        hist = self.training_history.copy()
        featured = build_features(
            hist, crop_config=self.crop_config, weather_df=self._weather_df, drop_na=True
        )
        if featured.empty or len(featured) < 5:
            half_width = abs(yhat) * 0.1
            return yhat - half_width, yhat + half_width

        for col in self._feature_cols:
            if col not in featured.columns:
                featured[col] = 0.0

        X_hist = np.nan_to_num(featured[self._feature_cols].values, nan=0.0)
        y_hist = featured["y"].values
        preds_hist = self.model.predict(X_hist)
        residuals = y_hist - preds_hist

        confidence = self.crop_config.get("confidence_level", 0.80)
        alpha = (1.0 - confidence) / 2.0

        n_bootstrap = self.crop_config.get("n_bootstrap", 100)
        rng = np.random.default_rng(seed=42)
        bootstrap_preds = np.array(
            [yhat + rng.choice(residuals) for _ in range(n_bootstrap)]
        )

        lower = float(np.percentile(bootstrap_preds, alpha * 100))
        upper = float(np.percentile(bootstrap_preds, (1 - alpha) * 100))
        return lower, upper
