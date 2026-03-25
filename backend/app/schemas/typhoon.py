from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class TyphoonEventResponse(BaseModel):
    id: int
    cwa_id: str
    typhoon_name_zh: str
    typhoon_name_en: str
    year: int
    warning_start: datetime
    warning_end: datetime
    intensity: str
    invasion_path: Optional[str] = None
    min_pressure_hpa: Optional[float] = None
    max_wind_ms: Optional[float] = None
    storm_radius_7_km: Optional[float] = None
    storm_radius_10_km: Optional[float] = None
    warning_count: Optional[int] = None

    model_config = {"from_attributes": True}


class TyphoonImpactResponse(BaseModel):
    crop_key: str
    typhoon_name_zh: str
    year: int
    intensity: str
    price_change_pct: Optional[float] = None
    volume_change_pct: Optional[float] = None

    model_config = {"from_attributes": True}


class TyphoonSimulateRequest(BaseModel):
    intensity: str
    month: int
    crop_key: str


class TyphoonSimulateResponse(BaseModel):
    original_forecast: float
    adjusted_forecast: float
    impact_pct: float
    confidence: str

    model_config = {"from_attributes": True}
