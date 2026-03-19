"""
feature_engineering.py - Feature engineering for XGBoost-based forecasting.

Builds a rich feature matrix from a monthly time series:
- Lag features (configurable periods)
- Rolling statistics (mean, std, max, min over configurable windows)
- Calendar features (month, quarter, week-of-year, is_peak_season)
- Sine / cosine seasonal encoding
- Year-over-year comparisons (same-month-last-year value, YoY growth rate)
- Weather features (monthly avg temperature, cumulative rainfall,
  temperature anomaly) when an external weather DataFrame is provided
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Default configuration (used when keys are absent from crop_config)
# ------------------------------------------------------------------

_DEFAULT_LAG_PERIODS: List[int] = [1, 2, 3, 6, 12]
_DEFAULT_ROLLING_WINDOWS: List[int] = [3, 6, 12]
_DEFAULT_PEAK_MONTHS: List[int] = []  # no peak season assumed


# ====================================================================
# Individual feature builders
# ====================================================================

def add_lag_features(
    df: pd.DataFrame,
    value_col: str,
    lags: List[int],
) -> pd.DataFrame:
    """Add lagged values of ``value_col`` as new columns.

    Column naming: ``lag_{n}`` where *n* is the number of periods.
    """
    df = df.copy()
    for lag in sorted(lags):
        col_name = f"lag_{lag}"
        df[col_name] = df[value_col].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame,
    value_col: str,
    windows: List[int],
) -> pd.DataFrame:
    """Add rolling mean, std, max, and min for each window size.

    Column naming: ``roll_{stat}_{w}`` (e.g. ``roll_mean_3``).
    Calculations use ``min_periods=1`` so that early rows still get partial
    values rather than NaN wherever possible.
    """
    df = df.copy()
    for w in sorted(windows):
        rolled = df[value_col].shift(1).rolling(window=w, min_periods=1)
        df[f"roll_mean_{w}"] = rolled.mean()
        df[f"roll_std_{w}"] = rolled.std()
        df[f"roll_max_{w}"] = rolled.max()
        df[f"roll_min_{w}"] = rolled.min()
    return df


def add_calendar_features(
    df: pd.DataFrame,
    date_col: str,
    peak_months: Optional[List[int]] = None,
) -> pd.DataFrame:
    """Add calendar-derived features.

    Features created:
    - ``month`` (1-12)
    - ``quarter`` (1-4)
    - ``week_of_year`` (1-53 via ISO)
    - ``is_peak_season`` (1 if month is in *peak_months*, else 0)
    """
    df = df.copy()
    dt = pd.to_datetime(df[date_col])
    df["month"] = dt.dt.month
    df["quarter"] = dt.dt.quarter
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)

    if peak_months:
        df["is_peak_season"] = dt.dt.month.isin(peak_months).astype(int)
    else:
        df["is_peak_season"] = 0

    return df


def add_seasonal_encoding(
    df: pd.DataFrame,
    date_col: str,
) -> pd.DataFrame:
    """Add sine / cosine encoding of the month to capture cyclical seasonality.

    - ``month_sin`` = sin(2 * pi * month / 12)
    - ``month_cos`` = cos(2 * pi * month / 12)
    """
    df = df.copy()
    month = pd.to_datetime(df[date_col]).dt.month
    df["month_sin"] = np.sin(2 * np.pi * month / 12)
    df["month_cos"] = np.cos(2 * np.pi * month / 12)
    return df


def add_yoy_features(
    df: pd.DataFrame,
    value_col: str,
) -> pd.DataFrame:
    """Add year-over-year features.

    - ``yoy_value``: same month last year (lag-12).
    - ``yoy_growth``: (current - last_year) / last_year.
      Returns NaN when last year's value is zero or unavailable.
    """
    df = df.copy()
    df["yoy_value"] = df[value_col].shift(12)
    prev = df["yoy_value"]
    # Safe division — replace 0 with NaN to avoid inf
    safe_prev = prev.replace(0, np.nan)
    df["yoy_growth"] = (df[value_col] - prev) / safe_prev
    return df


def add_weather_features(
    df: pd.DataFrame,
    date_col: str,
    weather_df: pd.DataFrame,
    weather_date_col: str = "ds",
    temp_col: str = "temp_avg",
    rain_col: str = "rainfall_mm",
) -> pd.DataFrame:
    """Merge monthly weather data and compute a temperature anomaly.

    Expected weather columns: ``weather_date_col``, ``temp_col``, ``rain_col``.
    Both DataFrames are merged on a derived ``_merge_key`` (year-month) so
    exact day alignment is not required.

    Derived feature:
    - ``temp_anomaly``: deviation of the month's temperature from the
      long-run mean for that calendar month.
    """
    df = df.copy()
    weather = weather_df.copy()

    # Create year-month merge key
    df["_merge_key"] = pd.to_datetime(df[date_col]).dt.to_period("M")
    weather["_merge_key"] = pd.to_datetime(weather[weather_date_col]).dt.to_period("M")

    # Aggregate weather to monthly if not already
    agg_dict: Dict[str, str] = {}
    if temp_col in weather.columns:
        agg_dict[temp_col] = "mean"
    if rain_col in weather.columns:
        agg_dict[rain_col] = "sum"

    if not agg_dict:
        logger.warning("Weather DataFrame has none of the expected columns; skipping.")
        df.drop(columns=["_merge_key"], inplace=True)
        return df

    weather_monthly = (
        weather.groupby("_merge_key")
        .agg(agg_dict)
        .reset_index()
    )

    df = df.merge(weather_monthly, on="_merge_key", how="left")
    df.drop(columns=["_merge_key"], inplace=True)

    # Fill any gaps introduced by the merge
    if temp_col in df.columns:
        df[temp_col] = df[temp_col].ffill().bfill()
    if rain_col in df.columns:
        df[rain_col] = df[rain_col].ffill().bfill()

    # Temperature anomaly: deviation from the calendar-month average
    if temp_col in df.columns and date_col in df.columns:
        month = pd.to_datetime(df[date_col]).dt.month
        monthly_mean = df.groupby(month)[temp_col].transform("mean")
        df["temp_anomaly"] = df[temp_col] - monthly_mean

    return df


# ====================================================================
# Main entry point
# ====================================================================

def build_features(
    df: pd.DataFrame,
    crop_config: Dict[str, Any],
    weather_df: Optional[pd.DataFrame] = None,
    date_col: str = "ds",
    value_col: str = "y",
    drop_na: bool = True,
) -> pd.DataFrame:
    """Build the full feature matrix from a monthly time series.

    Parameters
    ----------
    df : pd.DataFrame
        Must contain ``date_col`` (datetime) and ``value_col`` (float).
    crop_config : dict
        Crop-specific settings.  Recognised keys:

        - ``lag_features`` : list[int]  — lag periods (default [1,2,3,6,12])
        - ``rolling_windows`` : list[int] — window sizes (default [3,6,12])
        - ``peak_months`` : list[int] — months considered peak season
    weather_df : pd.DataFrame, optional
        Monthly weather data.  If provided, weather features are merged.
    date_col, value_col : str
        Column names in *df*.
    drop_na : bool
        If ``True`` (default) rows with any NaN are dropped after feature
        construction.  Set to ``False`` when building *future* feature rows
        where the target is intentionally missing.

    Returns
    -------
    pd.DataFrame
        Original columns plus all engineered features.
    """
    lags: List[int] = crop_config.get("lag_features", _DEFAULT_LAG_PERIODS)
    windows: List[int] = crop_config.get("rolling_windows", _DEFAULT_ROLLING_WINDOWS)
    peak_months: List[int] = crop_config.get("peak_months", _DEFAULT_PEAK_MONTHS)

    out = df.copy()
    out[date_col] = pd.to_datetime(out[date_col])
    out = out.sort_values(date_col).reset_index(drop=True)

    # --- Feature groups ---
    out = add_lag_features(out, value_col, lags)
    out = add_rolling_features(out, value_col, windows)
    out = add_calendar_features(out, date_col, peak_months)
    out = add_seasonal_encoding(out, date_col)
    out = add_yoy_features(out, value_col)

    if weather_df is not None and not weather_df.empty:
        out = add_weather_features(
            out, date_col, weather_df,
            weather_date_col="ds",
            temp_col="temp_avg",
            rain_col="rainfall_mm",
        )

    if drop_na:
        # Fill NaN in lag/yoy/rolling-std columns with 0 for early rows
        # that lack sufficient history, rather than discarding them entirely.
        lag_cols = [c for c in out.columns if c.startswith("lag_")]
        yoy_cols = [c for c in out.columns if c.startswith("yoy_")]
        roll_std_cols = [c for c in out.columns if c.startswith("roll_std_")]
        fillable = lag_cols + yoy_cols + roll_std_cols
        if fillable:
            out[fillable] = out[fillable].fillna(0)

        before = len(out)
        out = out.dropna().reset_index(drop=True)
        dropped = before - len(out)
        if dropped > 0:
            logger.info(
                "Dropped %d rows with NaN after feature engineering "
                "(%d remaining).",
                dropped,
                len(out),
            )

    return out


def get_feature_columns(
    df: pd.DataFrame,
    date_col: str = "ds",
    value_col: str = "y",
) -> List[str]:
    """Return the list of feature column names (everything except ds and y)."""
    exclude = {date_col, value_col}
    return [c for c in df.columns if c not in exclude]


def build_future_features(
    history_df: pd.DataFrame,
    horizon_months: int,
    crop_config: Dict[str, Any],
    weather_df: Optional[pd.DataFrame] = None,
    date_col: str = "ds",
    value_col: str = "y",
) -> pd.DataFrame:
    """Create feature rows for future months that need to be predicted.

    The approach:
    1. Append ``horizon_months`` placeholder rows (``y = NaN``) after the
       last date in *history_df*.
    2. For each future row, iteratively fill lag / rolling features from
       previously predicted or known values (caller must supply predictions
       via the ``y`` column of the returned frame).
    3. Calendar and seasonal features are deterministic and always available.

    Returns a DataFrame containing **only** the future rows, with feature
    columns filled as far as possible.  Lag features that depend on
    not-yet-predicted values will be NaN — the caller should fill them in
    an auto-regressive loop.
    """
    hist = history_df.copy()
    hist[date_col] = pd.to_datetime(hist[date_col])
    last_date = hist[date_col].max()

    future_dates = pd.date_range(
        start=last_date + pd.DateOffset(months=1),
        periods=horizon_months,
        freq="MS",
    )
    future = pd.DataFrame({date_col: future_dates, value_col: np.nan})

    combined = pd.concat([hist, future], ignore_index=True)
    combined = build_features(
        combined,
        crop_config,
        weather_df=weather_df,
        date_col=date_col,
        value_col=value_col,
        drop_na=False,  # keep the NaN target rows
    )

    # Return only future portion
    n_future = horizon_months
    return combined.iloc[-n_future:].reset_index(drop=True)
