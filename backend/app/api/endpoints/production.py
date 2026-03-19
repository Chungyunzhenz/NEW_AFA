from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...models.region import County
from ...models.production import ProductionData
from ...schemas.production import ProductionResponse, ProductionByCounty

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    """Fetch a crop by its key or raise 404."""
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/{crop_key}/by-county", response_model=List[ProductionByCounty])
def get_production_by_county(
    crop_key: str,
    year: int = Query(..., description="Year to query"),
    month: Optional[int] = Query(
        None, ge=1, le=12, description="Month to filter (optional)"
    ),
    db: Session = Depends(get_db),
):
    """
    Get production data aggregated by county for a specific year.
    Optionally filter by month for crops with monthly production data.
    Returns data suitable for choropleth map display.
    """
    crop = _get_crop_or_404(db, crop_key)

    query = (
        db.query(
            County.county_code,
            County.county_name_zh,
            ProductionData.production_tonnes,
            ProductionData.year,
        )
        .select_from(ProductionData)
        .join(County, ProductionData.county_id == County.id)
        .filter(ProductionData.crop_id == crop.id)
        .filter(ProductionData.year == year)
    )

    if month is not None:
        query = query.filter(ProductionData.month == month)

    rows = query.all()

    results = []
    for row in rows:
        results.append(
            ProductionByCounty(
                county_code=row.county_code,
                county_name_zh=row.county_name_zh,
                production_tonnes=row.production_tonnes or 0.0,
                year=row.year,
            )
        )
    return results


@router.get("/{crop_key}/timeseries", response_model=List[ProductionResponse])
def get_production_timeseries(
    crop_key: str,
    county_code: Optional[str] = Query(
        None, description="County code to filter by"
    ),
    start_year: Optional[int] = Query(None, description="Start year (inclusive)"),
    end_year: Optional[int] = Query(None, description="End year (inclusive)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get production time series data for a crop.
    Optionally filter by county and year range.
    """
    crop = _get_crop_or_404(db, crop_key)

    query = (
        db.query(
            ProductionData.id,
            ProductionData.year,
            ProductionData.month,
            County.county_name_zh,
            ProductionData.planted_area_ha,
            ProductionData.harvest_area_ha,
            ProductionData.production_tonnes,
            ProductionData.yield_per_ha,
        )
        .select_from(ProductionData)
        .outerjoin(County, ProductionData.county_id == County.id)
        .filter(ProductionData.crop_id == crop.id)
    )

    if county_code:
        query = query.filter(County.county_code == county_code)
    if start_year is not None:
        query = query.filter(ProductionData.year >= start_year)
    if end_year is not None:
        query = query.filter(ProductionData.year <= end_year)

    query = query.order_by(
        ProductionData.year.desc(), ProductionData.month.desc()
    )

    rows = query.offset(skip).limit(limit).all()

    results = []
    for row in rows:
        results.append(
            ProductionResponse(
                id=row.id,
                year=row.year,
                month=row.month,
                county_name_zh=row.county_name_zh or "",
                planted_area_ha=row.planted_area_ha,
                harvest_area_ha=row.harvest_area_ha,
                production_tonnes=row.production_tonnes,
                yield_per_ha=row.yield_per_ha,
            )
        )
    return results
