from pydantic import BaseModel
from typing import Optional


class ProductionResponse(BaseModel):
    id: int
    year: int
    month: Optional[int] = None
    county_name_zh: str
    planted_area_ha: Optional[float] = None
    harvest_area_ha: Optional[float] = None
    production_tonnes: float
    yield_per_ha: Optional[float] = None

    model_config = {"from_attributes": True}


class ProductionByCounty(BaseModel):
    county_code: str
    county_name_zh: str
    production_tonnes: float
    year: int

    model_config = {"from_attributes": True}
