"""Data quality audit for the Agriculture database.

Generates a comprehensive quality report covering:
- Table row counts and date ranges
- Trading data: NULL crop_id / market_id ratios, unmatched crop analysis
- Weather data: county coverage, NULL fields, date gaps
- CODiS CSV vs DB comparison
- Market gap analysis

Usage:
    python scripts/audit_data.py
    python scripts/audit_data.py --section trading
    python scripts/audit_data.py --section weather
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))
sys.path.insert(0, str(SCRIPTS_DIR))

from sqlalchemy import func  # noqa: E402

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.models import (  # noqa: E402
    TradingData, WeatherData, Crop, County, Market, ProductionData,
)
from app.services.weather_collector import STATION_COUNTY_MAP  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402
from import_codis_csv import parse_codis_csv  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

CODIS_DIR = PROJECT_ROOT / "data" / "codis_downloads"


# ===================================================================
# Section 1: Table Counts & Date Ranges
# ===================================================================
def audit_table_counts(db) -> None:
    """Print row counts and date ranges for all major tables."""
    print("\n" + "=" * 70)
    print("  TABLE COUNTS & DATE RANGES")
    print("=" * 70)

    # TradingData
    trading_count = db.query(func.count(TradingData.id)).scalar()
    trading_min = db.query(func.min(TradingData.trade_date)).scalar()
    trading_max = db.query(func.max(TradingData.trade_date)).scalar()
    print(f"\n  trading_data:    {trading_count:>10,} rows  ({trading_min} ~ {trading_max})")

    # WeatherData
    weather_count = db.query(func.count(WeatherData.id)).scalar()
    weather_min = db.query(func.min(WeatherData.observation_date)).scalar()
    weather_max = db.query(func.max(WeatherData.observation_date)).scalar()
    print(f"  weather_data:    {weather_count:>10,} rows  ({weather_min} ~ {weather_max})")

    # ProductionData
    prod_count = db.query(func.count(ProductionData.id)).scalar()
    prod_min_year = db.query(func.min(ProductionData.year)).scalar()
    prod_max_year = db.query(func.max(ProductionData.year)).scalar()
    print(f"  production_data: {prod_count:>10,} rows  (year {prod_min_year} ~ {prod_max_year})")

    # Crops, Counties, Markets
    crop_count = db.query(func.count(Crop.id)).scalar()
    county_count = db.query(func.count(County.id)).scalar()
    market_count = db.query(func.count(Market.id)).scalar()
    print(f"  crops:           {crop_count:>10,} rows")
    print(f"  counties:        {county_count:>10,} rows")
    print(f"  markets:         {market_count:>10,} rows")


# ===================================================================
# Section 2: Trading Data Audit
# ===================================================================
def audit_trading(db) -> None:
    """Audit trading data quality: NULL ratios, unmatched crops, market gaps."""
    print("\n" + "=" * 70)
    print("  TRADING DATA AUDIT")
    print("=" * 70)

    total = db.query(func.count(TradingData.id)).scalar()
    if total == 0:
        print("\n  (no trading data)")
        return

    # NULL crop_id
    null_crop = db.query(func.count(TradingData.id)).filter(
        TradingData.crop_id == None  # noqa: E711
    ).scalar()
    pct_null_crop = null_crop / total * 100 if total else 0

    # NULL market_id
    null_market = db.query(func.count(TradingData.id)).filter(
        TradingData.market_id == None  # noqa: E711
    ).scalar()
    pct_null_market = null_market / total * 100 if total else 0

    print(f"\n  Total records:       {total:>10,}")
    print(f"  NULL crop_id:        {null_crop:>10,}  ({pct_null_crop:.1f}%)")
    print(f"  NULL market_id:      {null_market:>10,}  ({pct_null_market:.1f}%)")

    # --- Per-crop counts ---
    print(f"\n  --- Per-Crop Record Counts ---")
    crop_counts = (
        db.query(Crop.crop_key, Crop.display_name_zh, func.count(TradingData.id))
        .join(TradingData, TradingData.crop_id == Crop.id)
        .group_by(Crop.id)
        .order_by(func.count(TradingData.id).desc())
        .all()
    )
    for crop_key, name_zh, cnt in crop_counts:
        print(f"    {name_zh:6s} ({crop_key:15s}): {cnt:>8,}")

    # --- Per-market counts ---
    print(f"\n  --- Per-Market Record Counts ---")
    market_counts = (
        db.query(Market.market_name, func.count(TradingData.id))
        .join(TradingData, TradingData.market_id == Market.id)
        .group_by(Market.id)
        .order_by(func.count(TradingData.id).desc())
        .all()
    )
    for name, cnt in market_counts:
        print(f"    {name:8s}: {cnt:>8,}")

    # --- TOP 30 unmatched crop names ---
    print(f"\n  --- TOP 30 Unmatched Crop Names (crop_id IS NULL) ---")
    top_unmatched = (
        db.query(TradingData.crop_name_raw, func.count().label("cnt"))
        .filter(TradingData.crop_id == None)  # noqa: E711
        .group_by(TradingData.crop_name_raw)
        .order_by(func.count().desc())
        .limit(30)
        .all()
    )
    for i, (name, cnt) in enumerate(top_unmatched, 1):
        print(f"    {i:2d}. {name:30s}  {cnt:>8,}")

    # --- Unmatched crop analysis (Phase 2A) ---
    analyze_unmatched_crops(db)

    # --- Market gap analysis (Phase 3B) ---
    audit_market_gaps(db)


def analyze_unmatched_crops(db) -> None:
    """Analyze unmatched crop names and suggest pattern expansions."""
    print(f"\n  --- Unmatched Crop Analysis (Pattern Matching) ---")

    collector = AMISDataCollector()
    crop_lookup = collector.build_crop_lookup(db)

    # All distinct unmatched names with counts
    unmatched_rows = (
        db.query(TradingData.crop_name_raw, func.count().label("cnt"))
        .filter(TradingData.crop_id == None)  # noqa: E711
        .group_by(TradingData.crop_name_raw)
        .order_by(func.count().desc())
        .all()
    )

    if not unmatched_rows:
        print("    No unmatched crop names found.")
        return

    # Get existing crops from DB for reverse lookup (crop_id -> crop_key)
    crop_rows = {c.id: c for c in db.query(Crop).all()}
    crop_id_to_key = {c.id: c.crop_key for c in crop_rows.values()}

    # Try to match each unmatched name by splitting on "-" and taking the
    # first segment (category name), then looking up in crop_lookup
    expandable: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
    brand_new: List[Tuple[str, int]] = []

    for raw_name, cnt in unmatched_rows:
        # Try direct match first (shouldn't match since it's unmatched, but sanity check)
        direct_match = collector._match_crop_id(raw_name, crop_lookup)
        if direct_match:
            continue

        # Split on "-" and try matching the first segment
        segments = raw_name.split("-")
        base_name = segments[0].strip()

        base_match = collector._match_crop_id(base_name, crop_lookup)
        if base_match:
            crop_key = crop_id_to_key.get(base_match, "?")
            expandable[crop_key].append((raw_name, cnt))
        else:
            brand_new.append((raw_name, cnt))

    # Print results
    if expandable:
        total_expandable = sum(cnt for items in expandable.values() for _, cnt in items)
        print(f"\n    [EXPANDABLE] Could match {total_expandable:,} records by adding patterns:")
        for crop_key, items in sorted(expandable.items(), key=lambda x: -sum(c for _, c in x[1])):
            subtotal = sum(cnt for _, cnt in items)
            print(f"\n      {crop_key} (+{subtotal:,} records):")
            # Collect suggested new patterns
            suggested_patterns = set()
            for raw_name, cnt in items[:15]:
                print(f"        - {raw_name:30s} ({cnt:>6,})")
                # The base_name already matches; suggest the full raw name as pattern
                # if it has a sub-variety suffix
                if "-" in raw_name:
                    suggested_patterns.add(raw_name.split("-")[0])
                else:
                    suggested_patterns.add(raw_name)
            if len(items) > 15:
                print(f"        ... and {len(items) - 15} more")
            # Show suggested patterns (deduplicated)
            existing_patterns = [p for p, cid in crop_lookup.items() if crop_id_to_key.get(cid) == crop_key]
            new_suggestions = suggested_patterns - set(existing_patterns)
            if new_suggestions:
                print(f"      -> Suggested new patterns: {sorted(new_suggestions)}")

    if brand_new:
        total_new = sum(cnt for _, cnt in brand_new)
        print(f"\n    [NEW CROPS] {len(brand_new)} names ({total_new:,} records) not matching any existing crop:")
        for raw_name, cnt in brand_new[:50]:
            print(f"        - {raw_name:30s} ({cnt:>6,})")
        if len(brand_new) > 50:
            print(f"        ... and {len(brand_new) - 50} more")


def audit_market_gaps(db) -> None:
    """Analyze market_id=NULL records and detect missing markets."""
    print(f"\n  --- Market Gap Analysis ---")

    null_market_count = db.query(func.count(TradingData.id)).filter(
        TradingData.market_id == None  # noqa: E711
    ).scalar()

    if null_market_count == 0:
        print("    No records with NULL market_id.")
        return

    print(f"    Total records with NULL market_id: {null_market_count:,}")
    print("    NOTE: Original market_code was not stored in DB (no market_code_raw column).")
    print("    After adding market_code_raw to the schema, new data will capture this field.")
    print("    To identify missing markets, fetch fresh AMIS data and compare market codes.")


# ===================================================================
# Section 3: Weather Data Audit
# ===================================================================
def audit_weather(db) -> None:
    """Audit weather data: county coverage, NULL fields, date gaps."""
    print("\n" + "=" * 70)
    print("  WEATHER DATA AUDIT")
    print("=" * 70)

    total = db.query(func.count(WeatherData.id)).scalar()
    if total == 0:
        print("\n  (no weather data)")
        return

    print(f"\n  Total records: {total:,}")

    # --- NULL field counts ---
    print(f"\n  --- NULL Field Counts ---")
    for col_name, col_attr in [
        ("temp_avg", WeatherData.temp_avg),
        ("temp_max", WeatherData.temp_max),
        ("temp_min", WeatherData.temp_min),
        ("rainfall_mm", WeatherData.rainfall_mm),
        ("humidity_pct", WeatherData.humidity_pct),
    ]:
        null_cnt = db.query(func.count(WeatherData.id)).filter(
            col_attr == None  # noqa: E711
        ).scalar()
        pct = null_cnt / total * 100 if total else 0
        print(f"    {col_name:15s}: {null_cnt:>8,} NULL ({pct:.1f}%)")

    # --- Per-county coverage ---
    print(f"\n  --- Per-County Coverage ---")
    county_coverage = (
        db.query(
            County.county_name_zh,
            func.count(WeatherData.id),
            func.min(WeatherData.observation_date),
            func.max(WeatherData.observation_date),
        )
        .outerjoin(WeatherData, WeatherData.county_id == County.id)
        .group_by(County.id)
        .order_by(func.count(WeatherData.id).desc())
        .all()
    )
    for name, cnt, min_date, max_date in county_coverage:
        if cnt > 0:
            print(f"    {name:6s}: {cnt:>6,} records  ({min_date} ~ {max_date})")
        else:
            print(f"    {name:6s}:      0 records  (NO DATA)")

    # --- Date gaps (for counties with data) ---
    print(f"\n  --- Date Gaps (counties with >100 records) ---")
    for name, cnt, min_date, max_date in county_coverage:
        if cnt < 100 or min_date is None or max_date is None:
            continue

        county_id = db.query(County.id).filter(County.county_name_zh == name).scalar()
        dates_in_db = set(
            row[0] for row in
            db.query(WeatherData.observation_date)
            .filter(WeatherData.county_id == county_id)
            .all()
        )

        # Calculate expected dates
        expected = set()
        d = min_date
        while d <= max_date:
            expected.add(d)
            d += timedelta(days=1)

        missing = sorted(expected - dates_in_db)
        if missing:
            # Summarize gaps as ranges
            gaps = _summarize_date_gaps(missing)
            print(f"    {name}: {len(missing)} missing days, {len(gaps)} gap(s)")
            for gap_start, gap_end, gap_len in gaps[:5]:
                if gap_len == 1:
                    print(f"      - {gap_start}")
                else:
                    print(f"      - {gap_start} ~ {gap_end} ({gap_len} days)")
            if len(gaps) > 5:
                print(f"      ... and {len(gaps) - 5} more gaps")
        else:
            print(f"    {name}: complete coverage ({min_date} ~ {max_date})")


def _summarize_date_gaps(missing_dates: List[date]) -> List[Tuple[date, date, int]]:
    """Summarize a sorted list of missing dates into contiguous gap ranges."""
    if not missing_dates:
        return []
    gaps = []
    gap_start = missing_dates[0]
    prev = missing_dates[0]
    for d in missing_dates[1:]:
        if d - prev > timedelta(days=1):
            gaps.append((gap_start, prev, (prev - gap_start).days + 1))
            gap_start = d
        prev = d
    gaps.append((gap_start, prev, (prev - gap_start).days + 1))
    return gaps


# ===================================================================
# Section 4: CODiS CSV vs DB Comparison
# ===================================================================
def audit_codis_vs_db(db) -> None:
    """Compare CODiS CSV files in data/codis_downloads/ with weather_data in DB."""
    print("\n" + "=" * 70)
    print("  CODiS CSV vs DB COMPARISON")
    print("=" * 70)

    if not CODIS_DIR.is_dir():
        print(f"\n  CODiS directory not found: {CODIS_DIR}")
        return

    csv_files = sorted(CODIS_DIR.glob("*.csv"))
    if not csv_files:
        print(f"\n  No CSV files in {CODIS_DIR}")
        return

    print(f"\n  Found {len(csv_files)} CSV file(s) in {CODIS_DIR}")

    # Build county lookup
    county_lookup = {c.county_code: c.id for c in db.query(County).all()}
    county_names = {c.county_code: c.county_name_zh for c in db.query(County).all()}

    total_csv_records = 0
    total_in_db = 0
    total_missing = 0

    for csv_file in csv_files:
        station_id, records = parse_codis_csv(csv_file)
        if not station_id or not records:
            print(f"\n    {csv_file.name}: skipped (no station ID or no records)")
            continue

        county_code = STATION_COUNTY_MAP.get(station_id)
        if not county_code:
            print(f"\n    {csv_file.name}: station {station_id} not in STATION_COUNTY_MAP")
            continue

        county_id = county_lookup.get(county_code)
        county_name = county_names.get(county_code, "?")

        # Check how many of these dates are already in DB
        csv_dates = {r["observation_date"] for r in records}
        total_csv_records += len(csv_dates)

        if county_id:
            db_dates = set(
                row[0] for row in
                db.query(WeatherData.observation_date)
                .filter(
                    WeatherData.county_id == county_id,
                    WeatherData.observation_date.in_(list(csv_dates)),
                )
                .all()
            )
        else:
            db_dates = set()

        in_db = len(csv_dates & db_dates)
        missing = len(csv_dates - db_dates)
        total_in_db += in_db
        total_missing += missing

        date_range = f"{min(csv_dates)} ~ {max(csv_dates)}"
        status = "ALL IN DB" if missing == 0 else f"{missing} NOT in DB"
        print(
            f"    {csv_file.name:30s}  station={station_id}  county={county_name:4s}  "
            f"records={len(csv_dates):>5}  ({date_range})  [{status}]"
        )

    print(f"\n  Summary:")
    print(f"    Total CSV records:   {total_csv_records:>8,}")
    print(f"    Already in DB:       {total_in_db:>8,}")
    print(f"    Missing from DB:     {total_missing:>8,}")
    if total_missing > 0:
        print(f"    -> Run: python scripts/import_codis_csv.py --input-dir data/codis_downloads/")


# ===================================================================
# Section 5: Join Chain Completeness
# ===================================================================
def audit_join_chain(db) -> None:
    """Audit the full join chain: TradingData -> Market -> County -> WeatherData."""
    print("\n" + "=" * 70)
    print("  JOIN CHAIN COMPLETENESS")
    print("=" * 70)

    total = db.query(func.count(TradingData.id)).scalar()
    if total == 0:
        print("\n  (no trading data)")
        return

    # 1. Total trading records
    print(f"\n  1. Total trading records:           {total:>10,}")

    # 2. Records with market_id
    has_market = db.query(func.count(TradingData.id)).filter(
        TradingData.market_id.isnot(None)
    ).scalar()
    pct_market = has_market / total * 100
    print(f"  2. Has market_id:                   {has_market:>10,}  ({pct_market:.1f}%)")

    # 3. Can join to County (market has county_id)
    can_join_county = (
        db.query(func.count(TradingData.id))
        .join(Market, TradingData.market_id == Market.id)
        .filter(Market.county_id.isnot(None))
        .scalar()
    )
    pct_county = can_join_county / total * 100
    print(f"  3. Can join to County:              {can_join_county:>10,}  ({pct_county:.1f}%)")

    # 4. Full join chain (has matching weather data on same date)
    full_chain = (
        db.query(func.count(func.distinct(TradingData.id)))
        .join(Market, TradingData.market_id == Market.id)
        .join(County, Market.county_id == County.id)
        .join(
            WeatherData,
            (WeatherData.county_id == County.id)
            & (WeatherData.observation_date == TradingData.trade_date),
        )
        .scalar()
    )
    pct_full = full_chain / total * 100
    print(f"  4. Full chain (with weather):       {full_chain:>10,}  ({pct_full:.1f}%)")

    # 5. Breakdown of where the chain breaks
    null_market = total - has_market
    null_county = has_market - can_join_county
    no_weather = can_join_county - full_chain

    print(f"\n  --- Chain Break Analysis ---")
    print(f"    NULL market_id:                   {null_market:>10,}  ({null_market/total*100:.1f}%)")
    print(f"    Market has no county_id:          {null_county:>10,}  ({null_county/total*100:.1f}%)")
    print(f"    No weather data for date+county:  {no_weather:>10,}  ({no_weather/total*100:.1f}%)")

    # 6. Per-county join detail
    print(f"\n  --- Per-County Join Detail ---")
    county_detail = (
        db.query(
            County.county_name_zh,
            func.count(func.distinct(TradingData.id)).label("trading_cnt"),
            func.count(func.distinct(WeatherData.id)).label("weather_cnt"),
        )
        .select_from(TradingData)
        .join(Market, TradingData.market_id == Market.id)
        .join(County, Market.county_id == County.id)
        .outerjoin(
            WeatherData,
            (WeatherData.county_id == County.id)
            & (WeatherData.observation_date == TradingData.trade_date),
        )
        .group_by(County.county_code, County.county_name_zh)
        .order_by(func.count(func.distinct(TradingData.id)).desc())
        .all()
    )
    print(f"    {'County':8s}  {'Trading':>10s}  {'Has Weather':>12s}  {'Coverage':>8s}")
    print(f"    {'─' * 8}  {'─' * 10}  {'─' * 12}  {'─' * 8}")
    for name, t_cnt, w_cnt in county_detail:
        # w_cnt counts distinct weather rows joined — approximate
        # For exact "trading records with weather", we'd need a subquery;
        # this gives a good overview.
        pct = "N/A"
        if t_cnt > 0:
            # Count trading records that actually have matching weather
            matched = (
                db.query(func.count(func.distinct(TradingData.id)))
                .join(Market, TradingData.market_id == Market.id)
                .join(County, Market.county_id == County.id)
                .join(
                    WeatherData,
                    (WeatherData.county_id == County.id)
                    & (WeatherData.observation_date == TradingData.trade_date),
                )
                .filter(County.county_name_zh == name)
                .scalar()
            ) or 0
            pct = f"{matched/t_cnt*100:.0f}%"
            print(f"    {name:8s}  {t_cnt:>10,}  {matched:>12,}  {pct:>8s}")
        else:
            print(f"    {name:8s}  {t_cnt:>10,}  {'—':>12s}  {'—':>8s}")


# ===================================================================
# Main
# ===================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Data quality audit for the Agriculture database.",
    )
    parser.add_argument(
        "--section",
        type=str,
        default=None,
        choices=["counts", "trading", "weather", "codis", "chain"],
        help="Run only a specific audit section (default: all).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        print("\n" + "#" * 70)
        print("#  AGRICULTURE DATABASE - DATA QUALITY AUDIT")
        print("#" * 70)

        sections = {
            "counts": audit_table_counts,
            "trading": audit_trading,
            "weather": audit_weather,
            "codis": audit_codis_vs_db,
            "chain": audit_join_chain,
        }

        if args.section:
            sections[args.section](db)
        else:
            for section_fn in sections.values():
                section_fn(db)

        print("\n" + "=" * 70)
        print("  AUDIT COMPLETE")
        print("=" * 70 + "\n")
    finally:
        db.close()


if __name__ == "__main__":
    main()
