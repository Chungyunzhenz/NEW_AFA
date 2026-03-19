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

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

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
        default=None,
        help="Seconds to sleep between API calls (overrides config).",
    )
    return parser.parse_args()


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
    if args.rate_limit is not None:
        collector.RATE_LIMIT = args.rate_limit

    # Register graceful shutdown
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    db = SessionLocal()
    total_inserted = 0
    days_processed = 0
    current = start_date

    try:
        while current <= end_date:
            if _shutdown_requested:
                logger.info("Shutdown requested. Stopping after %d days.", days_processed)
                break

            days_processed += 1
            pct = days_processed / total_days * 100

            logger.info(
                "[%d/%d  %.1f%%] Fetching %s ...",
                days_processed,
                total_days,
                pct,
                current,
            )

            try:
                inserted = collector.fetch_single_day(current, db)
                total_inserted += inserted
                if inserted > 0:
                    logger.info("  -> inserted %d records.", inserted)
            except Exception:
                logger.exception("  -> ERROR on %s. Continuing.", current)
                db.rollback()

            current += timedelta(days=1)

            # Rate-limit between calls
            if current <= end_date and not _shutdown_requested:
                time.sleep(collector.RATE_LIMIT)

    except Exception:
        logger.exception("Fatal error during backfill.")
    finally:
        db.close()

    logger.info(
        "Backfill finished: %d days processed, %d total records inserted.",
        days_processed,
        total_inserted,
    )


if __name__ == "__main__":
    main()
