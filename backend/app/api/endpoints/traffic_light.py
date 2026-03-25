from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...models.trading import TradingData
from ...models.production import ProductionData
from ...schemas.traffic_light import TrafficLightMetrics

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/{crop_key}", response_model=TrafficLightMetrics)
def get_traffic_light(
    crop_key: str,
    db: Session = Depends(get_db),
):
    """
    Calculate traffic-light alert metrics for a given crop.

    - supply_index: recent production_tonnes / recent trading volume
    - price_drop_pct: 30-day avg price vs prior 6-month avg price drop %
    - area_growth_pct: latest year planted_area_ha vs previous year growth %
    """
    crop = _get_crop_or_404(db, crop_key)

    # Use latest data date as reference instead of today, so metrics
    # work even when data hasn't been updated recently.
    latest_date = (
        db.query(func.max(TradingData.trade_date))
        .filter(TradingData.crop_id == crop.id)
        .scalar()
    )
    ref_date = latest_date if latest_date else date.today()

    # --- supply_index ---
    supply_index = None
    recent_production = (
        db.query(func.sum(ProductionData.production_tonnes))
        .filter(ProductionData.crop_id == crop.id)
        .scalar()
    )
    recent_volume = (
        db.query(func.sum(TradingData.volume))
        .filter(TradingData.crop_id == crop.id)
        .filter(TradingData.trade_date >= ref_date - timedelta(days=180))
        .scalar()
    )
    if recent_production and recent_volume and recent_volume > 0:
        supply_index = round(recent_production / recent_volume, 4)

    # --- price_drop_pct ---
    price_drop_pct = None
    avg_30d = (
        db.query(func.avg(TradingData.price_avg))
        .filter(TradingData.crop_id == crop.id)
        .filter(TradingData.trade_date >= ref_date - timedelta(days=30))
        .scalar()
    )
    avg_6m = (
        db.query(func.avg(TradingData.price_avg))
        .filter(TradingData.crop_id == crop.id)
        .filter(TradingData.trade_date >= ref_date - timedelta(days=180))
        .filter(TradingData.trade_date < ref_date - timedelta(days=30))
        .scalar()
    )
    if avg_30d is not None and avg_6m is not None and avg_6m > 0:
        price_drop_pct = round((avg_6m - avg_30d) / avg_6m * 100, 2)

    # --- area_growth_pct ---
    area_growth_pct = None
    latest_year_row = (
        db.query(func.max(ProductionData.year))
        .filter(ProductionData.crop_id == crop.id)
        .filter(ProductionData.planted_area_ha.isnot(None))
        .scalar()
    )
    if latest_year_row and latest_year_row > 1:
        latest_area = (
            db.query(func.sum(ProductionData.planted_area_ha))
            .filter(ProductionData.crop_id == crop.id)
            .filter(ProductionData.year == latest_year_row)
            .scalar()
        )
        prev_area = (
            db.query(func.sum(ProductionData.planted_area_ha))
            .filter(ProductionData.crop_id == crop.id)
            .filter(ProductionData.year == latest_year_row - 1)
            .scalar()
        )
        if latest_area and prev_area and prev_area > 0:
            area_growth_pct = round((latest_area - prev_area) / prev_area * 100, 2)

    data_available = any(v is not None for v in [supply_index, price_drop_pct, area_growth_pct])

    return TrafficLightMetrics(
        crop_key=crop_key,
        supply_index=supply_index,
        price_drop_pct=price_drop_pct,
        area_growth_pct=area_growth_pct,
        data_available=data_available,
    )
