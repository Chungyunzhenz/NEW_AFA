from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...database import get_db
from ...schemas.data_quality import DataQualityOverview, CropQuality
from ...services.data_quality_service import DataQualityService

router = APIRouter()
_service = DataQualityService()


@router.get("/overview", response_model=DataQualityOverview)
def get_overview(db: Session = Depends(get_db)):
    """Get overall data quality health summary."""
    return _service.overview(db)


@router.get("/{crop_key}", response_model=CropQuality)
def get_crop_quality(crop_key: str, db: Session = Depends(get_db)):
    """Get data quality details for a specific crop."""
    result = _service.crop_detail(db, crop_key)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return result
