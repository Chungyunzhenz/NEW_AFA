"""
ml - Machine Learning pipeline for the Taiwan Agricultural Product
Prediction System.

Modules
-------
base_model
    Abstract base class ``BasePredictor``.
preprocessor
    ``TimeSeriesPreprocessor`` for resampling, missing-value handling,
    scaling, and Prophet-format preparation.
feature_engineering
    Feature construction (lags, rolling stats, calendar, seasonal encoding,
    year-over-year, weather) consumed primarily by ``XGBoostPredictor``.
prophet_model
    ``ProphetPredictor`` - Facebook Prophet wrapper.
sarima_model
    ``SARIMAPredictor`` - pmdarima / auto_arima wrapper.
xgboost_model
    ``XGBoostPredictor`` - XGBoost wrapper with quantile confidence bands.
"""

from .base_model import BasePredictor
from .preprocessor import TimeSeriesPreprocessor
from .feature_engineering import build_features, build_future_features, get_feature_columns
from .prophet_model import ProphetPredictor
from .sarima_model import SARIMAPredictor
from .xgboost_model import XGBoostPredictor

__all__ = [
    "BasePredictor",
    "TimeSeriesPreprocessor",
    "build_features",
    "build_future_features",
    "get_feature_columns",
    "ProphetPredictor",
    "SARIMAPredictor",
    "XGBoostPredictor",
]
