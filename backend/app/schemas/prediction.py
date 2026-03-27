from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class PredictionResponse(BaseModel):
    id: int
    crop_key: str
    region_type: str
    region_id: int
    target_metric: str
    forecast_date: date
    forecast_value: float
    lower_bound: float
    upper_bound: float
    model_name: str
    ensemble_weights: Optional[dict] = None
    generated_at: datetime
    horizon_label: str

    model_config = {"from_attributes": True}


class PredictionByCounty(BaseModel):
    county_code: str
    county_name_zh: str
    forecast_value: float
    lower_bound: float
    upper_bound: float

    model_config = {"from_attributes": True}


class ModelInfoResponse(BaseModel):
    model_type: str
    mse: float
    rmse: float
    mae: float
    r_squared: float
    trained_at: datetime
    training_rows: int
    is_active: bool

    model_config = {"from_attributes": True}
