import json
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.region import County, Market
from ...schemas.region import CountyResponse, MarketResponse

router = APIRouter()

# Resolve the geojson file path relative to this module
_GEOJSON_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "geojson"


@router.get("/counties", response_model=List[CountyResponse])
def list_counties(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all counties."""
    counties = (
        db.query(County)
        .order_by(County.county_code)
        .offset(skip)
        .limit(min(limit, 1000))
        .all()
    )
    results = []
    for c in counties:
        results.append(
            CountyResponse(
                id=c.id,
                county_code=c.county_code,
                county_name_zh=c.county_name_zh,
                county_name_en=c.county_name_en or "",
            )
        )
    return results


@router.get("/markets", response_model=List[MarketResponse])
def list_markets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all markets with their county name joined."""
    query = (
        db.query(
            Market.id,
            Market.market_code,
            Market.market_name,
            Market.county_id,
            County.county_name_zh,
        )
        .outerjoin(County, Market.county_id == County.id)
        .order_by(Market.market_code)
        .offset(skip)
        .limit(min(limit, 1000))
    )
    rows = query.all()
    results = []
    for row in rows:
        results.append(
            MarketResponse(
                id=row.id,
                market_code=row.market_code,
                market_name=row.market_name,
                county_id=row.county_id or 0,
                county_name_zh=row.county_name_zh,
            )
        )
    return results


@router.get("/geojson")
def get_geojson():
    """Serve the Taiwan counties TopoJSON / GeoJSON file."""
    geojson_path = _GEOJSON_DIR / "taiwan_counties.json"
    if not geojson_path.exists():
        raise HTTPException(
            status_code=404,
            detail="GeoJSON file not found. Please place taiwan_counties.json in data/geojson/.",
        )
    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return JSONResponse(content=data)
