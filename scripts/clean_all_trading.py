"""Batch clean trading data for all active crops.

Runs the TradingDataCleaner pipeline on each crop and optionally on
unmatched (crop_id=NULL) records.

Usage:
    python scripts/clean_all_trading.py --dry-run
    python scripts/clean_all_trading.py --crop rice --dry-run
    python scripts/clean_all_trading.py --include-unmatched
    python scripts/clean_all_trading.py
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
from app.services.data_cleaner import TradingDataCleaner, CleaningStats  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def clean_all(
    db,
    crop_key: str | None = None,
    include_unmatched: bool = False,
    dry_run: bool = False,
) -> None:
    """Clean trading data for all active crops."""
    cleaner = TradingDataCleaner()
    crops = db.query(Crop).filter(Crop.is_active == True).all()  # noqa: E712

    if crop_key:
        crops = [c for c in crops if c.crop_key == crop_key]
        if not crops:
            print(f"ERROR: Crop '{crop_key}' not found or not active.")
            return

    if dry_run:
        print("\n*** DRY RUN — showing what would be cleaned ***\n")

    total_stats = CleaningStats()
    print(f"\nCleaning {len(crops)} crop(s)...\n")
    print(f"{'Crop':20s} {'Total':>8s} {'Invalid':>8s} {'Dups':>8s} {'ZeroVol':>8s} {'Outliers':>8s} {'After':>8s}")
    print("-" * 80)

    for crop in crops:
        if dry_run:
            # Dry run: scan records and report what would be cleaned
            records = (
                db.query(TradingData)
                .filter(TradingData.crop_id == crop.id)
                .order_by(TradingData.trade_date)
                .all()
            )
            count = len(records)
            invalid_count = sum(1 for r in records if cleaner.validate_record(r))
            zero_vol_count = sum(1 for r in records if r.volume is not None and r.volume == 0)
            # Count duplicates
            seen = {}
            dup_count = 0
            for r in records:
                key = (r.trade_date, r.crop_name_raw, r.market_id)
                if key in seen:
                    dup_count += 1
                else:
                    seen[key] = True
            print(
                f"{crop.crop_key:20s} {count:>8,} "
                f"{invalid_count:>8,} {dup_count:>8,} "
                f"{zero_vol_count:>8,} {'?':>8s} "
                f"{'?':>8s}"
            )
            total_stats.total_records += count
            total_stats.invalid_removed += invalid_count
            total_stats.duplicates_removed += dup_count
            total_stats.zero_volume_removed += zero_vol_count
            db.expire_all()  # release memory
        else:
            stats = cleaner.clean_trading_data(db, crop_id=crop.id)
            print(
                f"{crop.crop_key:20s} {stats.total_records:>8,} "
                f"{stats.invalid_removed:>8,} {stats.duplicates_removed:>8,} "
                f"{stats.zero_volume_removed:>8,} {stats.outliers_flagged:>8,} "
                f"{stats.records_after_cleaning:>8,}"
            )
            total_stats.total_records += stats.total_records
            total_stats.invalid_removed += stats.invalid_removed
            total_stats.duplicates_removed += stats.duplicates_removed
            total_stats.zero_volume_removed += stats.zero_volume_removed
            total_stats.outliers_flagged += stats.outliers_flagged
            total_stats.records_after_cleaning += stats.records_after_cleaning

    print("-" * 80)
    if dry_run:
        print(
            f"{'TOTAL':20s} {total_stats.total_records:>8,} "
            f"{total_stats.invalid_removed:>8,} {total_stats.duplicates_removed:>8,} "
            f"{total_stats.zero_volume_removed:>8,} {'?':>8s} "
            f"{'?':>8s}"
        )
        print("\n  (dry-run: outliers and final counts require actual cleaning)")
    else:
        print(
            f"{'TOTAL':20s} {total_stats.total_records:>8,} "
            f"{total_stats.invalid_removed:>8,} {total_stats.duplicates_removed:>8,} "
            f"{total_stats.zero_volume_removed:>8,} {total_stats.outliers_flagged:>8,} "
            f"{total_stats.records_after_cleaning:>8,}"
        )

    if include_unmatched:
        print("\n" + "=" * 60)
        print("Cleaning unmatched records (crop_id IS NULL)...")
        clean_unmatched(db, cleaner, dry_run)


def clean_unmatched(db, cleaner: TradingDataCleaner, dry_run: bool = False) -> None:
    """Clean trading records with crop_id=NULL.

    Only performs basic validation and duplicate/zero-volume removal.
    Outlier detection is skipped (no crop grouping available).
    Processes in batches to control memory usage.
    """
    total = db.query(func.count(TradingData.id)).filter(
        TradingData.crop_id == None  # noqa: E711
    ).scalar()

    if total == 0:
        print("  No unmatched records found.")
        return

    print(f"  Total unmatched records: {total:,}")

    BATCH = 5000

    if dry_run:
        # Count potential issues without modifying, processing in batches
        invalid_count = 0
        zero_vol_count = 0
        offset = 0
        while offset < total:
            batch = (
                db.query(TradingData)
                .filter(TradingData.crop_id == None)  # noqa: E711
                .order_by(TradingData.id)
                .offset(offset).limit(BATCH)
                .all()
            )
            for rec in batch:
                if cleaner.validate_record(rec):
                    invalid_count += 1
                if rec.volume is not None and rec.volume == 0:
                    zero_vol_count += 1
            offset += BATCH
            db.expire_all()
        print(f"  Would remove invalid:    {invalid_count:,}")
        print(f"  Would remove zero-vol:   {zero_vol_count:,}")
        print(f"  (dry-run: no changes)")
        return

    # Step 1: Validate and remove invalid records
    ids_to_delete = []
    offset = 0
    while True:
        batch = (
            db.query(TradingData)
            .filter(TradingData.crop_id == None)  # noqa: E711
            .order_by(TradingData.id)
            .offset(offset).limit(BATCH)
            .all()
        )
        if not batch:
            break
        for rec in batch:
            if cleaner.validate_record(rec):
                ids_to_delete.append(rec.id)
        offset += BATCH
        db.expire_all()

    if ids_to_delete:
        for i in range(0, len(ids_to_delete), 500):
            chunk = ids_to_delete[i : i + 500]
            db.query(TradingData).filter(TradingData.id.in_(chunk)).delete(
                synchronize_session="fetch"
            )
        db.commit()
    invalid_removed = len(ids_to_delete)

    # Step 2: Remove duplicates (same date, crop_name_raw, market_id)
    seen_keys = {}
    dup_ids = []
    offset = 0
    while True:
        batch = (
            db.query(TradingData)
            .filter(TradingData.crop_id == None)  # noqa: E711
            .order_by(TradingData.id)
            .offset(offset).limit(BATCH)
            .all()
        )
        if not batch:
            break
        for rec in batch:
            key = (rec.trade_date, rec.crop_name_raw, rec.market_id)
            if key in seen_keys:
                dup_ids.append(rec.id)
            else:
                seen_keys[key] = rec.id
        offset += BATCH
        db.expire_all()

    if dup_ids:
        for i in range(0, len(dup_ids), 500):
            chunk = dup_ids[i : i + 500]
            db.query(TradingData).filter(TradingData.id.in_(chunk)).delete(
                synchronize_session="fetch"
            )
        db.commit()
    duplicates_removed = len(dup_ids)

    # Step 3: Remove zero-volume records (use count + batch delete)
    zero_vol_removed = 0
    while True:
        zero_batch = (
            db.query(TradingData.id)
            .filter(
                TradingData.crop_id == None,  # noqa: E711
                TradingData.volume == 0,
            )
            .limit(500)
            .all()
        )
        if not zero_batch:
            break
        zero_ids = [r[0] for r in zero_batch]
        db.query(TradingData).filter(TradingData.id.in_(zero_ids)).delete(
            synchronize_session="fetch"
        )
        zero_vol_removed += len(zero_ids)
        db.commit()

    remaining = db.query(func.count(TradingData.id)).filter(
        TradingData.crop_id == None  # noqa: E711
    ).scalar()

    print(f"  Invalid removed:         {invalid_removed:,}")
    print(f"  Duplicates removed:      {duplicates_removed:,}")
    print(f"  Zero-volume removed:     {zero_vol_removed:,}")
    print(f"  Remaining unmatched:     {remaining:,}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Batch clean trading data for all active crops.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be cleaned without modifying the database.",
    )
    parser.add_argument(
        "--crop",
        type=str,
        default=None,
        help="Clean only this specific crop (by crop_key).",
    )
    parser.add_argument(
        "--include-unmatched",
        action="store_true",
        help="Also clean records with crop_id=NULL.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        clean_all(
            db,
            crop_key=args.crop,
            include_unmatched=args.include_unmatched,
            dry_run=args.dry_run,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
