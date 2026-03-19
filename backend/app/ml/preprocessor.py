"""
preprocessor.py - Data preprocessing for the Taiwan Agricultural Product
Prediction System.

Responsibilities:
- Resample daily trading data to monthly frequency
- Handle missing values (forward fill, then backward fill)
- Scale data if needed (MinMaxScaler)
- Prepare Prophet-format DataFrame (ds, y columns)
- Time-series-aware train / validation split (last N% for validation)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, List, Dict, Any
from sklearn.preprocessing import MinMaxScaler
import logging

logger = logging.getLogger(__name__)


class TimeSeriesPreprocessor:
    """Stateless (mostly) preprocessing utilities for monthly time series.

    The only mutable state is the optional ``MinMaxScaler`` stored after
    ``scale_values`` is called so that the same transformation can be
    inverted later with ``inverse_scale_values``.
    """

    def __init__(self) -> None:
        self._scaler: Optional[MinMaxScaler] = None
        self._scale_col: Optional[str] = None

    # ------------------------------------------------------------------
    # Resampling
    # ------------------------------------------------------------------

    def resample_to_monthly(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        agg: str = "mean",
    ) -> pd.DataFrame:
        """Resample daily (or irregular) data to calendar-month start frequency.

        Parameters
        ----------
        df : pd.DataFrame
            Raw data with at least ``date_col`` and ``value_col``.
        date_col : str
            Name of the datetime column.
        value_col : str
            Name of the numeric value column to aggregate.
        agg : str
            Aggregation function: ``"mean"`` or ``"sum"``.

        Returns
        -------
        pd.DataFrame
            Two-column DataFrame (``date_col``, ``value_col``) at monthly
            frequency with NaN months dropped.
        """
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.set_index(date_col).sort_index()

        agg_map = {
            "mean": "mean",
            "sum": "sum",
            "median": "median",
            "first": "first",
            "last": "last",
        }
        agg_func = agg_map.get(agg, "mean")
        monthly = df[[value_col]].resample("MS").agg(agg_func)
        monthly = monthly.dropna()
        return monthly.reset_index()

    # ------------------------------------------------------------------
    # Missing value handling
    # ------------------------------------------------------------------

    def fill_missing(
        self,
        df: pd.DataFrame,
        value_col: str,
    ) -> pd.DataFrame:
        """Fill missing values with forward-fill then backward-fill.

        If the column is entirely NaN the original DataFrame is returned
        unchanged.
        """
        df = df.copy()
        if df[value_col].isna().all():
            logger.warning(
                "Column '%s' is entirely NaN; skipping fill_missing.", value_col
            )
            return df
        df[value_col] = df[value_col].ffill(limit=2).bfill(limit=2)
        return df

    def fill_missing_multiple(
        self,
        df: pd.DataFrame,
        value_cols: List[str],
    ) -> pd.DataFrame:
        """Apply ``fill_missing`` to several columns at once."""
        df = df.copy()
        for col in value_cols:
            if col in df.columns:
                df = self.fill_missing(df, col)
        return df

    # ------------------------------------------------------------------
    # Scaling
    # ------------------------------------------------------------------

    def scale_values(
        self,
        df: pd.DataFrame,
        value_col: str,
        feature_range: Tuple[float, float] = (0.0, 1.0),
    ) -> pd.DataFrame:
        """Apply MinMaxScaler to ``value_col`` and store the scaler internally.

        Parameters
        ----------
        df : pd.DataFrame
        value_col : str
        feature_range : tuple of float
            Range for the scaler (default 0-1).

        Returns
        -------
        pd.DataFrame
            Copy of ``df`` with ``value_col`` replaced by scaled values.
        """
        df = df.copy()
        self._scaler = MinMaxScaler(feature_range=feature_range)
        self._scale_col = value_col
        values = df[value_col].values.reshape(-1, 1)
        df[value_col] = self._scaler.fit_transform(values).ravel()
        return df

    def inverse_scale_values(
        self,
        df: pd.DataFrame,
        value_col: Optional[str] = None,
    ) -> pd.DataFrame:
        """Reverse a previous ``scale_values`` transformation.

        Raises ``RuntimeError`` if no scaler has been fitted yet.
        """
        if self._scaler is None:
            raise RuntimeError(
                "No scaler available. Call scale_values() first."
            )
        col = value_col or self._scale_col
        if col is None:
            raise RuntimeError("Cannot determine which column to inverse-scale.")
        df = df.copy()
        values = df[col].values.reshape(-1, 1)
        df[col] = self._scaler.inverse_transform(values).ravel()
        return df

    # ------------------------------------------------------------------
    # Prophet format
    # ------------------------------------------------------------------

    def prepare_prophet_df(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
    ) -> pd.DataFrame:
        """Convert to Prophet's expected schema: ``ds`` (datetime), ``y`` (float).

        The result is sorted by ``ds`` in ascending order.
        """
        result = df[[date_col, value_col]].copy()
        result.columns = ["ds", "y"]
        result["ds"] = pd.to_datetime(result["ds"])
        result["y"] = result["y"].astype(float)
        result = result.sort_values("ds").reset_index(drop=True)
        return result

    # ------------------------------------------------------------------
    # Train / validation split
    # ------------------------------------------------------------------

    def train_val_split(
        self,
        df: pd.DataFrame,
        val_ratio: float = 0.2,
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Time-series-aware split: the **last** ``val_ratio`` fraction is
        used for validation.

        No shuffling is applied — this is critical for time series data.

        Parameters
        ----------
        df : pd.DataFrame
        val_ratio : float
            Fraction of rows to hold out (default 20%).

        Returns
        -------
        (train_df, val_df) : tuple of pd.DataFrame
        """
        if not 0.0 < val_ratio < 1.0:
            raise ValueError(f"val_ratio must be in (0, 1), got {val_ratio}")
        n = len(df)
        split_idx = int(n * (1 - val_ratio))
        # Ensure at least 1 row in each split
        split_idx = max(1, min(split_idx, n - 1))
        train = df.iloc[:split_idx].copy().reset_index(drop=True)
        val = df.iloc[split_idx:].copy().reset_index(drop=True)
        logger.info(
            "Train/val split: %d train rows, %d val rows (ratio=%.2f)",
            len(train),
            len(val),
            val_ratio,
        )
        return train, val

    # ------------------------------------------------------------------
    # Outlier detection (simple IQR)
    # ------------------------------------------------------------------

    def clip_outliers(
        self,
        df: pd.DataFrame,
        value_col: str,
        iqr_multiplier: float = 1.5,
    ) -> pd.DataFrame:
        """Clip values outside the IQR fence to the fence boundaries.

        This is a conservative approach that keeps the data point count
        unchanged but limits the influence of extreme values.
        """
        df = df.copy()
        q1 = df[value_col].quantile(0.25)
        q3 = df[value_col].quantile(0.75)
        iqr = q3 - q1
        lower = q1 - iqr_multiplier * iqr
        upper = q3 + iqr_multiplier * iqr
        clipped = df[value_col].clip(lower=lower, upper=upper)
        n_clipped = int((df[value_col] != clipped).sum())
        if n_clipped > 0:
            logger.info(
                "Clipped %d outlier(s) in '%s' to [%.2f, %.2f]",
                n_clipped,
                value_col,
                lower,
                upper,
            )
        df[value_col] = clipped
        return df

    # ------------------------------------------------------------------
    # Full preprocessing pipeline
    # ------------------------------------------------------------------

    def full_pipeline(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        agg: str = "mean",
        clip_outliers: bool = False,
        scale: bool = False,
    ) -> pd.DataFrame:
        """Run the standard preprocessing pipeline end-to-end.

        Steps:
        1. Resample to monthly.
        2. Fill missing values.
        3. (Optional) Clip outliers.
        4. (Optional) Scale values.
        5. Convert to Prophet format (``ds``, ``y``).
        """
        out = self.resample_to_monthly(df, date_col, value_col, agg=agg)
        out = self.fill_missing(out, value_col)
        if clip_outliers:
            out = self.clip_outliers(out, value_col)
        if scale:
            out = self.scale_values(out, value_col)
        out = self.prepare_prophet_df(out, date_col, value_col)
        return out
