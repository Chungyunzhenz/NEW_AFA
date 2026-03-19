from typing import Optional
from pydantic import BaseModel


class TrafficLightMetrics(BaseModel):
    crop_key: str
    supply_index: Optional[float] = None
    price_drop_pct: Optional[float] = None
    area_growth_pct: Optional[float] = None
    data_available: bool
