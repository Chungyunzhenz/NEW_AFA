"""Seed the database with counties, markets, and crop configs.

Usage:
    python scripts/seed_database.py

This script reads static seed data from backend/app/data/seed/ and
crop configuration files from backend/app/data/crop_configs/, then
inserts them into the database. Existing rows (matched by unique keys)
are skipped so the script is safe to re-run.
"""
from __future__ import annotations

import sys
import json
import logging
from pathlib import Path
from typing import Dict

# ---------------------------------------------------------------------------
# Ensure the backend package is importable regardless of working directory.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.models import County, Market, Crop  # noqa: E402
from app.config import load_crop_configs  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def seed() -> None:
    """Create tables (if absent) and populate static reference data."""
    logger.info("Creating database tables ...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        data_dir = PROJECT_ROOT / "backend" / "app" / "data" / "seed"

        # ------------------------------------------------------------------
        # 1. Counties
        # ------------------------------------------------------------------
        counties_path = data_dir / "counties.json"
        with open(counties_path, "r", encoding="utf-8") as f:
            counties_raw = json.load(f)

        county_map: Dict[str, County] = {}
        added_counties = 0
        for c in counties_raw:
            existing = (
                db.query(County)
                .filter(County.county_code == c["county_code"])
                .first()
            )
            if existing is None:
                county = County(
                    county_code=c["county_code"],
                    county_name_zh=c["county_name_zh"],
                    county_name_en=c["county_name_en"],
                )
                db.add(county)
                db.flush()
                county_map[c["county_code"]] = county
                added_counties += 1
            else:
                county_map[c["county_code"]] = existing

        logger.info(
            "Counties: %d total in file, %d newly added.",
            len(counties_raw),
            added_counties,
        )

        # ------------------------------------------------------------------
        # 2. Markets
        # ------------------------------------------------------------------
        markets_path = data_dir / "markets.json"
        with open(markets_path, "r", encoding="utf-8") as f:
            markets_raw = json.load(f)

        added_markets = 0
        for m in markets_raw:
            existing = (
                db.query(Market)
                .filter(Market.market_code == m["market_code"])
                .first()
            )
            if existing is None:
                county = county_map.get(m["county_code"])
                if county is None:
                    logger.warning(
                        "Skipping market %s (%s): county_code %s not found.",
                        m["market_code"],
                        m["market_name"],
                        m["county_code"],
                    )
                    continue
                market = Market(
                    market_code=m["market_code"],
                    market_name=m["market_name"],
                    county_id=county.id,
                )
                db.add(market)
                added_markets += 1

        logger.info(
            "Markets: %d total in file, %d newly added.",
            len(markets_raw),
            added_markets,
        )

        # ------------------------------------------------------------------
        # 3. Crops (from config files)
        # ------------------------------------------------------------------
        crop_configs = load_crop_configs()
        added_crops = 0
        for key, config in crop_configs.items():
            existing = db.query(Crop).filter(Crop.crop_key == key).first()
            if existing is None:
                crop = Crop(
                    crop_key=config["crop_key"],
                    display_name_zh=config["display_name_zh"],
                    display_name_en=config["display_name_en"],
                    category_code=config.get("category_code"),
                    config_json=json.dumps(config, ensure_ascii=False),
                    is_active=True,
                )
                db.add(crop)
                added_crops += 1

        logger.info(
            "Crops: %d configs found, %d newly added.",
            len(crop_configs),
            added_crops,
        )

        db.commit()
        logger.info(
            "Seed complete: %d counties, %d markets, %d crops.",
            len(counties_raw),
            len(markets_raw),
            len(crop_configs),
        )
    except Exception:
        db.rollback()
        logger.exception("Seeding failed — transaction rolled back.")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
