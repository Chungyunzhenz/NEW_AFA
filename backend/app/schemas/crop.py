from pydantic import BaseModel
from typing import Optional


class CropResponse(BaseModel):
    id: int
    crop_key: str
    display_name_zh: str
    display_name_en: str
    category_code: str
    is_active: bool
    color_theme: Optional[str] = None
    has_data: bool = False

    model_config = {"from_attributes": True}


class CropDetailResponse(CropResponse):
    seasonality: dict
    prediction_horizons_months: list

    model_config = {"from_attributes": True}
