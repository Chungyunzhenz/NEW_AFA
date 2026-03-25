from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import extract, func, desc
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...models.typhoon import TyphoonEvent
from ...models.trading import TradingData
from ...models.prediction import Prediction
from ...schemas.typhoon import (
    TyphoonEventResponse,
    TyphoonImpactResponse,
    TyphoonSimulateRequest,
    TyphoonSimulateResponse,
)

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    """Fetch a crop by its key or raise 404."""
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/events", response_model=List[TyphoonEventResponse])
def list_typhoon_events(
    year_start: Optional[int] = Query(None, description="Start year filter (inclusive)"),
    year_end: Optional[int] = Query(None, description="End year filter (inclusive)"),
    db: Session = Depends(get_db),
):
    """
    List all typhoon events that triggered warnings for Taiwan.
    Supports optional year range filtering.
    """
    query = db.query(TyphoonEvent)

    if year_start is not None:
        query = query.filter(TyphoonEvent.year >= year_start)
    if year_end is not None:
        query = query.filter(TyphoonEvent.year <= year_end)

    query = query.order_by(desc(TyphoonEvent.year), desc(TyphoonEvent.warning_start))

    rows = query.all()
    return rows


@router.get("/events/{year}", response_model=List[TyphoonEventResponse])
def get_typhoon_events_by_year(
    year: int,
    db: Session = Depends(get_db),
):
    """
    Get all typhoon events for a specific year.
    """
    rows = (
        db.query(TyphoonEvent)
        .filter(TyphoonEvent.year == year)
        .order_by(TyphoonEvent.warning_start)
        .all()
    )
    return rows


@router.get("/impact/{crop_key}", response_model=List[TyphoonImpactResponse])
def get_typhoon_impact(
    crop_key: str,
    db: Session = Depends(get_db),
):
    """
    Analyze the historical impact of typhoons on a specific crop.

    For each typhoon event, computes:
    - price_change_pct: percentage change in average price during the typhoon month
      compared to the previous month
    - volume_change_pct: percentage change in trading volume during the typhoon month
      compared to the previous month
    """
    crop = _get_crop_or_404(db, crop_key)

    # Get all typhoon events
    typhoons = (
        db.query(TyphoonEvent)
        .order_by(TyphoonEvent.year, TyphoonEvent.warning_start)
        .all()
    )

    if not typhoons:
        return []

    # Batch query: fetch all monthly stats in one query (GROUP BY year, month)
    monthly_stats_rows = (
        db.query(
            extract("year", TradingData.trade_date).label("yr"),
            extract("month", TradingData.trade_date).label("mo"),
            func.avg(TradingData.price_avg).label("avg_price"),
            func.sum(TradingData.volume).label("total_volume"),
        )
        .filter(TradingData.crop_id == crop.id)
        .group_by(
            extract("year", TradingData.trade_date),
            extract("month", TradingData.trade_date),
        )
        .all()
    )

    # Build lookup dict: (year, month) -> {avg_price, total_volume}
    monthly_stats = {}
    for row in monthly_stats_rows:
        monthly_stats[(int(row.yr), int(row.mo))] = {
            "avg_price": float(row.avg_price) if row.avg_price is not None else None,
            "total_volume": float(row.total_volume) if row.total_volume is not None else None,
        }

    results = []

    for typhoon in typhoons:
        typhoon_year = typhoon.warning_start.year
        typhoon_month = typhoon.warning_start.month

        # Calculate previous month
        if typhoon_month == 1:
            prev_year = typhoon_year - 1
            prev_month = 12
        else:
            prev_year = typhoon_year
            prev_month = typhoon_month - 1

        typhoon_stats = monthly_stats.get((typhoon_year, typhoon_month))
        prev_stats = monthly_stats.get((prev_year, prev_month))

        price_change_pct = None
        volume_change_pct = None

        if (
            typhoon_stats
            and prev_stats
            and typhoon_stats["avg_price"] is not None
            and prev_stats["avg_price"] is not None
            and prev_stats["avg_price"] > 0
        ):
            price_change_pct = round(
                (typhoon_stats["avg_price"] - prev_stats["avg_price"])
                / prev_stats["avg_price"]
                * 100,
                2,
            )

        if (
            typhoon_stats
            and prev_stats
            and typhoon_stats["total_volume"] is not None
            and prev_stats["total_volume"] is not None
            and prev_stats["total_volume"] > 0
        ):
            volume_change_pct = round(
                (typhoon_stats["total_volume"] - prev_stats["total_volume"])
                / prev_stats["total_volume"]
                * 100,
                2,
            )

        results.append(
            TyphoonImpactResponse(
                crop_key=crop.crop_key,
                typhoon_name_zh=typhoon.typhoon_name_zh,
                year=typhoon.year,
                intensity=typhoon.intensity,
                price_change_pct=price_change_pct,
                volume_change_pct=volume_change_pct,
            )
        )

    return results


@router.post("/simulate", response_model=TyphoonSimulateResponse)
def simulate_typhoon_impact(
    request: TyphoonSimulateRequest,
    db: Session = Depends(get_db),
):
    """
    Simulate the impact of a typhoon on a crop's price forecast.

    Takes an intensity level, month, and crop_key, then:
    1. Looks up historical typhoons of the given intensity
    2. Calculates the average price impact percentage
    3. Applies that adjustment to the latest forecast value
    """
    crop = _get_crop_or_404(db, request.crop_key)

    # Validate intensity
    valid_intensities = {"mild", "moderate", "severe"}
    if request.intensity not in valid_intensities:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid intensity '{request.intensity}'. Must be one of: {', '.join(sorted(valid_intensities))}",
        )

    # Validate month
    if request.month < 1 or request.month > 12:
        raise HTTPException(
            status_code=400,
            detail="Month must be between 1 and 12",
        )

    # Find historical typhoons of the given intensity
    typhoons = (
        db.query(TyphoonEvent)
        .filter(TyphoonEvent.intensity == request.intensity)
        .all()
    )

    # Batch query: fetch all monthly avg prices in one query
    monthly_price_rows = (
        db.query(
            extract("year", TradingData.trade_date).label("yr"),
            extract("month", TradingData.trade_date).label("mo"),
            func.avg(TradingData.price_avg).label("avg_price"),
        )
        .filter(TradingData.crop_id == crop.id)
        .group_by(
            extract("year", TradingData.trade_date),
            extract("month", TradingData.trade_date),
        )
        .all()
    )

    # Build lookup dict: (year, month) -> avg_price
    monthly_prices = {}
    for row in monthly_price_rows:
        if row.avg_price is not None:
            monthly_prices[(int(row.yr), int(row.mo))] = float(row.avg_price)

    # Calculate average price impact for this intensity using in-memory lookup
    impact_values = []
    for typhoon in typhoons:
        typhoon_year = typhoon.warning_start.year
        typhoon_month = typhoon.warning_start.month

        if typhoon_month == 1:
            prev_year = typhoon_year - 1
            prev_month = 12
        else:
            prev_year = typhoon_year
            prev_month = typhoon_month - 1

        typhoon_month_price = monthly_prices.get((typhoon_year, typhoon_month))
        prev_month_price = monthly_prices.get((prev_year, prev_month))

        if (
            typhoon_month_price is not None
            and prev_month_price is not None
            and prev_month_price > 0
        ):
            change_pct = (typhoon_month_price - prev_month_price) / prev_month_price * 100
            impact_values.append(change_pct)

    # Determine average impact and confidence
    if impact_values:
        avg_impact_pct = sum(impact_values) / len(impact_values)
        sample_count = len(impact_values)
    else:
        avg_impact_pct = 0.0
        sample_count = 0

    # Confidence based on sample size
    if sample_count >= 10:
        confidence = "high"
    elif sample_count >= 5:
        confidence = "medium"
    else:
        confidence = "low"

    # Get the latest forecast for this crop (price_avg metric)
    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.crop_id == crop.id)
        .filter(Prediction.target_metric == "price_avg")
        .order_by(desc(Prediction.forecast_date), desc(Prediction.generated_at))
        .first()
    )

    if latest_prediction is None:
        raise HTTPException(
            status_code=404,
            detail=f"No price forecast found for crop '{request.crop_key}'",
        )

    original_forecast = latest_prediction.forecast_value
    adjusted_forecast = round(original_forecast * (1 + avg_impact_pct / 100), 2)
    avg_impact_pct = round(avg_impact_pct, 2)

    return TyphoonSimulateResponse(
        original_forecast=original_forecast,
        adjusted_forecast=adjusted_forecast,
        impact_pct=avg_impact_pct,
        confidence=confidence,
    )
