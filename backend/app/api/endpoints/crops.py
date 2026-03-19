import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...schemas.crop import CropResponse, CropDetailResponse

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    """Fetch a crop by its key or raise 404."""
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/", response_model=List[CropResponse])
def list_crops(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all active crops."""
    crops = (
        db.query(Crop)
        .filter(Crop.is_active == True)  # noqa: E712
        .offset(skip)
        .limit(min(limit, 1000))
        .all()
    )
    results = []
    for c in crops:
        config = {}
        if c.config_json:
            try:
                config = json.loads(c.config_json)
            except json.JSONDecodeError:
                pass
        results.append(
            CropResponse(
                id=c.id,
                crop_key=c.crop_key,
                display_name_zh=c.display_name_zh,
                display_name_en=c.display_name_en or "",
                category_code=c.category_code or "",
                is_active=c.is_active,
                color_theme=config.get("color_theme"),
            )
        )
    return results


@router.get("/{crop_key}", response_model=CropDetailResponse)
def get_crop_detail(
    crop_key: str,
    db: Session = Depends(get_db),
):
    """Get detailed information for a single crop, including parsed config."""
    crop = _get_crop_or_404(db, crop_key)

    config = {}
    if crop.config_json:
        try:
            config = json.loads(crop.config_json)
        except json.JSONDecodeError:
            pass

    seasonality = config.get("seasonality", {})
    prediction_horizons = config.get("prediction_horizons_months", [])

    return CropDetailResponse(
        id=crop.id,
        crop_key=crop.crop_key,
        display_name_zh=crop.display_name_zh,
        display_name_en=crop.display_name_en or "",
        category_code=crop.category_code or "",
        is_active=crop.is_active,
        color_theme=config.get("color_theme"),
        seasonality=seasonality,
        prediction_horizons_months=prediction_horizons,
    )
