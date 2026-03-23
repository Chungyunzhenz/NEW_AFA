"""Migration: Add market_code_raw column to trading_data table.

SQLite does not support full ALTER TABLE, but ADD COLUMN works.

Usage:
    python scripts/migrate_add_market_code_raw.py
    python scripts/migrate_add_market_code_raw.py --check
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from sqlalchemy import inspect, text  # noqa: E402
from app.database import engine  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column already exists in a table."""
    insp = inspect(engine)
    columns = [col["name"] for col in insp.get_columns(table_name)]
    return column_name in columns


def migrate(check_only: bool = False) -> None:
    table = "trading_data"
    column = "market_code_raw"

    if column_exists(table, column):
        logger.info("Column '%s.%s' already exists. Nothing to do.", table, column)
        return

    if check_only:
        logger.info("Column '%s.%s' does NOT exist. Run without --check to add it.", table, column)
        return

    logger.info("Adding column '%s' to table '%s'...", column, table)
    with engine.begin() as conn:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} TEXT"))
    logger.info("Done. Column '%s.%s' added successfully.", table, column)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Add market_code_raw column to trading_data table.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check if migration is needed, without applying.",
    )
    args = parser.parse_args()
    migrate(check_only=args.check)


if __name__ == "__main__":
    main()
