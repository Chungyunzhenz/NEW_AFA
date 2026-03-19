from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

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
    metric: str = Query(
        "price_avg",
        description="Metric to aggregate: price_avg or volume",
        pattern="^(price_avg|volume)$",
    ),
    db: Session = Depends(get_db),
):
    """
    Aggregate trading data by county for choropleth map display.
    Groups through Market -> County relationship.
    """
    crop = _get_crop_or_404(db, crop_key)

    if metric == "volume":
        value_expr = func.sum(TradingData.volume)
    else:
        value_expr = func.avg(TradingData.price_avg)

    query = (
        db.query(
            County.county_code,
            County.county_name_zh,
            value_expr.label("value"),
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

    results = []
    for row in rows:
        results.append(
            TradingByCounty(
                county_code=row.county_code,
                county_name_zh=row.county_name_zh,
                value=round(row.value, 2) if row.value else 0.0,
                metric=metric,
            )
        )
    return results


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
