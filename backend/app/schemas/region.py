from pydantic import BaseModel
from typing import Optional


class CountyResponse(BaseModel):
    id: int
    county_code: str
    county_name_zh: str
    county_name_en: str

    model_config = {"from_attributes": True}


class MarketResponse(BaseModel):
    id: int
    market_code: str
    market_name: str
    county_id: int
    county_name_zh: Optional[str] = None

    model_config = {"from_attributes": True}
