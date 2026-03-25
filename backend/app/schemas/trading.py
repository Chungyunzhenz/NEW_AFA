from typing import Optional
from pydantic import BaseModel
from datetime import date


class TradingDataResponse(BaseModel):
    id: int
    trade_date: date
    crop_name_raw: str
    market_code: str
    market_name: str
    price_high: float
    price_mid: float
    price_low: float
    price_avg: float
    volume: float

    model_config = {"from_attributes": True}


class TradingAggregated(BaseModel):
    period: str
    price_avg: float
    volume_total: float
    trade_count: int

    model_config = {"from_attributes": True}


class TradingByCounty(BaseModel):
    county_code: str
    county_name_zh: str
    avg_price: float
    volume: float
    temp_avg: Optional[float] = None
    rainfall_mm: Optional[float] = None

    model_config = {"from_attributes": True}
