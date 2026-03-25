"""ML pipeline coordinator for the Taiwan Agricultural Product Prediction System.

Orchestrates data preparation, model training, evaluation, ensembling, and
persistence for every active crop / metric / geographic level.

Usage::

    from app.database import SessionLocal
    from app.services.prediction_engine import PredictionEngine

    db = SessionLocal()
    engine = PredictionEngine()
    engine.run_full_pipeline(db)
    db.close()
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import load_crop_configs
from ..models import Crop, Market, TradingData, WeatherData
from ..models.prediction import Prediction
from ..models.model_registry import ModelRegistry
from ..models.typhoon import TyphoonEvent
from .ensemble import EnsemblePredictor
from .model_evaluator import ModelEvaluator
from .model_trainer import ModelTrainer

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MINIMUM_MONTHS = 24           # At least 24 monthly observations required
TRAIN_RATIO = 0.70            # 70 / 30 train-val split (after holdout removal)
HOLDOUT_DAYS = 90             # Reserve the most recent 90 days for future validation
TARGET_METRICS = ("price_avg", "volume")
HORIZON_MAP = {               # label -> months
    "1m": 1,
    "3m": 3,
    "6m": 6,
}
MODEL_TYPES = ("prophet", "sarima", "xgboost")


class PredictionEngine:
    """Top-level orchestrator for the prediction pipeline."""

    def __init__(self) -> None:
        self.trainer = ModelTrainer()
        self.evaluator = ModelEvaluator()
        self.ensemble = EnsemblePredictor()

    # ==================================================================
    # Public entry points
    # ==================================================================
    def run_full_pipeline(self, db: Session) -> Dict[str, Any]:
        """Run the entire training + prediction pipeline for all active crops.

        Returns a summary dict keyed by ``crop_key``.
        """
        logger.info("===== Starting full prediction pipeline =====")
        crop_configs = load_crop_configs()
        active_crops = (
            db.query(Crop).filter(Crop.is_active == True).all()  # noqa: E712
        )

        results: Dict[str, Any] = {}
        for crop in active_crops:
            cfg = crop_configs.get(crop.crop_key)
            if cfg is None:
                logger.warning(
                    "No config file found for crop '%s' — skipping.", crop.crop_key
                )
                continue
            try:
                crop_result = self.run_for_crop(crop.crop_key, db, crop_config=cfg)
                results[crop.crop_key] = crop_result
            except Exception:
                logger.exception(
                    "Pipeline failed for crop '%s'.", crop.crop_key
                )
                results[crop.crop_key] = {"status": "error"}

        logger.info("===== Full pipeline complete. Processed %d crops. =====", len(results))
        return results

    def run_for_crop(
        self,
        crop_key: str,
        db: Session,
        crop_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the pipeline for a single crop across all metrics and regions.

        Parameters
        ----------
        crop_key:
            The crop key (e.g. ``"cabbage"``).
        db:
            Active SQLAlchemy session.
        crop_config:
            Pre-loaded crop config dict.  If *None* the config is loaded
            from disk.

        Returns
        -------
        dict
            Summary with per-metric, per-region results.
        """
        logger.info("--- Pipeline for crop '%s' ---", crop_key)

        crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
        if crop is None:
            logger.error("Crop '%s' not found in DB.", crop_key)
            return {"status": "error", "detail": "crop not found"}

        if crop_config is None:
            configs = load_crop_configs()
            crop_config = configs.get(crop_key)
            if crop_config is None:
                logger.error("No config file for crop '%s'.", crop_key)
                return {"status": "error", "detail": "config not found"}

        horizons: List[int] = crop_config.get("prediction_horizons_months", [1, 3, 6])
        max_horizon = max(horizons) if horizons else 6

        summary: Dict[str, Any] = {"crop_key": crop_key, "metrics": {}}

        for target_metric in TARGET_METRICS:
            metric_results: Dict[str, Any] = {}

            # ---- National aggregate ----
            national_result = self._run_for_region(
                crop=crop,
                crop_config=crop_config,
                target_metric=target_metric,
                region_type="national",
                region_id=0,
                market_id=None,
                horizons=horizons,
                max_horizon=max_horizon,
                db=db,
            )
            metric_results["national"] = national_result

            # ---- Per-market ----
            market_ids = self._get_crop_market_ids(crop.id, db)
            per_market: Dict[int, Any] = {}
            for market_id in market_ids:
                mkt_result = self._run_for_region(
                    crop=crop,
                    crop_config=crop_config,
                    target_metric=target_metric,
                    region_type="market",
                    region_id=market_id,
                    market_id=market_id,
                    horizons=horizons,
                    max_horizon=max_horizon,
                    db=db,
                )
                per_market[market_id] = mkt_result
            metric_results["markets"] = per_market

            summary["metrics"][target_metric] = metric_results

        summary["status"] = "ok"
        logger.info("--- Pipeline for crop '%s' finished. ---", crop_key)
        return summary

    # ==================================================================
    # Internal pipeline stages
    # ==================================================================
    def _run_for_region(
        self,
        crop: Crop,
        crop_config: Dict[str, Any],
        target_metric: str,
        region_type: str,
        region_id: int,
        market_id: Optional[int],
        horizons: List[int],
        max_horizon: int,
        db: Session,
    ) -> Dict[str, Any]:
        """Execute the full train-evaluate-predict cycle for one region."""
        label = f"{crop.crop_key}/{target_metric}/{region_type}:{region_id}"
        logger.info("Processing %s", label)

        # 1. Prepare data
        prepared = self._prepare_data(crop.id, target_metric, market_id, db)
        if prepared is None:
            logger.warning("Insufficient data for %s — skipping.", label)
            return {"status": "skipped", "reason": "insufficient_data"}

        monthly_df, weather_features = prepared

        # 2. Merge weather features
        if weather_features is not None and not weather_features.empty:
            monthly_df = monthly_df.merge(weather_features, on="ds", how="left")
            # Forward-fill weather columns to handle gaps.
            weather_cols = [
                c for c in weather_features.columns if c != "ds"
            ]
            monthly_df[weather_cols] = monthly_df[weather_cols].ffill().bfill()

        # 2b. Fetch typhoon data and add typhoon features
        typhoon_df = self._fetch_typhoon_data(db)
        if typhoon_df is not None and not typhoon_df.empty:
            from ..ml.feature_engineering import add_typhoon_features
            monthly_df = add_typhoon_features(monthly_df, "ds", typhoon_df)

        # 3. Train / validation / holdout split
        train_df, val_df, holdout_df = self._time_split(monthly_df)
        if len(train_df) < 12 or len(val_df) < 3:
            logger.warning(
                "Train/val split too small for %s (train=%d, val=%d, holdout=%d) — skipping.",
                label, len(train_df), len(val_df), len(holdout_df),
            )
            return {"status": "skipped", "reason": "split_too_small"}
        logger.info(
            "Data split for %s: train=%d, val=%d, holdout=%d (reserved, not used)",
            label, len(train_df), len(val_df), len(holdout_df),
        )

        # 4. Train and evaluate all model types
        model_results = self._train_and_evaluate(
            train_df=train_df,
            val_df=val_df,
            crop_config=crop_config,
            target_metric=target_metric,
            region_info={"region_type": region_type, "region_id": region_id},
            crop_id=crop.id,
            db=db,
            forecast_horizon=max_horizon,
        )

        if not model_results:
            logger.warning("All models failed for %s.", label)
            return {"status": "error", "reason": "all_models_failed"}

        # 5. Compute ensemble weights and combined predictions
        mapes = {
            name: info["metrics"].mape
            for name, info in model_results.items()
            if info.get("metrics") is not None
        }
        weights = self.ensemble.compute_weights(mapes)

        # Gather per-model forecast DataFrames.
        forecast_dfs = {
            name: info["predictions"]
            for name, info in model_results.items()
            if info.get("predictions") is not None
            and not info["predictions"].empty
        }

        if forecast_dfs:
            ensemble_df = self.ensemble.ensemble_predictions(forecast_dfs, weights)
        else:
            ensemble_df = pd.DataFrame(
                columns=["ds", "yhat", "yhat_lower", "yhat_upper"]
            )

        # 6. Save predictions for each horizon
        for h_label, h_months in HORIZON_MAP.items():
            if h_months not in horizons:
                continue

            # Ensemble predictions
            if not ensemble_df.empty:
                horizon_df = ensemble_df.head(h_months)
                self._save_predictions(
                    predictions=horizon_df,
                    crop_id=crop.id,
                    region_type=region_type,
                    region_id=region_id,
                    target_metric=target_metric,
                    model_name="ensemble",
                    weights=weights,
                    horizon_label=h_label,
                    db=db,
                )

            # Individual model predictions
            for model_name, model_df in forecast_dfs.items():
                horizon_slice = model_df.head(h_months)
                self._save_predictions(
                    predictions=horizon_slice,
                    crop_id=crop.id,
                    region_type=region_type,
                    region_id=region_id,
                    target_metric=target_metric,
                    model_name=model_name,
                    weights=None,
                    horizon_label=h_label,
                    db=db,
                )

        db.commit()

        return {
            "status": "ok",
            "train_rows": len(train_df),
            "val_rows": len(val_df),
            "holdout_rows": len(holdout_df),
            "models_trained": list(model_results.keys()),
            "ensemble_weights": {k: round(v, 4) for k, v in weights.items()},
        }

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------
    def _prepare_data(
        self,
        crop_id: int,
        target_metric: str,
        market_id: Optional[int],
        db: Session,
    ) -> Optional[Tuple[pd.DataFrame, Optional[pd.DataFrame]]]:
        """Fetch historical trading data, resample to monthly, optionally
        merge weather features.

        Returns ``(monthly_df, weather_df)`` or *None* if insufficient data.
        """
        query = db.query(
            TradingData.trade_date,
            TradingData.price_avg,
            TradingData.volume,
            TradingData.market_id,
        ).filter(TradingData.crop_id == crop_id)

        if market_id is not None:
            query = query.filter(TradingData.market_id == market_id)

        query = query.order_by(TradingData.trade_date)
        rows = query.all()

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=["trade_date", "price_avg", "volume", "market_id"])
        df["trade_date"] = pd.to_datetime(df["trade_date"])

        # Resample to month-start frequency.
        df = df.set_index("trade_date")
        monthly = df.resample("MS").agg(
            {
                "price_avg": "mean",
                "volume": "sum",
                "market_id": "first",
            }
        ).reset_index()

        # Rename for Prophet-style interface.
        monthly = monthly.rename(columns={"trade_date": "ds"})

        if target_metric not in monthly.columns:
            logger.error("Target metric '%s' not in monthly columns.", target_metric)
            return None

        monthly["y"] = monthly[target_metric]
        monthly = monthly.dropna(subset=["y"])

        if len(monthly) < MINIMUM_MONTHS:
            logger.info(
                "Only %d monthly observations for crop_id=%d, metric=%s "
                "(need %d). Skipping.",
                len(monthly), crop_id, target_metric, MINIMUM_MONTHS,
            )
            return None

        # --- Weather features ---
        weather_df = self._fetch_weather_features(monthly, market_id, db)

        return monthly, weather_df

    def _fetch_weather_features(
        self,
        monthly_df: pd.DataFrame,
        market_id: Optional[int],
        db: Session,
    ) -> Optional[pd.DataFrame]:
        """Fetch and aggregate weather observations into monthly features.

        If *market_id* is provided the weather data is scoped to the county
        that hosts the market; otherwise a national average is computed.
        """
        county_id: Optional[int] = None
        if market_id is not None:
            market = db.query(Market).filter(Market.id == market_id).first()
            if market and market.county_id:
                county_id = market.county_id

        query = db.query(
            WeatherData.observation_date,
            WeatherData.temp_avg,
            WeatherData.rainfall_mm,
            WeatherData.humidity_pct,
        )

        if county_id is not None:
            query = query.filter(WeatherData.county_id == county_id)

        query = query.order_by(WeatherData.observation_date)
        rows = query.all()

        if not rows:
            return None

        wdf = pd.DataFrame(
            rows,
            columns=["observation_date", "temp_avg", "rainfall_mm", "humidity_pct"],
        )
        wdf["observation_date"] = pd.to_datetime(wdf["observation_date"])
        wdf = wdf.set_index("observation_date")

        monthly_weather = wdf.resample("MS").agg(
            {
                "temp_avg": "mean",
                "rainfall_mm": "sum",
                "humidity_pct": "mean",
            }
        ).reset_index()

        monthly_weather = monthly_weather.rename(
            columns={"observation_date": "ds"}
        )

        return monthly_weather

    # ------------------------------------------------------------------
    # Train / validation split
    # ------------------------------------------------------------------
    @staticmethod
    def _time_split(
        df: pd.DataFrame,
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Split a chronologically sorted DataFrame into train / val / holdout.

        1. Remove the most recent ``HOLDOUT_DAYS`` (≈3 months) as holdout —
           this data is completely excluded from training and evaluation.
        2. Split the remaining data 70/30 into train and validation sets.

        Returns ``(train_df, val_df, holdout_df)``.
        """
        df = df.copy()
        df["ds"] = pd.to_datetime(df["ds"])

        cutoff_date = df["ds"].max() - pd.Timedelta(days=HOLDOUT_DAYS)
        holdout = df[df["ds"] > cutoff_date].copy().reset_index(drop=True)
        remaining = df[df["ds"] <= cutoff_date].copy()

        n = len(remaining)
        split_idx = int(n * TRAIN_RATIO)
        train = remaining.iloc[:split_idx].copy().reset_index(drop=True)
        val = remaining.iloc[split_idx:].copy().reset_index(drop=True)

        return train, val, holdout

    # ------------------------------------------------------------------
    # Train and evaluate all models
    # ------------------------------------------------------------------
    def _train_and_evaluate(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        crop_config: Dict[str, Any],
        target_metric: str,
        region_info: Dict[str, Any],
        crop_id: int,
        db: Session,
        forecast_horizon: int = 6,
    ) -> Dict[str, Dict[str, Any]]:
        """Train Prophet, SARIMA, and XGBoost; return per-model results."""
        results: Dict[str, Dict[str, Any]] = {}

        for model_type in MODEL_TYPES:
            try:
                result = self.trainer.train_single_model(
                    model_type=model_type,
                    train_df=train_df,
                    val_df=val_df,
                    crop_config=crop_config,
                    target_metric=target_metric,
                    region_info=region_info,
                    db=db,
                    crop_id=crop_id,
                    forecast_horizon=forecast_horizon,
                )
                if result.get("metrics") is not None:
                    results[model_type] = result
                else:
                    logger.warning(
                        "Model '%s' produced no metrics — excluded from ensemble.",
                        model_type,
                    )
            except Exception:
                logger.exception(
                    "Error training model '%s' for crop_id=%d.", model_type, crop_id
                )

        return results

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _save_predictions(
        self,
        predictions: pd.DataFrame,
        crop_id: int,
        region_type: str,
        region_id: int,
        target_metric: str,
        model_name: str,
        weights: Optional[Dict[str, float]],
        horizon_label: str,
        db: Session,
    ) -> int:
        """Write forecast rows to the ``predictions`` table.

        Returns the count of rows inserted.
        """
        if predictions.empty:
            return 0

        weights_json = json.dumps(weights, ensure_ascii=False) if weights else None
        now = datetime.utcnow()
        count = 0

        for _, row in predictions.iterrows():
            forecast_date = pd.to_datetime(row["ds"]).date()
            forecast_value = float(row["yhat"])
            lower = float(row.get("yhat_lower", forecast_value))
            upper = float(row.get("yhat_upper", forecast_value))

            # Remove stale prediction for the same slot if it exists.
            db.query(Prediction).filter(
                Prediction.crop_id == crop_id,
                Prediction.region_type == region_type,
                Prediction.region_id == region_id,
                Prediction.target_metric == target_metric,
                Prediction.model_name == model_name,
                Prediction.forecast_date == forecast_date,
                Prediction.horizon_label == horizon_label,
            ).delete(synchronize_session="fetch")

            pred = Prediction(
                crop_id=crop_id,
                region_type=region_type,
                region_id=region_id,
                target_metric=target_metric,
                forecast_date=forecast_date,
                forecast_value=forecast_value,
                lower_bound=lower,
                upper_bound=upper,
                model_name=model_name,
                ensemble_weights=weights_json,
                generated_at=now,
                horizon_label=horizon_label,
            )
            db.add(pred)
            count += 1

        logger.info(
            "Saved %d prediction rows (%s, %s, %s/%d, horizon=%s).",
            count,
            model_name,
            target_metric,
            region_type,
            region_id,
            horizon_label,
        )
        return count

    # ------------------------------------------------------------------
    # Typhoon data
    # ------------------------------------------------------------------
    @staticmethod
    def _fetch_typhoon_data(db: Session) -> Optional[pd.DataFrame]:
        """Fetch all typhoon events from the database as a DataFrame."""
        try:
            rows = (
                db.query(
                    TyphoonEvent.warning_start,
                    TyphoonEvent.warning_end,
                    TyphoonEvent.intensity,
                    TyphoonEvent.max_wind_ms,
                    TyphoonEvent.min_pressure_hpa,
                )
                .order_by(TyphoonEvent.warning_start)
                .all()
            )
            if not rows:
                return None
            return pd.DataFrame(
                rows,
                columns=["warning_start", "warning_end", "intensity", "max_wind_ms", "min_pressure_hpa"],
            )
        except Exception:
            logger.warning("Could not fetch typhoon data — table may not exist yet.")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _get_crop_market_ids(crop_id: int, db: Session) -> List[int]:
        """Return distinct market IDs that have trading data for *crop_id*."""
        rows = (
            db.query(TradingData.market_id)
            .filter(
                TradingData.crop_id == crop_id,
                TradingData.market_id.isnot(None),
            )
            .distinct()
            .all()
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Cleanup utility
    # ------------------------------------------------------------------
    @staticmethod
    def cleanup_old_predictions(
        db: Session,
        months_to_keep: int = 12,
    ) -> int:
        """Delete predictions whose ``generated_at`` is older than
        *months_to_keep* months ago.

        Returns the number of deleted rows.
        """
        cutoff = datetime.utcnow() - timedelta(days=months_to_keep * 30)
        deleted = (
            db.query(Prediction)
            .filter(Prediction.generated_at < cutoff)
            .delete(synchronize_session="fetch")
        )
        db.commit()
        logger.info(
            "Cleaned up %d old prediction rows (cutoff=%s).", deleted, cutoff.date()
        )
        return deleted
