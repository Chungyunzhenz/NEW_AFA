import logging
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ...database import get_db
from ...models.crop import Crop
from ...models.region import County, Market
from ...models.trading import TradingData
from ...schemas.trading import TradingDataResponse, TradingAggregated, TradingByCounty

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    """Fetch a crop by its key or raise 404."""
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/{crop_key}/daily", response_model=List[TradingDataResponse])
def get_daily_trading(
    crop_key: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    market_code: Optional[str] = Query(None, description="Filter by market code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Retrieve daily trading data for a crop with optional date range and market filters.
    Joins with Market to include market_code and market_name.
    """
    crop = _get_crop_or_404(db, crop_key)

    query = (
        db.query(
            TradingData.id,
            TradingData.trade_date,
            TradingData.crop_name_raw,
            Market.market_code,
            Market.market_name,
            TradingData.price_high,
            TradingData.price_mid,
            TradingData.price_low,
            TradingData.price_avg,
            TradingData.volume,
        )
        .outerjoin(Market, TradingData.market_id == Market.id)
        .filter(TradingData.crop_id == crop.id)
    )

    if start_date:
        query = query.filter(TradingData.trade_date >= start_date)
    if end_date:
        query = query.filter(TradingData.trade_date <= end_date)
    if market_code:
        query = query.filter(Market.market_code == market_code)

    query = query.order_by(TradingData.trade_date.desc())

    rows = query.offset(skip).limit(limit).all()

    results = []
    for row in rows:
        results.append(
            TradingDataResponse(
                id=row.id,
                trade_date=row.trade_date,
                crop_name_raw=row.crop_name_raw,
                market_code=row.market_code or "",
                market_name=row.market_name or "",
                price_high=row.price_high or 0.0,
                price_mid=row.price_mid or 0.0,
                price_low=row.price_low or 0.0,
                price_avg=row.price_avg or 0.0,
                volume=row.volume or 0.0,
            )
        )
    return results


@router.get("/{crop_key}/aggregated", response_model=List[TradingAggregated])
def get_aggregated_trading(
    crop_key: str,
    granularity: str = Query(
        "month",
        description="Aggregation granularity: week, month, or year",
        pattern="^(week|month|year)$",
    ),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Aggregate trading data by week, month, or year.
    Returns average price, total volume, and trade count per period.
    """
    crop = _get_crop_or_404(db, crop_key)

    # Build the period expression based on granularity.
    # SQLite uses strftime; adjust if using PostgreSQL.
    if granularity == "week":
        period_expr = func.strftime("%Y-W%W", TradingData.trade_date)
    elif granularity == "year":
        period_expr = func.strftime("%Y", TradingData.trade_date)
    else:  # month
        period_expr = func.strftime("%Y-%m", TradingData.trade_date)

    query = (
        db.query(
            period_expr.label("period"),
            func.avg(TradingData.price_avg).label("price_avg"),
            func.sum(TradingData.volume).label("volume_total"),
            func.count(TradingData.id).label("trade_count"),
        )
        .filter(TradingData.crop_id == crop.id)
    )

    if start_date:
        query = query.filter(TradingData.trade_date >= start_date)
    if end_date:
        query = query.filter(TradingData.trade_date <= end_date)

    query = (
        query.group_by(period_expr)
        .order_by(period_expr.desc())
        .offset(skip)
        .limit(limit)
    )

    rows = query.all()

    results = []
    for row in rows:
        results.append(
            TradingAggregated(
                period=row.period or "",
                price_avg=round(row.price_avg, 2) if row.price_avg else 0.0,
                volume_total=round(row.volume_total, 2) if row.volume_total else 0.0,
                trade_count=row.trade_count or 0,
            )
        )
    return results


@router.get("/{crop_key}/by-county", response_model=List[TradingByCounty])
def get_trading_by_county(
    crop_key: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
):
    """
    Aggregate trading data by county for choropleth map display.
    Groups through Market -> County relationship.
    """
    crop = _get_crop_or_404(db, crop_key)

    # Warn if records are being excluded due to NULL market_id
    null_market_count = (
        db.query(func.count(TradingData.id))
        .filter(TradingData.crop_id == crop.id, TradingData.market_id.is_(None))
        .scalar()
    )
    if null_market_count:
        logger.warning(
            "by-county: excluded %d records with NULL market_id for crop %s",
            null_market_count, crop_key,
        )

    query = (
        db.query(
            County.county_code,
            County.county_name_zh,
            func.avg(TradingData.price_avg).label("avg_price"),
            func.sum(TradingData.volume).label("volume"),
        )
        .select_from(TradingData)
        .join(Market, TradingData.market_id == Market.id)
        .join(County, Market.county_id == County.id)
        .filter(TradingData.crop_id == crop.id)
    )

    if start_date:
        query = query.filter(TradingData.trade_date >= start_date)
    if end_date:
        query = query.filter(TradingData.trade_date <= end_date)

    query = query.group_by(County.county_code, County.county_name_zh)

    rows = query.all()

    # Fetch latest weather data per county
    from ...models.weather import WeatherData
    weather_query = (
        db.query(
            WeatherData.county_id,
            func.avg(WeatherData.temp_avg).label("temp_avg"),
            func.sum(WeatherData.rainfall_mm).label("rainfall_mm"),
        )
        .filter(WeatherData.county_id.isnot(None))
    )
    # Use the most recent month of weather data
    latest_weather_date = db.query(func.max(WeatherData.observation_date)).scalar()
    if latest_weather_date:
        from datetime import timedelta as td
        weather_query = weather_query.filter(
            WeatherData.observation_date >= latest_weather_date - td(days=30)
        )
    weather_query = weather_query.group_by(WeatherData.county_id)
    weather_rows = weather_query.all()
    weather_map = {
        r.county_id: {"temp_avg": round(r.temp_avg, 1) if r.temp_avg is not None else None,
                      "rainfall_mm": round(r.rainfall_mm, 1) if r.rainfall_mm is not None else None}
        for r in weather_rows
    }

    # Build county_code -> county_id lookup
    county_lookup = {c.county_code: c.id for c in db.query(County).all()}

    return [
        TradingByCounty(
            county_code=r.county_code,
            county_name_zh=r.county_name_zh,
            avg_price=round(r.avg_price, 2) if r.avg_price else 0.0,
            volume=round(r.volume, 2) if r.volume else 0.0,
            temp_avg=weather_map.get(county_lookup.get(r.county_code), {}).get("temp_avg"),
            rainfall_mm=weather_map.get(county_lookup.get(r.county_code), {}).get("rainfall_mm"),
        )
        for r in rows
    ]


@router.get(
    "/{crop_key}/markets/{market_code}",
    response_model=List[TradingDataResponse],
)
def get_market_time_series(
    crop_key: str,
    market_code: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Retrieve trading time series for a specific crop at a specific market.
    """
    crop = _get_crop_or_404(db, crop_key)

    market = db.query(Market).filter(Market.market_code == market_code).first()
    if not market:
        raise HTTPException(
            status_code=404, detail=f"Market '{market_code}' not found"
        )

    query = (
        db.query(
            TradingData.id,
            TradingData.trade_date,
            TradingData.crop_name_raw,
            Market.market_code,
            Market.market_name,
            TradingData.price_high,
            TradingData.price_mid,
            TradingData.price_low,
            TradingData.price_avg,
            TradingData.volume,
        )
        .outerjoin(Market, TradingData.market_id == Market.id)
        .filter(TradingData.crop_id == crop.id)
        .filter(TradingData.market_id == market.id)
    )

    if start_date:
        query = query.filter(TradingData.trade_date >= start_date)
    if end_date:
        query = query.filter(TradingData.trade_date <= end_date)

    query = query.order_by(TradingData.trade_date.desc())
    rows = query.offset(skip).limit(limit).all()

    results = []
    for row in rows:
        results.append(
            TradingDataResponse(
                id=row.id,
                trade_date=row.trade_date,
                crop_name_raw=row.crop_name_raw,
                market_code=row.market_code or "",
                market_name=row.market_name or "",
                price_high=row.price_high or 0.0,
                price_mid=row.price_mid or 0.0,
                price_low=row.price_low or 0.0,
                price_avg=row.price_avg or 0.0,
                volume=row.volume or 0.0,
            )
        )
    return results
