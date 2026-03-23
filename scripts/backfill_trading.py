"""Backfill historical trading data from the AMIS API.

Usage:
    python scripts/backfill_trading.py [--start YYYY-MM-DD] [--end YYYY-MM-DD]

By default the script fetches trading data for the last 3 years up to
yesterday.  Progress is printed to stdout, and the script handles
keyboard interrupts gracefully (commits already-fetched data).
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Set

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.models import TradingData  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402

# Disable verbose SQL echo for batch operations
engine.echo = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Suppress verbose SQLAlchemy SQL statement logging for batch runs
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Graceful shutdown flag
# ---------------------------------------------------------------------------
_shutdown_requested: bool = False


def _signal_handler(signum: int, frame: object) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Interrupt received — finishing current day then stopping.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill AMIS trading data for a date range.",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date (YYYY-MM-DD). Default: 3 years before today.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date (YYYY-MM-DD). Default: yesterday.",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=0.5,
        help="Seconds to sleep between API calls (default: 0.5).",
    )
    return parser.parse_args()


def _get_existing_dates(db, start_date: date, end_date: date) -> Set[date]:
    """Query DB for dates that already have trading data in the range."""
    from sqlalchemy import func

    rows = (
        db.query(func.distinct(TradingData.trade_date))
        .filter(
            TradingData.trade_date >= start_date,
            TradingData.trade_date <= end_date,
        )
        .all()
    )
    # SQLite returns strings via func.distinct(); convert to date objects
    result: Set[date] = set()
    for row in rows:
        val = row[0]
        if isinstance(val, date):
            result.add(val)
        elif isinstance(val, str):
            result.add(datetime.strptime(val, "%Y-%m-%d").date())
    return result


def _format_eta(seconds: float) -> str:
    """Format seconds into a human-readable HH:MM:SS string."""
    if seconds < 0:
        return "--:--:--"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def main() -> None:
    args = parse_args()

    today = date.today()
    start_date: date = (
        datetime.strptime(args.start, "%Y-%m-%d").date()
        if args.start
        else today - timedelta(days=3 * 365)
    )
    end_date: date = (
        datetime.strptime(args.end, "%Y-%m-%d").date()
        if args.end
        else today - timedelta(days=1)
    )

    if start_date > end_date:
        logger.error("start_date (%s) is after end_date (%s). Aborting.", start_date, end_date)
        sys.exit(1)

    total_days = (end_date - start_date).days + 1
    logger.info(
        "Backfilling trading data from %s to %s (%d days).",
        start_date,
        end_date,
        total_days,
    )

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    collector = AMISDataCollector()
    collector.RATE_LIMIT = args.rate_limit

    # Register graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    db = SessionLocal()

    # --- Step 1: Build lookups ONCE outside the loop ---
    logger.info("Building crop & market lookups ...")
    crop_lookup = collector.build_crop_lookup(db)
    market_lookup = collector.build_market_lookup(db)
    logger.info(
        "Lookups ready: %d crop patterns, %d markets.",
        len(crop_lookup),
        len(market_lookup),
    )

    # --- Step 2: Query existing dates to skip ---
    logger.info("Querying existing dates in DB ...")
    existing_dates = _get_existing_dates(db, start_date, end_date)
    logger.info(
        "Found %d dates with existing data — these will be skipped.",
        len(existing_dates),
    )

    total_inserted = 0
    days_processed = 0
    days_skipped = 0
    days_fetched = 0
    current = start_date
    fetch_start_time = time.monotonic()

    try:
        while current <= end_date:
            if _shutdown_requested:
                logger.info("Shutdown requested. Stopping after %d days.", days_processed)
                break

            days_processed += 1

            # --- Step 2: Skip dates already in DB ---
            if current in existing_dates:
                days_skipped += 1
                logger.debug("Skipping %s (already in DB).", current)
                current += timedelta(days=1)
                continue

            # --- Step 4: Progress with ETA ---
            days_remaining = total_days - days_processed
            if days_fetched > 0:
                elapsed = time.monotonic() - fetch_start_time
                avg_per_fetch = elapsed / days_fetched
                # Estimate remaining fetches (subtract already-skipped proportion)
                skip_ratio = days_skipped / days_processed if days_processed > 0 else 0
                estimated_fetches_left = days_remaining * (1 - skip_ratio)
                eta_seconds = estimated_fetches_left * avg_per_fetch
            else:
                eta_seconds = -1

            pct = days_processed / total_days * 100
            logger.info(
                "[%d/%d  %.1f%%  ETA %s] Fetching %s ... (skipped: %d, fetched: %d, inserted: %d)",
                days_processed,
                total_days,
                pct,
                _format_eta(eta_seconds),
                current,
                days_skipped,
                days_fetched,
                total_inserted,
            )

            try:
                inserted = collector.fetch_single_day_with_lookups(
                    current, db, crop_lookup, market_lookup,
                    skip_duplicate_check=(current not in existing_dates),
                )
                total_inserted += inserted
                days_fetched += 1
                if inserted > 0:
                    logger.info("  -> inserted %d records.", inserted)
            except Exception:
                logger.exception("  -> ERROR on %s. Continuing.", current)
                db.rollback()

            current += timedelta(days=1)

            # Rate-limit between API calls
            if current <= end_date and not _shutdown_requested:
                time.sleep(collector.RATE_LIMIT)

    except Exception:
        logger.exception("Fatal error during backfill.")
    finally:
        db.close()

    elapsed_total = time.monotonic() - fetch_start_time
    logger.info(
        "Backfill finished in %s: %d days processed, %d skipped, "
        "%d fetched, %d total records inserted.",
        _format_eta(elapsed_total),
        days_processed,
        days_skipped,
        days_fetched,
        total_inserted,
    )


if __name__ == "__main__":
    main()
