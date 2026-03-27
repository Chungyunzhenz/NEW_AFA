"""Model evaluation utilities for the agricultural prediction pipeline.

Provides metric computation (MSE, RMSE, MAE, R², MAPE), model comparison on a
validation set, and expanding-window cross-validation.

Usage::

    from app.services.model_evaluator import ModelEvaluator

    evaluator = ModelEvaluator()
    metrics = evaluator.compute_metrics(y_true, y_pred)
    cv_results = evaluator.cross_validate_expanding(df, train_fn, predict_fn)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class EvaluationMetrics:
    """Container for a single model's evaluation metrics."""

    mse: float = 0.0
    rmse: float = 0.0
    mae: float = 0.0
    r_squared: float = 0.0
    mape: float = float("inf")  # kept for ensemble weighting
    n_samples: int = 0

    def to_dict(self) -> Dict[str, float]:
        return {
            "mse": round(self.mse, 6),
            "rmse": round(self.rmse, 6),
            "mae": round(self.mae, 6),
            "r_squared": round(self.r_squared, 6),
            "mape": round(self.mape, 6),
            "n_samples": self.n_samples,
        }


@dataclass
class ModelComparisonResult:
    """Result of comparing multiple models on the same validation set."""

    model_metrics: Dict[str, EvaluationMetrics] = field(default_factory=dict)
    best_model: Optional[str] = None
    best_mape: float = float("inf")  # used internally for ranking
    best_r_squared: float = float("-inf")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "models": {k: v.to_dict() for k, v in self.model_metrics.items()},
            "best_model": self.best_model,
            "best_r_squared": round(self.best_r_squared, 6),
        }


@dataclass
class CVFoldResult:
    """Result for a single cross-validation fold."""

    fold: int = 0
    train_size: int = 0
    val_size: int = 0
    metrics: Optional[EvaluationMetrics] = None


@dataclass
class CrossValidationResult:
    """Aggregate result of expanding-window cross-validation."""

    model_name: str = ""
    folds: List[CVFoldResult] = field(default_factory=list)
    mean_mse: float = 0.0
    mean_rmse: float = 0.0
    mean_mae: float = 0.0
    mean_r_squared: float = 0.0
    mean_mape: float = float("inf")
    std_mape: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_name": self.model_name,
            "n_folds": len(self.folds),
            "mean_mse": round(self.mean_mse, 6),
            "mean_rmse": round(self.mean_rmse, 6),
            "mean_mae": round(self.mean_mae, 6),
            "mean_r_squared": round(self.mean_r_squared, 6),
            "mean_mape": round(self.mean_mape, 6),
            "std_mape": round(self.std_mape, 6),
            "folds": [
                {
                    "fold": f.fold,
                    "train_size": f.train_size,
                    "val_size": f.val_size,
                    "metrics": f.metrics.to_dict() if f.metrics else None,
                }
                for f in self.folds
            ],
        }


class ModelEvaluator:
    """Evaluate and compare time-series forecasting models."""

    # ------------------------------------------------------------------
    # Core metrics
    # ------------------------------------------------------------------
    @staticmethod
    def compute_metrics(
        y_true: np.ndarray,
        y_pred: np.ndarray,
        clip_mape: float = 200.0,
    ) -> EvaluationMetrics:
        """Compute MSE, RMSE, MAE, R², and MAPE for a pair of arrays.

        Parameters
        ----------
        y_true:
            Ground-truth values.
        y_pred:
            Predicted values (same length as *y_true*).
        clip_mape:
            Maximum allowed MAPE percentage.  Prevents a single near-zero
            actual from blowing MAPE to infinity.

        Returns
        -------
        EvaluationMetrics
        """
        y_true = np.asarray(y_true, dtype=np.float64)
        y_pred = np.asarray(y_pred, dtype=np.float64)

        if len(y_true) != len(y_pred):
            raise ValueError(
                f"Length mismatch: y_true has {len(y_true)} elements, "
                f"y_pred has {len(y_pred)}."
            )

        # Drop NaN pairs
        mask = ~(np.isnan(y_true) | np.isnan(y_pred))
        y_true = y_true[mask]
        y_pred = y_pred[mask]

        n = len(y_true)
        if n == 0:
            logger.warning("No valid samples for metric computation.")
            return EvaluationMetrics()

        errors = y_true - y_pred
        abs_errors = np.abs(errors)

        mse = float(np.mean(errors ** 2))
        rmse = float(np.sqrt(mse))
        mae = float(np.mean(abs_errors))

        # R² (coefficient of determination)
        ss_res = float(np.sum(errors ** 2))
        ss_tot = float(np.sum((y_true - np.mean(y_true)) ** 2))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # MAPE — guard against division by zero (kept for ensemble weighting)
        nonzero_mask = y_true != 0
        if nonzero_mask.any():
            pct_errors = np.abs(errors[nonzero_mask] / y_true[nonzero_mask]) * 100.0
            mape = float(np.mean(np.clip(pct_errors, 0.0, clip_mape)))
        else:
            mape = float("inf")

        return EvaluationMetrics(
            mse=mse, rmse=rmse, mae=mae, r_squared=r_squared,
            mape=mape, n_samples=n,
        )

    # ------------------------------------------------------------------
    # Model comparison
    # ------------------------------------------------------------------
    def compare_models(
        self,
        val_df: pd.DataFrame,
        model_predictions: Dict[str, np.ndarray],
        target_col: str = "y",
    ) -> ModelComparisonResult:
        """Compare multiple models' predictions on the same validation set.

        Parameters
        ----------
        val_df:
            Validation DataFrame containing at least a ``target_col`` column.
        model_predictions:
            ``{model_name: predicted_values_array}``
        target_col:
            Name of the ground-truth column in *val_df*.

        Returns
        -------
        ModelComparisonResult
        """
        y_true = val_df[target_col].values
        result = ModelComparisonResult()

        for name, y_pred in model_predictions.items():
            try:
                metrics = self.compute_metrics(y_true, y_pred)
                result.model_metrics[name] = metrics
                logger.info(
                    "Model '%s': MSE=%.4f, RMSE=%.4f, MAE=%.4f, R²=%.4f (n=%d)",
                    name,
                    metrics.mse,
                    metrics.rmse,
                    metrics.mae,
                    metrics.r_squared,
                    metrics.n_samples,
                )

                if metrics.mape < result.best_mape:
                    result.best_mape = metrics.mape
                    result.best_r_squared = metrics.r_squared
                    result.best_model = name

            except Exception:
                logger.exception("Error evaluating model '%s'.", name)
                result.model_metrics[name] = EvaluationMetrics()

        if result.best_model:
            logger.info(
                "Best model: '%s' with R²=%.4f.",
                result.best_model,
                result.best_r_squared,
            )
        return result

    # ------------------------------------------------------------------
    # Expanding-window cross-validation
    # ------------------------------------------------------------------
    def cross_validate_expanding(
        self,
        df: pd.DataFrame,
        train_fn: Callable[[pd.DataFrame], Any],
        predict_fn: Callable[[Any, pd.DataFrame], np.ndarray],
        target_col: str = "y",
        min_train_size: int = 24,
        n_folds: int = 3,
        val_size: int = 6,
        model_name: str = "unknown",
    ) -> CrossValidationResult:
        """Expanding-window cross-validation for time-series models.

        The data is assumed to be sorted chronologically.  For each fold the
        training window expands by ``val_size`` rows while the validation
        window slides forward.

        Parameters
        ----------
        df:
            Full dataset sorted by time with at least columns ``ds`` and
            ``target_col``.
        train_fn:
            ``train_fn(train_df) -> fitted_model`` — trains on the given
            subset and returns the model object.
        predict_fn:
            ``predict_fn(model, val_df) -> np.ndarray`` — generates
            predictions for the validation subset.
        target_col:
            Name of the target column.
        min_train_size:
            Minimum number of rows required in the training window.
        n_folds:
            Number of cross-validation folds.
        val_size:
            Number of rows in each validation fold.
        model_name:
            Label used in the result for identification.

        Returns
        -------
        CrossValidationResult
        """
        cv_result = CrossValidationResult(model_name=model_name)
        total_rows = len(df)

        # Determine fold boundaries.  Work backwards from the end so that
        # the last fold uses the most recent data as validation.
        fold_ends = []
        for i in range(n_folds):
            val_end = total_rows - i * val_size
            val_start = val_end - val_size
            if val_start < min_train_size:
                break
            fold_ends.append((val_start, val_end))

        # Reverse so we iterate chronologically.
        fold_ends.reverse()

        if not fold_ends:
            logger.warning(
                "Not enough data for cross-validation "
                "(total=%d, min_train=%d, val_size=%d, n_folds=%d).",
                total_rows,
                min_train_size,
                val_size,
                n_folds,
            )
            return cv_result

        mses: List[float] = []
        rmses: List[float] = []
        maes: List[float] = []
        r_squareds: List[float] = []
        mapes: List[float] = []

        for fold_idx, (val_start, val_end) in enumerate(fold_ends, start=1):
            train_subset = df.iloc[:val_start].copy()
            val_subset = df.iloc[val_start:val_end].copy()

            fold_result = CVFoldResult(
                fold=fold_idx,
                train_size=len(train_subset),
                val_size=len(val_subset),
            )

            try:
                model = train_fn(train_subset)
                y_pred = predict_fn(model, val_subset)
                y_true = val_subset[target_col].values

                metrics = self.compute_metrics(y_true, y_pred)
                fold_result.metrics = metrics

                mses.append(metrics.mse)
                rmses.append(metrics.rmse)
                maes.append(metrics.mae)
                r_squareds.append(metrics.r_squared)
                if np.isfinite(metrics.mape):
                    mapes.append(metrics.mape)

                logger.info(
                    "CV fold %d/%d: train=%d, val=%d — "
                    "MSE=%.4f, RMSE=%.4f, MAE=%.4f, R²=%.4f",
                    fold_idx,
                    len(fold_ends),
                    len(train_subset),
                    len(val_subset),
                    metrics.mse,
                    metrics.rmse,
                    metrics.mae,
                    metrics.r_squared,
                )
            except Exception:
                logger.exception("Error in CV fold %d for model '%s'.", fold_idx, model_name)

            cv_result.folds.append(fold_result)

        # Aggregate fold metrics.
        if mses:
            cv_result.mean_mse = float(np.mean(mses))
        if rmses:
            cv_result.mean_rmse = float(np.mean(rmses))
        if maes:
            cv_result.mean_mae = float(np.mean(maes))
        if r_squareds:
            cv_result.mean_r_squared = float(np.mean(r_squareds))
        if mapes:
            cv_result.mean_mape = float(np.mean(mapes))
            cv_result.std_mape = float(np.std(mapes))

        logger.info(
            "CV complete for '%s': mean_MSE=%.4f, mean_RMSE=%.4f, "
            "mean_MAE=%.4f, mean_R²=%.4f, %d folds.",
            model_name,
            cv_result.mean_mse,
            cv_result.mean_rmse,
            cv_result.mean_mae,
            cv_result.mean_r_squared,
            len(cv_result.folds),
        )
        return cv_result

    # ------------------------------------------------------------------
    # Directional accuracy (supplementary metric)
    # ------------------------------------------------------------------
    @staticmethod
    def directional_accuracy(
        y_true: np.ndarray,
        y_pred: np.ndarray,
    ) -> float:
        """Fraction of time steps where the predicted direction of change
        matches the actual direction.

        Returns a value in ``[0.0, 1.0]``.  Requires at least 2 samples.
        """
        y_true = np.asarray(y_true, dtype=np.float64)
        y_pred = np.asarray(y_pred, dtype=np.float64)

        if len(y_true) < 2:
            return 0.0

        true_direction = np.sign(np.diff(y_true))
        pred_direction = np.sign(np.diff(y_pred))

        matches = (true_direction == pred_direction).sum()
        return float(matches / len(true_direction))
