"""Import a production statistics CSV file into the database.

Usage:
    python scripts/load_production_csv.py <csv_path> <crop_key>

Example:
    python scripts/load_production_csv.py data_archive/cabbage_production.csv cabbage
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

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.services.production_collector import ProductionCSVImporter  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import a production statistics CSV into the database.",
    )
    parser.add_argument(
        "csv_path",
        type=str,
        help="Path to the CSV file to import.",
    )
    parser.add_argument(
        "crop_key",
        type=str,
        help="Crop key matching a Crop row in the database (e.g. 'cabbage').",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    csv_path = Path(args.csv_path)
    if not csv_path.is_absolute():
        csv_path = PROJECT_ROOT / csv_path

    if not csv_path.exists():
        logger.error("CSV file not found: %s", csv_path)
        sys.exit(1)

    if not csv_path.is_file():
        logger.error("Path is not a file: %s", csv_path)
        sys.exit(1)

    crop_key: str = args.crop_key.strip()
    logger.info("Importing %s for crop_key='%s' ...", csv_path, crop_key)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        importer = ProductionCSVImporter()
        stats = importer.import_csv(csv_path, crop_key, db)

        logger.info("--- Import Summary ---")
        logger.info("  File:              %s", stats.file_path)
        logger.info("  Crop key:          %s", stats.crop_key)
        logger.info("  Total rows read:   %d", stats.total_rows)
        logger.info("  Inserted:          %d", stats.inserted)
        logger.info("  Skipped (existing):%d", stats.skipped_existing)
        logger.info("  Skipped (error):   %d", stats.skipped_error)

        if stats.errors:
            logger.warning("Errors encountered (%d):", len(stats.errors))
            for err in stats.errors[:20]:
                logger.warning("  %s", err)
            if len(stats.errors) > 20:
                logger.warning("  ... and %d more.", len(stats.errors) - 20)
    except Exception:
        logger.exception("Fatal error during CSV import.")
        sys.exit(1)
    finally:
        db.close()

    logger.info("Done.")


if __name__ == "__main__":
    main()
