"""Inverse-error weighted ensemble for combining multi-model predictions.

Combines forecasts from Prophet, SARIMA, and XGBoost using inverse-MAPE
weighting.  When one model has much lower MAPE than the others it receives
proportionally more influence on the final prediction.  Confidence intervals
are computed conservatively by taking the widest bounds across all models.

Usage::

    from app.services.ensemble import EnsemblePredictor

    ep = EnsemblePredictor()
    weights = ep.compute_weights({"prophet": 5.2, "sarima": 7.1, "xgboost": 4.8})
    combined = ep.ensemble_predictions(predictions_dict, weights)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class EnsemblePredictor:
    """Combines predictions from multiple models using inverse-MAPE weighting."""

    # ------------------------------------------------------------------
    # Weight computation
    # ------------------------------------------------------------------
    def compute_weights(self, model_mapes: Dict[str, float]) -> Dict[str, float]:
        """Compute inverse-error weights: weight_i = (1/MAPE_i) / sum(1/MAPE_j).

        Parameters
        ----------
        model_mapes:
            Mapping of ``model_name -> MAPE`` (percentage, e.g. 5.2 means 5.2%).

        Returns
        -------
        dict
            Mapping of ``model_name -> weight`` that sums to 1.0.

        Notes
        -----
        * Models with zero, negative, or infinite MAPE are excluded.
        * If *all* models are excluded the method falls back to equal weights.
        """
        valid = {
            k: v
            for k, v in model_mapes.items()
            if v is not None and np.isfinite(v) and v > 0
        }

        if not valid:
            n = len(model_mapes)
            if n == 0:
                logger.warning("compute_weights called with empty model_mapes.")
                return {}
            equal_w = 1.0 / n
            logger.warning(
                "No valid MAPE values found — falling back to equal weights (%.4f).",
                equal_w,
            )
            return {k: equal_w for k in model_mapes}

        inv_mapes = {k: 1.0 / v for k, v in valid.items()}
        total = sum(inv_mapes.values())
        weights = {k: v / total for k, v in inv_mapes.items()}

        # Assign zero weight to any excluded models so the caller can still
        # iterate over the original model set without KeyError.
        for k in model_mapes:
            if k not in weights:
                weights[k] = 0.0

        logger.info(
            "Ensemble weights computed: %s",
            {k: round(v, 4) for k, v in weights.items()},
        )
        return weights

    # ------------------------------------------------------------------
    # Prediction combination
    # ------------------------------------------------------------------
    def ensemble_predictions(
        self,
        predictions: Dict[str, pd.DataFrame],
        weights: Dict[str, float],
    ) -> pd.DataFrame:
        """Combine per-model predictions into a single ensemble forecast.

        Parameters
        ----------
        predictions:
            ``{model_name: DataFrame}`` where each DataFrame has at least the
            columns ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
        weights:
            ``{model_name: weight}`` — should sum to 1.0.

        Returns
        -------
        pd.DataFrame
            A DataFrame with columns ``ds``, ``yhat``, ``yhat_lower``,
            ``yhat_upper``.

        Notes
        -----
        * ``yhat`` is computed as the weighted average across models.
        * ``yhat_lower`` / ``yhat_upper`` are set to the most conservative
          (widest) bounds across all contributing models.
        * All DataFrames are aligned on the ``ds`` column of the first model
          that appears in the dict.  Models whose ``ds`` values do not match
          are aligned via a left merge.
        """
        if not predictions:
            logger.warning("ensemble_predictions called with empty predictions dict.")
            return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])

        # Use the first model's ds as the reference timeline.
        base_name = next(iter(predictions))
        base_df = predictions[base_name]

        result = pd.DataFrame({"ds": base_df["ds"].values})
        result["yhat"] = 0.0
        result["yhat_lower"] = np.inf
        result["yhat_upper"] = -np.inf

        # Track per-row cumulative weight for correct normalisation
        # when some models lack predictions for certain dates.
        weight_per_row = np.zeros(len(result))

        for name, df in predictions.items():
            w = weights.get(name, 0.0)
            if w <= 0:
                continue

            # Align on ds — if lengths differ, use positional alignment first,
            # then fall back to merge for safety.
            if len(df) == len(result) and np.array_equal(
                df["ds"].values, result["ds"].values
            ):
                yhat_vals = df["yhat"].values
                lower_vals = df["yhat_lower"].values
                upper_vals = df["yhat_upper"].values
            else:
                merged = result[["ds"]].merge(
                    df[["ds", "yhat", "yhat_lower", "yhat_upper"]],
                    on="ds",
                    how="left",
                )
                yhat_vals = merged["yhat"].values
                lower_vals = merged["yhat_lower"].values
                upper_vals = merged["yhat_upper"].values

            # Only include this model's contribution where it has values
            valid = ~np.isnan(yhat_vals)
            result["yhat"] += np.where(valid, yhat_vals * w, 0.0)
            weight_per_row += np.where(valid, w, 0.0)

            safe_lower = np.where(~np.isnan(lower_vals), lower_vals, np.inf)
            safe_upper = np.where(~np.isnan(upper_vals), upper_vals, -np.inf)
            result["yhat_lower"] = np.minimum(
                result["yhat_lower"].values, safe_lower
            )
            result["yhat_upper"] = np.maximum(
                result["yhat_upper"].values, safe_upper
            )

        # Re-normalise yhat per row based on actual weight applied.
        nonzero = weight_per_row > 0
        if nonzero.any():
            result.loc[nonzero, "yhat"] = (
                result.loc[nonzero, "yhat"].values / weight_per_row[nonzero]
            )
        total_weight_applied = float(weight_per_row.mean()) if nonzero.any() else 0.0

        # Replace inf/-inf sentinels that were never overwritten (no model
        # contributed a bound) with the point estimate itself.
        inf_lower = result["yhat_lower"] == np.inf
        inf_upper = result["yhat_upper"] == -np.inf
        if inf_lower.any():
            result.loc[inf_lower, "yhat_lower"] = result.loc[inf_lower, "yhat"]
        if inf_upper.any():
            result.loc[inf_upper, "yhat_upper"] = result.loc[inf_upper, "yhat"]

        logger.info(
            "Ensemble produced %d forecast rows (weight applied: %.4f).",
            len(result),
            total_weight_applied,
        )
        return result

    # ------------------------------------------------------------------
    # Convenience: one-shot from model results
    # ------------------------------------------------------------------
    def combine(
        self,
        model_results: Dict[str, Dict],
    ) -> pd.DataFrame:
        """High-level helper that takes a dict of model results and returns
        the combined ensemble DataFrame.

        Parameters
        ----------
        model_results:
            ``{model_name: {"predictions": DataFrame, "mape": float, ...}}``

        Returns
        -------
        pd.DataFrame
            Combined forecast with ``ds``, ``yhat``, ``yhat_lower``,
            ``yhat_upper``.
        """
        mapes: Dict[str, float] = {}
        preds: Dict[str, pd.DataFrame] = {}

        for name, info in model_results.items():
            mape_val = info.get("mape")
            pred_df = info.get("predictions")
            if pred_df is not None and not pred_df.empty:
                preds[name] = pred_df
                mapes[name] = mape_val if mape_val is not None else float("inf")

        if not preds:
            logger.warning("combine() received no usable predictions.")
            return pd.DataFrame(columns=["ds", "yhat", "yhat_lower", "yhat_upper"])

        weights = self.compute_weights(mapes)
        return self.ensemble_predictions(preds, weights)
