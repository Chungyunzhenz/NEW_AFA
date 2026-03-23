"""Batch rematch market_id for trading records with NULL market_id.

Phase A: Uses market_code_raw to look up market_id (fast, no API calls).
Phase B (--refetch): Re-fetches AMIS API data to recover missing market_code
         for old records that have no market_code_raw.

Usage:
    python scripts/rematch_market_ids.py --dry-run           # Phase A only, preview
    python scripts/rematch_market_ids.py                      # Phase A only, apply
    python scripts/rematch_market_ids.py --refetch --dry-run  # Phase A+B, preview
    python scripts/rematch_market_ids.py --refetch --start 2023-01-01 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import func, distinct  # noqa: E402

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.models import TradingData, Market  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def rematch_phase_a(
    db, market_lookup: Dict[str, int], dry_run: bool = False
) -> int:
    """Phase A: Rematch market_id using market_code_raw (fast, no API).

    Finds records where market_id IS NULL but market_code_raw IS NOT NULL,
    then looks up the market_code_raw in the market_lookup dict.

    Returns the number of records matched.
    """
    # Get distinct unmatched market_code_raw values with counts
    unmatched = (
        db.query(TradingData.market_code_raw, func.count().label("cnt"))
        .filter(
            TradingData.market_id.is_(None),
            TradingData.market_code_raw.isnot(None),
            TradingData.market_code_raw != "",
        )
        .group_by(TradingData.market_code_raw)
        .order_by(func.count().desc())
        .all()
    )

    if not unmatched:
        print("  Phase A: No records with market_code_raw but NULL market_id.")
        return 0

    total_matched = 0
    total_still_null = 0

    for raw_code, cnt in unmatched:
        market_id = market_lookup.get(raw_code)
        if market_id:
            total_matched += cnt
            if not dry_run:
                db.query(TradingData).filter(
                    TradingData.market_code_raw == raw_code,
                    TradingData.market_id.is_(None),
                ).update(
                    {TradingData.market_id: market_id},
                    synchronize_session=False,
                )
            action = "WOULD MATCH" if dry_run else "MATCHED"
            logger.info(
                "  %s: market_code_raw=%s -> market_id=%d (%d records)",
                action, raw_code, market_id, cnt,
            )
        else:
            total_still_null += cnt
            logger.warning(
                "  UNKNOWN: market_code_raw=%s not in markets table (%d records)",
                raw_code, cnt,
            )

    if not dry_run:
        db.commit()

    print(f"\n  Phase A Summary:")
    action = "Would match" if dry_run else "Matched"
    print(f"    {action}: {total_matched:,} records")
    print(f"    Unknown market codes: {total_still_null:,} records")

    return total_matched


def rematch_phase_b(
    db,
    collector: AMISDataCollector,
    market_lookup: Dict[str, int],
    start_date: date,
    end_date: date,
    dry_run: bool = False,
) -> int:
    """Phase B: Re-fetch AMIS API to recover market_code for old records.

    Finds distinct trade_dates where market_id IS NULL AND market_code_raw
    IS NULL, then re-fetches from the API and matches back by composite key
    (trade_date, crop_name_raw, price_avg, volume).

    Returns the number of records matched.
    """
    # Find dates with NULL market_id AND NULL market_code_raw
    null_dates = (
        db.query(distinct(TradingData.trade_date))
        .filter(
            TradingData.market_id.is_(None),
            (TradingData.market_code_raw.is_(None) | (TradingData.market_code_raw == "")),
            TradingData.trade_date >= start_date,
            TradingData.trade_date <= end_date,
        )
        .order_by(TradingData.trade_date)
        .all()
    )

    dates_to_fetch = [row[0] for row in null_dates]

    if not dates_to_fetch:
        print("  Phase B: No dates with NULL market_id AND NULL market_code_raw.")
        return 0

    print(f"  Phase B: {len(dates_to_fetch)} dates to re-fetch from API")
    print(f"    Range: {dates_to_fetch[0]} ~ {dates_to_fetch[-1]}")

    total_matched = 0
    total_dates = len(dates_to_fetch)

    for i, trade_date in enumerate(dates_to_fetch, 1):
        logger.info(
            "  [%d/%d] Re-fetching %s ...", i, total_dates, trade_date
        )

        api_data = collector._fetch_api(trade_date)
        if not api_data:
            continue

        # Build a lookup from API response: (crop_name_raw, price_avg, volume) -> market_code
        api_lookup: Dict[Tuple, str] = {}
        for row in api_data:
            crop_name = (row.get("作物名稱") or "").strip()
            market_code = str(row.get("市場代號") or "").strip()
            price_avg = _safe_float(row.get("平均價"))
            volume = _safe_float(row.get("交易量"))

            if crop_name and market_code:
                key = (crop_name, price_avg, volume)
                api_lookup[key] = market_code

        # Find DB records for this date that need fixing
        null_records = (
            db.query(TradingData)
            .filter(
                TradingData.trade_date == trade_date,
                TradingData.market_id.is_(None),
                (TradingData.market_code_raw.is_(None) | (TradingData.market_code_raw == "")),
            )
            .all()
        )

        matched_this_date = 0
        for record in null_records:
            key = (record.crop_name_raw, record.price_avg, record.volume)
            market_code = api_lookup.get(key)
            if market_code:
                market_id = market_lookup.get(market_code)
                if market_id and not dry_run:
                    record.market_id = market_id
                    record.market_code_raw = market_code
                if market_id:
                    matched_this_date += 1

        if matched_this_date > 0:
            logger.info(
                "    matched %d / %d records", matched_this_date, len(null_records)
            )

        total_matched += matched_this_date

        # Rate limit
        if i < total_dates:
            time.sleep(collector.RATE_LIMIT)

    if not dry_run:
        db.commit()

    print(f"\n  Phase B Summary:")
    action = "Would match" if dry_run else "Matched"
    print(f"    {action}: {total_matched:,} records from {total_dates} dates")

    return total_matched


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        collector = AMISDataCollector()
        market_lookup = collector.build_market_lookup(db)

        # Stats before
        total_null = db.query(func.count(TradingData.id)).filter(
            TradingData.market_id.is_(None)
        ).scalar() or 0
        total_records = db.query(func.count(TradingData.id)).scalar() or 0

        print(f"\n{'=' * 60}")
        print(f"  REMATCH MARKET IDS")
        print(f"{'=' * 60}")
        print(f"  Total records:          {total_records:>10,}")
        print(f"  NULL market_id before:  {total_null:>10,}  ({total_null/total_records*100:.1f}%)" if total_records else "")
        print(f"  Markets in lookup:      {len(market_lookup):>10}")

        if args.dry_run:
            print(f"\n  *** DRY RUN — no changes will be made ***")

        # Phase A
        print(f"\n{'─' * 60}")
        print(f"  Phase A: Rematch via market_code_raw")
        print(f"{'─' * 60}")
        matched_a = rematch_phase_a(db, market_lookup, dry_run=args.dry_run)

        # Phase B (optional)
        matched_b = 0
        if args.refetch:
            print(f"\n{'─' * 60}")
            print(f"  Phase B: Re-fetch from AMIS API")
            print(f"{'─' * 60}")

            start = args.start if args.start else date(2023, 1, 1)
            end = args.end if args.end else date.today() - timedelta(days=1)

            matched_b = rematch_phase_b(
                db, collector, market_lookup,
                start_date=start, end_date=end,
                dry_run=args.dry_run,
            )

        # Final stats
        if not args.dry_run:
            total_null_after = db.query(func.count(TradingData.id)).filter(
                TradingData.market_id.is_(None)
            ).scalar() or 0
        else:
            total_null_after = total_null - matched_a - matched_b

        print(f"\n{'=' * 60}")
        print(f"  FINAL SUMMARY")
        print(f"{'=' * 60}")
        action = "Would fix" if args.dry_run else "Fixed"
        print(f"  Phase A {action}: {matched_a:>10,} records")
        print(f"  Phase B {action}: {matched_b:>10,} records")
        print(f"  NULL market_id after:  {total_null_after:>10,}")

        if args.dry_run:
            print(f"\n  To apply changes, run without --dry-run")

    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch rematch market_id for trading records with NULL market_id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be matched without modifying the database.",
    )
    parser.add_argument(
        "--refetch",
        action="store_true",
        help="Enable Phase B: re-fetch AMIS API to recover missing market_code.",
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=None,
        help="Start date for Phase B re-fetch (YYYY-MM-DD, default: 2023-01-01).",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=None,
        help="End date for Phase B re-fetch (YYYY-MM-DD, default: yesterday).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
