"""Seed typhoon_events table from CWA TDB JSON data.

Data source: Central Weather Administration Typhoon Database
             https://rdc28.cwa.gov.tw/TDB/public/basic_query/

Usage::

    cd Agriculture
    python -m scripts.seed_typhoon_data
"""
import json
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Allow running as ``python -m scripts.seed_typhoon_data`` from the repo root.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal, engine, Base
from backend.app.models.typhoon import TyphoonEvent, TyphoonAffectedCounty

SEED_FILE = ROOT / "backend" / "app" / "data" / "seed" / "typhoon_events.json"


def _parse_dt(s: str) -> datetime:
    """Parse an ISO-ish datetime string."""
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Cannot parse datetime: {s}")


def seed(drop_existing: bool = True) -> int:
    """Load typhoon events from the seed JSON into the database.

    Parameters
    ----------
    drop_existing:
        If *True*, delete all existing rows before seeding.

    Returns
    -------
    int
        Number of rows inserted.
    """
    with open(SEED_FILE, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Ensure the table exists.
    TyphoonEvent.__table__.create(bind=engine, checkfirst=True)
    TyphoonAffectedCounty.__table__.create(bind=engine, checkfirst=True)

    db = SessionLocal()
    try:
        if drop_existing:
            db.query(TyphoonAffectedCounty).delete()
            db.query(TyphoonEvent).delete()
            db.commit()

        count = 0
        for rec in records:
            event = TyphoonEvent(
                cwa_id=rec["cwa_id"],
                typhoon_name_zh=rec["typhoon_name_zh"],
                typhoon_name_en=rec["typhoon_name_en"],
                year=rec["year"],
                warning_start=_parse_dt(rec["warning_start"]),
                warning_end=_parse_dt(rec["warning_end"]),
                intensity=rec["intensity"],
                invasion_path=rec.get("invasion_path"),
                min_pressure_hpa=rec.get("min_pressure_hpa"),
                max_wind_ms=rec.get("max_wind_ms"),
                storm_radius_7_km=rec.get("storm_radius_7_km"),
                storm_radius_10_km=rec.get("storm_radius_10_km"),
                warning_count=rec.get("warning_count"),
            )
            db.add(event)
            count += 1

        db.commit()
        print(f"Seeded {count} typhoon events.")
        return count
    finally:
        db.close()


if __name__ == "__main__":
    seed()
