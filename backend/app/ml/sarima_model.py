"""
sarima_model.py - SARIMA wrapper using pmdarima for the Taiwan Agricultural
Product Prediction System.

Inherits from ``BasePredictor``.  Uses ``pmdarima.auto_arima`` to
automatically select (p, d, q) x (P, D, Q, m) parameters with seasonal
order m = 12 (monthly data).
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
import logging

from .base_model import BasePredictor

logger = logging.getLogger(__name__)


class SARIMAPredictor(BasePredictor):
    """SARIMA (Seasonal ARIMA) predictor backed by pmdarima.

    Configuration keys read from ``crop_config``:

    - ``max_p`` : int  (default 3) — maximum non-seasonal AR order
    - ``max_d`` : int  (default 2) — maximum non-seasonal differencing
    - ``max_q`` : int  (default 3) — maximum non-seasonal MA order
    - ``max_P`` : int  (default 2) — maximum seasonal AR order
    - ``max_D`` : int  (default 1) — maximum seasonal differencing
    - ``max_Q`` : int  (default 2) — maximum seasonal MA order
    - ``seasonal_period`` : int  (default 12)
    - ``stepwise`` : bool  (default ``True``)
    - ``information_criterion`` : str  (default ``"aic"``)
    - ``suppress_warnings`` : bool  (default ``True``)
    - ``trace`` : bool  (default ``False``)
    - ``confidence_level`` : float  (default 0.80) — for prediction intervals
    """

    def __init__(
        self,
        crop_config: Dict[str, Any],
        target_metric: str = "avg_price",
    ) -> None:
        super().__init__(crop_config, target_metric)
        self._arima_order: Optional[tuple] = None
        self._seasonal_order: Optional[tuple] = None

    # ------------------------------------------------------------------
    # Abstract interface implementation
    # ------------------------------------------------------------------

    def get_model_type(self) -> str:
        return "sarima"

    def fit(self, train_df: pd.DataFrame) -> None:
        """Run ``auto_arima`` to select parameters and fit the model.

        Parameters
        ----------
        train_df : pd.DataFrame
            Must contain ``ds`` (datetime) and ``y`` (numeric) columns.
        """
        try:
            import pmdarima as pm
        except ImportError:
            raise ImportError(
                "pmdarima is not installed.  "
                "Install it with: pip install pmdarima"
            )

        cfg = self.crop_config

        df = train_df[["ds", "y"]].copy()
        df["ds"] = pd.to_datetime(df["ds"])
        df = df.sort_values("ds").reset_index(drop=True)

        y = df["y"].values.astype(float)

        if len(y) < 2:
            raise ValueError(
                "Need at least 2 data points to fit SARIMA, got %d." % len(y)
            )

        seasonal_period: int = cfg.get("seasonal_period", 12)
        # If the series is shorter than 2 full seasonal cycles, fall back
        # to non-seasonal ARIMA to avoid estimation issues.
        use_seasonal = len(y) >= 2 * seasonal_period

        if not use_seasonal:
            logger.warning(
                "Series length (%d) < 2 * seasonal_period (%d). "
                "Falling back to non-seasonal ARIMA.",
                len(y),
                seasonal_period,
            )

        logger.info(
            "Running auto_arima on %d observations (seasonal=%s, m=%d)...",
            len(y),
            use_seasonal,
            seasonal_period if use_seasonal else 1,
        )

        self.model = pm.auto_arima(
            y,
            seasonal=use_seasonal,
            m=seasonal_period if use_seasonal else 1,
            max_p=cfg.get("max_p", 3),
            max_d=cfg.get("max_d", 2),
            max_q=cfg.get("max_q", 3),
            max_P=cfg.get("max_P", 2),
            max_D=cfg.get("max_D", 1),
            max_Q=cfg.get("max_Q", 2),
            stepwise=cfg.get("stepwise", True),
            information_criterion=cfg.get("information_criterion", "aic"),
            suppress_warnings=cfg.get("suppress_warnings", True),
            trace=cfg.get("trace", False),
            error_action="ignore",
            n_fits=cfg.get("n_fits", 50),
        )

        self._arima_order = self.model.order
        self._seasonal_order = self.model.seasonal_order
        self.is_fitted = True
        self.training_end_date = df["ds"].max()
        self.training_history = df.copy()

        logger.info(
            "SARIMA fitted: order=%s seasonal_order=%s  AIC=%.2f",
            self._arima_order,
            self._seasonal_order,
            self.model.aic(),
        )

    def predict(self, horizon_months: int) -> pd.DataFrame:
        """Generate forecast with confidence intervals.

        Returns
        -------
        pd.DataFrame
            Columns: ``ds``, ``yhat``, ``yhat_lower``, ``yhat_upper``.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        alpha = 1.0 - self.crop_config.get("confidence_level", 0.80)

        forecasts, conf_int = self.model.predict(
            n_periods=horizon_months,
            return_conf_int=True,
            alpha=alpha,
        )

        future_dates = pd.date_range(
            start=self.training_end_date + pd.DateOffset(months=1),
            periods=horizon_months,
            freq="MS",
        )

        result = pd.DataFrame(
            {
                "ds": future_dates,
                "yhat": forecasts,
                "yhat_lower": conf_int[:, 0],
                "yhat_upper": conf_int[:, 1],
            }
        )
        return result

    # ------------------------------------------------------------------
    # Extra utilities
    # ------------------------------------------------------------------

    def update(self, new_obs: pd.Series) -> None:
        """Incrementally update the model with newly observed values.

        This avoids a full refit and is useful for online/streaming scenarios.
        """
        if not self.is_fitted or self.model is None:
            raise RuntimeError("Model is not fitted. Call fit() first.")

        self.model.update(new_obs.values.astype(float))
        logger.info("SARIMA updated with %d new observation(s).", len(new_obs))

    def get_order(self) -> Optional[tuple]:
        """Return the selected (p, d, q) order, or ``None`` if not fitted."""
        return self._arima_order

    def get_seasonal_order(self) -> Optional[tuple]:
        """Return the selected (P, D, Q, m) seasonal order."""
        return self._seasonal_order

    def summary(self) -> Optional[str]:
        """Return the pmdarima model summary as a string."""
        if self.model is None:
            return None
        return str(self.model.summary())

    def get_diagnostics(self) -> Dict[str, Any]:
        """Return diagnostic information about the fitted model."""
        if not self.is_fitted or self.model is None:
            return {}
        return {
            "order": self._arima_order,
            "seasonal_order": self._seasonal_order,
            "aic": float(self.model.aic()),
            "bic": float(self.model.bic()),
            "n_observations": int(self.model.nobs),
        }

    def residuals(self) -> Optional[np.ndarray]:
        """Return in-sample residuals."""
        if self.model is None:
            return None
        return self.model.resid()
