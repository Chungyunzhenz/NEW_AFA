"""
prophet_model.py - Facebook Prophet wrapper for the Taiwan Agricultural
Product Prediction System.

Inherits from ``BasePredictor`` and uses crop-specific configuration to
tune seasonality, changepoint sensitivity, and optional peak-season
regressors.
"""

from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np
import logging

from .base_model import BasePredictor

logger = logging.getLogger(__name__)


class ProphetPredictor(BasePredictor):
    """Prophet-based time-series forecaster.

    Configuration keys read from ``crop_config``:

    - ``yearly_seasonality`` : bool | int | ``"auto"``  (default ``"auto"``)
    - ``weekly_seasonality`` : bool  (default ``False`` — monthly data)
    - ``daily_seasonality`` : bool  (default ``False``)
    - ``seasonality_mode`` : ``"additive"`` | ``"multiplicative"``
      (default ``"additive"``)
    - ``changepoint_prior_scale`` : float  (default 0.05)
    - ``seasonality_prior_scale`` : float  (default 10.0)
    - ``changepoint_range`` : float  (default 0.8)
    - ``peak_months`` : list[int]  — if provided a binary regressor
      ``is_peak_season`` is added so the model can learn a distinct
      peak-season effect.
    - ``holidays_df`` : pd.DataFrame  — optional Prophet-format holidays
      table (columns: ``holiday``, ``ds``, ``lower_window``,
      ``upper_window``).
    - ``interval_width`` : float  (default 0.80 for 80 % CI)
    """

    def __init__(
        self,
        crop_config: Dict[str, Any],
        target_metric: str = "avg_price",
    ) -> None:
        super().__init__(crop_config, target_metric)
        self._peak_months: List[int] = crop_config.get("peak_months", [])
        self._use_peak_regressor: bool = len(self._peak_months) > 0

    # ------------------------------------------------------------------
    # Abstract interface implementation
    # ------------------------------------------------------------------

    def get_model_type(self) -> str:
        return "prophet"

    def fit(self, train_df: pd.DataFrame) -> None:
        """Train Prophet on *train_df* (must have ``ds`` and ``y`` columns).

        If ``peak_months`` is specified in the crop config the training
        frame is augmented with an ``is_peak_season`` binary regressor.
        """
        # Lazy import so Prophet is only required when actually used.
        try:
            from prophet import Prophet
        except ImportError:
            raise ImportError(
                "Prophet is not installed. "
                "Install it with: pip install prophet"
            )

        cfg = self.crop_config

        self.model = Prophet(
            yearly_seasonality=cfg.get("yearly_seasonality", "auto"),
            weekly_seasonality=cfg.get("weekly_seasonality", False),
            daily_seasonality=cfg.get("daily_seasonality", False),
            seasonality_mode=cfg.get("seasonality_mode", "additive"),
            changepoint_prior_scale=cfg.get("changepoint_prior_scale", 0.05),
            seasonality_prior_scale=cfg.get("seasonality_prior_scale", 10.0),
            changepoint_range=cfg.get("changepoint_range", 0.8),
            interval_width=cfg.get("interval_width", 0.80),
            holidays=cfg.get("holidays_df", None),
        )

        df = train_df[["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"])

        # Peak-season regressor
        if self._use_peak_regressor:
            df["is_peak_season"] = (
                df["ds"].dt.month.isin(self._peak_months).astype(float)
            )
            self.model.add_regressor("is_peak_season")

        # Additional numeric regressors present in the training frame
        extra_regressors: List[str] = cfg.get("extra_regressors", [])
        for reg in extra_regressors:
            if reg in train_df.columns:
                df[reg] = train_df[reg].values
                self.model.add_regressor(reg)

        # Suppress the noisy Stan/cmdstanpy output
        with _suppress_prophet_logs():
            self.model.fit(df)

        self.is_fitted = True
        self.training_end_date = df["ds"].max()
        self.training_history = df.copy()
        logger.info(
            "Prophet fitted on %d rows up to %s",
            len(df),
            self.training_end_date.strftime("%Y-%m-%d"),
        )

    def predict(self, horizon_months: int) -> pd.DataFrame:
        """Generate a forecast for *horizon_months* future periods.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        future = self.model.make_future_dataframe(
            periods=horizon_months, freq="MS"
        )

        # Attach regressor columns to future frame
        if self._use_peak_regressor:
            future["is_peak_season"] = (
                future["ds"].dt.month.isin(self._peak_months).astype(float)
            )

        extra_regressors: List[str] = self.crop_config.get("extra_regressors", [])
        if extra_regressors and self.training_history is not None:
            for reg in extra_regressors:
                if reg in self.training_history.columns:
                    # For future rows: forward-fill from last known value
                    hist_vals = self.training_history.set_index("ds")[reg]
                    future = future.set_index("ds")
                    future[reg] = hist_vals
                    future[reg] = future[reg].ffill().bfill()
                    future = future.reset_index()

        with _suppress_prophet_logs():
            raw = self.model.predict(future)

        # Keep only future dates
        forecast = raw[raw["ds"] > self.training_end_date].copy()
        forecast = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        forecast = forecast.head(horizon_months).reset_index(drop=True)
        return forecast

    # ------------------------------------------------------------------
    # Extra diagnostics
    # ------------------------------------------------------------------

    def get_components(self, horizon_months: int) -> pd.DataFrame:
        """Return the full Prophet component decomposition for diagnostics."""
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        future = self.model.make_future_dataframe(
            periods=horizon_months, freq="MS"
        )
        if self._use_peak_regressor:
            future["is_peak_season"] = (
                future["ds"].dt.month.isin(self._peak_months).astype(float)
            )

        with _suppress_prophet_logs():
            return self.model.predict(future)

    def get_changepoints(self) -> Optional[pd.Series]:
        """Return detected changepoint dates, if available."""
        if self.model is None:
            return None
        return self.model.changepoints


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

class _suppress_prophet_logs:
    """Context manager to temporarily silence Prophet / cmdstanpy loggers."""

    _NOISY_LOGGERS = ("prophet", "cmdstanpy", "pystan")

    def __enter__(self) -> "_suppress_prophet_logs":
        self._original_levels: Dict[str, int] = {}
        for name in self._NOISY_LOGGERS:
            lgr = logging.getLogger(name)
            self._original_levels[name] = lgr.level
            lgr.setLevel(logging.WARNING)
        return self

    def __exit__(self, *exc: Any) -> None:  # type: ignore[override]
        for name, level in self._original_levels.items():
            logging.getLogger(name).setLevel(level)
