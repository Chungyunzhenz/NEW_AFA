"""Backfill production_data from the MOA TownCropData API.

Fetches annual crop production statistics (種植面積, 收穫面積, 產量)
from the government open data API, aggregates township-level data to
county level, matches crop names to crop_id, and inserts into the
production_data table.

API source: https://data.gov.tw/dataset/7302
Endpoint:   https://data.moa.gov.tw/Service/OpenData/FromM/TownCropData.aspx

Usage:
    python scripts/backfill_production.py --dry-run
    python scripts/backfill_production.py
    python scripts/backfill_production.py --start-year 2005 --end-year 2024
    python scripts/backfill_production.py --crop cabbage --year 2023
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

import requests

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import func  # noqa: E402

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.config import settings, load_crop_configs  # noqa: E402
from app.models import ProductionData, Crop, County  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API config
# ---------------------------------------------------------------------------
API_URL = "https://data.moa.gov.tw/Service/OpenData/FromM/TownCropData.aspx"
RATE_LIMIT = 1.0  # seconds between API calls

# ---------------------------------------------------------------------------
# County name normalization (API 縣市 -> DB county_name_zh)
# ---------------------------------------------------------------------------
COUNTY_NAME_MAP = {
    "台北市": "臺北市", "台中市": "臺中市", "台南市": "臺南市",
    "台東縣": "臺東縣",
}

# ---------------------------------------------------------------------------
# Crop name matching for production API
# The API 作物 field uses different naming than AMIS trading data.
# We build patterns from crop configs + add production-specific aliases.
# ---------------------------------------------------------------------------
PRODUCTION_CROP_ALIASES: Dict[str, List[str]] = {
    "rice": ["稻", "水稻", "稻米", "稻穀", "蓬萊稻", "在來稻", "糯稻"],
    "cabbage": ["甘藍", "高麗菜", "包心菜"],
    "banana": ["香蕉"],
    "watermelon": ["西瓜"],
    "guava": ["番石榴", "芭樂"],
    "papaya": ["木瓜"],
    "mango": ["芒果", "檬果", "改良種芒果", "本地種芒果"],
    "citrus": ["柑橘", "椪柑", "桶柑", "茂谷柑", "柳橙", "柳丁", "柑桔"],
    "grape": ["葡萄"],
    "lettuce": ["萵苣", "A菜", "大陸妹"],
    "spinach": ["菠菜", "菠薐菜"],
    "green_onion": ["青蔥", "蔥"],
    "garlic": ["蒜頭", "大蒜", "蒜"],
    "bamboo_shoot": ["竹筍", "筍"],
    "tomato": ["番茄", "食用番茄", "加工番茄"],
    "chili_pepper": ["辣椒"],
    "radish": ["蘿蔔"],
    "sweet_potato": ["甘藷", "甘薯", "番薯", "地瓜"],
    "pineapple": ["鳳梨"],
    "bitter_gourd": ["苦瓜"],
}


def build_crop_name_lookup(db) -> Dict[str, int]:
    """Build a mapping of production crop name pattern -> crop_id.

    Combines patterns from crop configs and PRODUCTION_CROP_ALIASES.
    """
    crop_rows = {c.crop_key: c.id for c in db.query(Crop).all()}
    lookup: Dict[str, int] = {}

    # From crop config amis_crop_name_patterns
    configs = load_crop_configs()
    for key, cfg in configs.items():
        crop_id = crop_rows.get(key)
        if crop_id is None:
            continue
        for pattern in cfg.get("amis_crop_name_patterns", []):
            lookup[pattern] = crop_id

    # From production-specific aliases
    for crop_key, aliases in PRODUCTION_CROP_ALIASES.items():
        crop_id = crop_rows.get(crop_key)
        if crop_id is None:
            continue
        for alias in aliases:
            lookup[alias] = crop_id

    return lookup


def match_crop_id(crop_name: str, lookup: Dict[str, int]) -> Optional[int]:
    """Match a production API crop name to a crop_id.

    Tries exact match first, then longest-prefix match.
    """
    crop_name = crop_name.strip()

    # Exact match
    if crop_name in lookup:
        return lookup[crop_name]

    # Longest prefix match
    sorted_patterns = sorted(lookup.keys(), key=len, reverse=True)
    for pattern in sorted_patterns:
        if crop_name.startswith(pattern):
            return lookup[pattern]

    return None


def build_county_lookup(db) -> Dict[str, int]:
    """Build mapping of county_name_zh -> county_id, including aliases."""
    base = {c.county_name_zh: c.id for c in db.query(County).all()}

    # Add common aliases
    result = dict(base)
    for alias, canonical in COUNTY_NAME_MAP.items():
        if canonical in base:
            result[alias] = base[canonical]

    return result


def _fetch_page(roc_year: int, skip: int = 0, top: int = 9999) -> List[Dict[str, Any]]:
    """Fetch a single page of production records from the API."""
    params = {
        "IsTransData": "1",
        "UnitId": "038",
        "Year": str(roc_year),
        "$top": str(top),
        "$skip": str(skip),
    }

    try:
        resp = requests.get(
            API_URL,
            params=params,
            timeout=60,
            verify=settings.VERIFY_SSL,
        )
        resp.raise_for_status()

        if not resp.text.strip():
            return []

        data = resp.json()
        if not isinstance(data, list):
            return []

        return data
    except requests.RequestException as exc:
        logger.error("HTTP error fetching year %d (skip=%d): %s", roc_year, skip, exc)
        return []
    except (ValueError, json.JSONDecodeError) as exc:
        logger.error("JSON decode error for year %d (skip=%d): %s", roc_year, skip, exc)
        return []


def fetch_year_data(roc_year: int) -> List[Dict[str, Any]]:
    """Fetch ALL production records for a single ROC year, handling pagination.

    The API returns max 9,999 records per request. We use $skip/$top
    to paginate through the full dataset.
    """
    PAGE_SIZE = 9999
    all_data: List[Dict[str, Any]] = []
    skip = 0

    while True:
        page = _fetch_page(roc_year, skip=skip, top=PAGE_SIZE)
        if not page:
            break

        all_data.extend(page)
        logger.info(
            "    page skip=%d: got %d records (total so far: %d)",
            skip, len(page), len(all_data),
        )

        if len(page) < PAGE_SIZE:
            break  # last page

        skip += PAGE_SIZE
        time.sleep(0.5)  # brief pause between pages

    return all_data


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(str(value).replace(",", "").strip())
        return v if v >= 0 else None
    except (TypeError, ValueError):
        return None


def aggregate_to_county(
    records: List[Dict[str, Any]],
    crop_lookup: Dict[str, int],
    county_lookup: Dict[str, int],
) -> List[Dict[str, Any]]:
    """Aggregate township-level API data to county level.

    Only uses 期作="全年" records to avoid double-counting.
    Groups by (year, county, crop_id) and sums area/production.

    Returns a list of dicts ready for DB insertion.
    """
    # Key: (western_year, county_id, crop_id)
    agg: Dict[Tuple, Dict[str, float]] = defaultdict(
        lambda: {"planted_area_ha": 0.0, "harvest_area_ha": 0.0,
                 "production_kg": 0.0}
    )
    skipped_crop = set()
    skipped_county = set()

    for row in records:
        # Only use 全年 (full year) to avoid double counting seasons
        period = (row.get("期作") or "").strip()
        if period != "全年":
            continue

        crop_name = (row.get("作物") or "").strip()
        if not crop_name:
            continue

        crop_id = match_crop_id(crop_name, crop_lookup)
        if crop_id is None:
            skipped_crop.add(crop_name)
            continue

        county_name = (row.get("縣市") or "").strip()
        county_id = county_lookup.get(county_name)
        if county_id is None:
            skipped_county.add(county_name)
            continue

        roc_year = int(row.get("年度", 0))
        western_year = roc_year + 1911

        planted = safe_float(row.get("種植面積(公頃)")) or 0.0
        harvest = safe_float(row.get("收穫面積(公頃)")) or 0.0
        production_kg = safe_float(row.get("收量(公斤)")) or 0.0

        key = (western_year, county_id, crop_id)
        agg[key]["planted_area_ha"] += planted
        agg[key]["harvest_area_ha"] += harvest
        agg[key]["production_kg"] += production_kg

    # Convert to DB-ready records
    results = []
    for (year, county_id, crop_id), vals in agg.items():
        production_tonnes = vals["production_kg"] / 1000.0
        harvest_ha = vals["harvest_area_ha"]
        yield_per_ha = (
            (vals["production_kg"] / harvest_ha) if harvest_ha > 0 else None
        )

        results.append({
            "year": year,
            "month": None,
            "crop_id": crop_id,
            "county_id": county_id,
            "planted_area_ha": round(vals["planted_area_ha"], 4),
            "harvest_area_ha": round(harvest_ha, 4),
            "production_tonnes": round(production_tonnes, 4),
            "yield_per_ha": round(yield_per_ha, 2) if yield_per_ha else None,
        })

    if skipped_crop:
        logger.debug(
            "  Unmatched crop names (sample): %s",
            list(skipped_crop)[:10],
        )

    return results


def backfill_year(
    db, year: int, crop_lookup: Dict[str, int],
    county_lookup: Dict[str, int],
    crop_filter: Optional[str] = None,
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Fetch and insert production data for a single western year.

    Returns (inserted, skipped).
    """
    roc_year = year - 1911
    logger.info("Fetching year %d (ROC %d) ...", year, roc_year)

    raw_data = fetch_year_data(roc_year)
    if not raw_data:
        logger.info("  No data returned for %d", year)
        return 0, 0

    logger.info("  API returned %d township records", len(raw_data))

    aggregated = aggregate_to_county(raw_data, crop_lookup, county_lookup)
    logger.info("  Aggregated to %d county-level records", len(aggregated))

    # Optional crop filter
    if crop_filter:
        crop_obj = db.query(Crop).filter(Crop.crop_key == crop_filter).first()
        if crop_obj:
            aggregated = [r for r in aggregated if r["crop_id"] == crop_obj.id]
            logger.info("  Filtered to %d records for crop=%s", len(aggregated), crop_filter)

    inserted = 0
    skipped = 0

    for record in aggregated:
        # Check for existing record
        existing = (
            db.query(ProductionData.id)
            .filter(
                ProductionData.year == record["year"],
                ProductionData.month == record["month"],
                ProductionData.crop_id == record["crop_id"],
                ProductionData.county_id == record["county_id"],
            )
            .first()
        )
        if existing:
            skipped += 1
            continue

        if not dry_run:
            db.add(ProductionData(**record))

        inserted += 1

    if not dry_run and inserted > 0:
        db.commit()

    return inserted, skipped


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        crop_lookup = build_crop_name_lookup(db)
        county_lookup = build_county_lookup(db)

        # Determine year range
        start_year = args.start_year
        end_year = args.end_year
        if args.year:
            start_year = args.year
            end_year = args.year

        total_inserted = 0
        total_skipped = 0
        years = list(range(start_year, end_year + 1))

        print(f"\n{'=' * 60}")
        print(f"  BACKFILL PRODUCTION DATA")
        print(f"{'=' * 60}")
        print(f"  Year range:     {start_year} ~ {end_year} ({len(years)} years)")
        print(f"  Crop filter:    {args.crop or 'all'}")
        print(f"  Crop patterns:  {len(crop_lookup)}")
        print(f"  Counties:       {len(county_lookup)}")

        if args.dry_run:
            print(f"\n  *** DRY RUN — no changes will be made ***")

        print()

        for i, year in enumerate(years):
            inserted, skipped = backfill_year(
                db, year, crop_lookup, county_lookup,
                crop_filter=args.crop, dry_run=args.dry_run,
            )
            total_inserted += inserted
            total_skipped += skipped

            action = "would insert" if args.dry_run else "inserted"
            logger.info(
                "  Year %d: %s %d, skipped %d existing",
                year, action, inserted, skipped,
            )

            # Rate limit between API calls
            if i < len(years) - 1:
                time.sleep(RATE_LIMIT)

        # Final summary
        print(f"\n{'=' * 60}")
        print(f"  SUMMARY")
        print(f"{'=' * 60}")
        action = "Would insert" if args.dry_run else "Inserted"
        print(f"  {action}:  {total_inserted:>8,} records")
        print(f"  Skipped (existing): {total_skipped:>8,} records")

        # Show final DB count
        if not args.dry_run:
            final_count = db.query(func.count(ProductionData.id)).scalar()
            print(f"  Total in DB:        {final_count:>8,} records")

        if args.dry_run:
            print(f"\n  To apply changes, run without --dry-run")

    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    current_year = date.today().year
    parser = argparse.ArgumentParser(
        description="Backfill production_data from MOA TownCropData API.",
    )
    parser.add_argument(
        "--start-year", type=int, default=2005,
        help="Start year, western calendar (default: 2005).",
    )
    parser.add_argument(
        "--end-year", type=int, default=current_year - 1,
        help=f"End year, western calendar (default: {current_year - 1}).",
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="Fetch a single year only (overrides --start-year/--end-year).",
    )
    parser.add_argument(
        "--crop", type=str, default=None,
        help="Filter by crop_key (e.g. 'cabbage'). Default: all crops.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview without modifying the database.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
