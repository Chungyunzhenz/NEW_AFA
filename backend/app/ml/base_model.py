"""
base_model.py - Abstract base class for all prediction models.

Provides the contract that every predictor in the Taiwan Agricultural Product
Prediction System must satisfy, plus shared utilities for evaluation,
serialization, and cross-validation.
"""

from abc import ABC, abstractmethod
from typing import Tuple, Dict, Any, Optional, List
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class BasePredictor(ABC):
    """Abstract base class for all prediction models.

    Every concrete predictor (Prophet, SARIMA, XGBoost, ...) inherits from this
    class and implements ``fit``, ``predict``, and ``get_model_type``.

    Parameters
    ----------
    crop_config : dict
        Crop-specific configuration (seasonality, peak months, lag settings, etc.).
    target_metric : str
        Name of the column to predict (e.g. ``"avg_price"``, ``"trade_volume"``).
    """

    def __init__(self, crop_config: Dict[str, Any], target_metric: str) -> None:
        self.crop_config = crop_config
        self.target_metric = target_metric
        self.model: Any = None
        self.is_fitted: bool = False
        self.training_end_date: Optional[pd.Timestamp] = None
        self.training_history: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def fit(self, train_df: pd.DataFrame) -> None:
        """Train the model on historical data.

        Parameters
        ----------
        train_df : pd.DataFrame
            Must contain at least a date column (``ds``) and a value column
            (``y``).  Additional columns may be used as regressors depending
            on the concrete implementation.
        """
        pass

    @abstractmethod
    def predict(self, horizon_months: int) -> pd.DataFrame:
        """Generate predictions for *horizon_months* periods into the future.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
        """
        pass

    @abstractmethod
    def get_model_type(self) -> str:
        """Return a human-readable identifier, e.g. ``'prophet'``."""
        pass

    # ------------------------------------------------------------------
    # Evaluation helpers
    # ------------------------------------------------------------------

    def evaluate(
        self,
        actual: pd.Series,
        predicted: pd.Series,
    ) -> Dict[str, float]:
        """Calculate standard regression metrics.

        Returns a dict with keys ``mse``, ``rmse``, ``mae``, ``r_squared``, ``mape``.
        """
        actual = actual.astype(float)
        predicted = predicted.astype(float)

        residuals = actual - predicted
        mse = float(np.mean(residuals ** 2))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(np.abs(residuals)))

        # R² (coefficient of determination)
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((actual - np.mean(actual)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # MAPE — skip zero actuals to avoid division by zero
        mask = actual != 0
        if mask.sum() > 0:
            mape = float(
                np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100
            )
        else:
            mape = float("inf")

        return {"mse": mse, "rmse": rmse, "mae": mae, "r_squared": r_squared, "mape": mape}

    def cross_validate_temporal(
        self,
        df: pd.DataFrame,
        n_splits: int = 3,
        min_train_size: int = 24,
    ) -> List[Dict[str, float]]:
        """Expanding-window temporal cross-validation.

        Parameters
        ----------
        df : pd.DataFrame
            Full dataset in Prophet format (``ds``, ``y``).
        n_splits : int
            Number of evaluation folds.
        min_train_size : int
            Minimum number of rows in the training fold.

        Returns
        -------
        list of dict
            One evaluation dict per fold.
        """
        n = len(df)
        if n < min_train_size + n_splits:
            logger.warning(
                "Not enough data for %d-fold CV (need >= %d rows, got %d). "
                "Returning empty results.",
                n_splits,
                min_train_size + n_splits,
                n,
            )
            return []

        fold_size = (n - min_train_size) // n_splits
        results: List[Dict[str, float]] = []

        for i in range(n_splits):
            train_end = min_train_size + i * fold_size
            val_end = min(train_end + fold_size, n)
            if train_end >= n or val_end <= train_end:
                break

            train_fold = df.iloc[:train_end].copy()
            val_fold = df.iloc[train_end:val_end].copy()

            try:
                self.fit(train_fold)
                horizon = len(val_fold)
                preds = self.predict(horizon)
                metrics = self.evaluate(val_fold["y"].values, preds["yhat"].values[:horizon])
                metrics["fold"] = i
                results.append(metrics)
            except Exception:
                logger.exception("CV fold %d failed", i)

        return results

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Persist the entire predictor to disk via *joblib*."""
        path_obj = Path(path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Model saved to %s", path)

    @classmethod
    def load(cls, path: str) -> "BasePredictor":
        """Load a previously saved predictor."""
        obj = joblib.load(path)
        if not isinstance(obj, BasePredictor):
            raise TypeError(
                f"Expected a BasePredictor instance, got {type(obj).__name__}"
            )
        return obj

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        fitted = "fitted" if self.is_fitted else "not fitted"
        return (
            f"<{self.__class__.__name__} "
            f"model_type={self.get_model_type()!r} "
            f"target={self.target_metric!r} "
            f"({fitted})>"
        )
