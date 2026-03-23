"""Batch rematch crop_id for trading records with NULL crop_id.

Reads the current crop config patterns and attempts to match
every distinct crop_name_raw that currently has crop_id=NULL.
Updates matching records in bulk.

Usage:
    python scripts/rematch_crop_ids.py --dry-run
    python scripts/rematch_crop_ids.py
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import func  # noqa: E402

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.models import TradingData, Crop  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def rematch(db, dry_run: bool = False) -> None:
    """Rematch crop_id for all trading records where crop_id IS NULL."""
    collector = AMISDataCollector()
    crop_lookup = collector.build_crop_lookup(db)

    # Reverse lookup for display
    crop_rows = {c.id: c for c in db.query(Crop).all()}

    # Get distinct unmatched crop names with counts
    unmatched = (
        db.query(TradingData.crop_name_raw, func.count().label("cnt"))
        .filter(TradingData.crop_id == None)  # noqa: E711
        .group_by(TradingData.crop_name_raw)
        .order_by(func.count().desc())
        .all()
    )

    total_before = db.query(func.count(TradingData.id)).filter(
        TradingData.crop_id == None  # noqa: E711
    ).scalar()

    print(f"\nTotal records with NULL crop_id: {total_before:,}")
    print(f"Distinct unmatched crop names:   {len(unmatched):,}")
    print(f"Crop patterns in lookup:         {len(crop_lookup):,}")

    if dry_run:
        print("\n*** DRY RUN — no changes will be made ***\n")

    matched_names = 0
    matched_records = 0
    still_unmatched_names = 0
    still_unmatched_records = 0

    for raw_name, cnt in unmatched:
        crop_id = collector._match_crop_id(raw_name, crop_lookup)
        if crop_id:
            crop_obj = crop_rows.get(crop_id)
            crop_key = crop_obj.crop_key if crop_obj else "?"
            matched_names += 1
            matched_records += cnt

            if not dry_run:
                db.query(TradingData).filter(
                    TradingData.crop_name_raw == raw_name,
                    TradingData.crop_id == None,  # noqa: E711
                ).update(
                    {TradingData.crop_id: crop_id},
                    synchronize_session=False,
                )

            action = "WOULD MATCH" if dry_run else "MATCHED"
            logger.info(
                "  %s: %s -> %s (%d records)",
                action, raw_name, crop_key, cnt,
            )
        else:
            still_unmatched_names += 1
            still_unmatched_records += cnt

    if not dry_run:
        db.commit()
        logger.info("Changes committed.")

    # Summary
    print("\n" + "=" * 60)
    print("REMATCH SUMMARY")
    print("=" * 60)
    action = "Would match" if dry_run else "Matched"
    print(f"  {action}:        {matched_names:>6} names  ({matched_records:>10,} records)")
    print(f"  Still unmatched: {still_unmatched_names:>6} names  ({still_unmatched_records:>10,} records)")

    if dry_run:
        print(f"\n  To apply changes, run without --dry-run")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch rematch crop_id for trading records with NULL crop_id.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be matched without modifying the database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        rematch(db, dry_run=args.dry_run)
    finally:
        db.close()


if __name__ == "__main__":
    main()
