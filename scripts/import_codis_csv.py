"""Import historical weather data from CODiS (Climate Observation Data Inquiry System) CSV files.

CODiS is the official data portal of Taiwan's Central Weather Administration (CWA).
Since the CWA open-data API does not support historical date queries, this script
provides an alternative: parse CSV files manually downloaded from https://codis.cwa.gov.tw
and insert/update records into the weather_data table.

Usage:
    python scripts/import_codis_csv.py --input-dir data/codis_downloads/
    python scripts/import_codis_csv.py --input-dir data/codis_downloads/ --dry-run
    python scripts/import_codis_csv.py --input-dir data/codis_downloads/ --file 466920.csv
"""
from __future__ import annotations

import argparse
import csv
import logging
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.models import County, WeatherData  # noqa: E402
from app.services.weather_collector import STATION_COUNTY_MAP  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CODiS CSV column aliases -> DB fields
# ---------------------------------------------------------------------------
# CODiS CSV headers vary slightly across download options.  We use fuzzy
# matching: if a column header *contains* any of the alias substrings, it
# maps to the corresponding DB field.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "date": ["觀測時間", "年月日", "日期", "Date"],
    "temp_avg": ["氣溫(℃)", "平均氣溫", "氣溫"],
    "temp_max": ["最高氣溫"],
    "temp_min": ["最低氣溫"],
    "rainfall_mm": ["降水量", "降雨量"],
    "humidity_pct": ["相對溼度", "相對濕度"],
}

# Regex to extract a 6-digit station ID from filename or CSV content
_STATION_ID_RE = re.compile(r"\b(\d{6})\b")
# Also support C/O-prefixed auto station IDs (e.g., C0A520)
_STATION_ID_FULL_RE = re.compile(r"\b([A-Z]\d[A-Z]\d{3}|\d{6})\b")


def _safe_float(val: str) -> Optional[float]:
    """Convert a CSV cell to float, returning None for missing / invalid values."""
    val = val.strip()
    if not val or val in ("...", "--", "/", "X", "x", "T", "V"):
        return None
    try:
        f = float(val)
        return None if f <= -999 else f
    except ValueError:
        return None


def _parse_date(val: str) -> Optional[date]:
    """Parse a date string from CODiS CSV (supports multiple formats)."""
    val = val.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(val, fmt).date()
        except ValueError:
            continue
    return None


def _extract_station_id_from_filename(filename: str) -> Optional[str]:
    """Try to extract a station ID from the CSV filename."""
    m = _STATION_ID_FULL_RE.search(filename)
    return m.group(1) if m else None


def _extract_station_id_from_content(lines: List[str]) -> Optional[str]:
    """Scan the first few lines of the CSV for a station ID.

    CODiS CSVs typically have metadata lines like '站號,466920' at the top.
    """
    for line in lines[:20]:
        if "站號" in line or "StationID" in line or "站碼" in line:
            m = _STATION_ID_FULL_RE.search(line)
            if m:
                return m.group(1)
    return None


def _match_columns(headers: List[str]) -> Dict[str, int]:
    """Map our target field names to column indices using fuzzy alias matching.

    Returns a dict like {"date": 0, "temp_avg": 2, ...}.
    """
    mapping: Dict[str, int] = {}
    for idx, header in enumerate(headers):
        header_clean = header.strip()
        for field, aliases in COLUMN_ALIASES.items():
            if field in mapping:
                continue
            for alias in aliases:
                if alias in header_clean:
                    mapping[field] = idx
                    break
    return mapping


def _find_header_row(lines: List[str]) -> Tuple[int, List[str]]:
    """Find the header row in a CODiS CSV.

    Returns (line_index, list_of_header_strings).
    The header row is the first row that contains at least 2 of our target aliases.
    """
    for i, line in enumerate(lines):
        cells = line.split(",")
        if len(cells) < 3:
            continue
        match_count = 0
        joined = ",".join(cells)
        for aliases in COLUMN_ALIASES.values():
            for alias in aliases:
                if alias in joined:
                    match_count += 1
                    break
        if match_count >= 2:
            return i, [c.strip() for c in cells]
    return -1, []


def parse_codis_csv(
    file_path: Path,
) -> Tuple[Optional[str], List[Dict[str, Any]]]:
    """Parse a single CODiS CSV file.

    Returns (station_id, list_of_row_dicts) where each row dict has keys:
    observation_date, temp_avg, temp_max, temp_min, rainfall_mm, humidity_pct.
    """
    # Read all lines with flexible encoding
    raw_lines: List[str] = []
    for encoding in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            raw_lines = file_path.read_text(encoding=encoding).splitlines()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if not raw_lines:
        logger.warning("Cannot read %s with any supported encoding.", file_path.name)
        return None, []

    # Extract station ID
    station_id = _extract_station_id_from_filename(file_path.stem)
    if not station_id:
        station_id = _extract_station_id_from_content(raw_lines)

    if not station_id:
        logger.warning(
            "Cannot determine station ID for %s. Skipping.", file_path.name
        )
        return None, []

    # Find header row
    header_idx, headers = _find_header_row(raw_lines)
    if header_idx < 0:
        logger.warning(
            "Cannot find header row in %s. Skipping.", file_path.name
        )
        return None, []

    col_map = _match_columns(headers)
    if "date" not in col_map:
        logger.warning(
            "No date column found in %s. Skipping.", file_path.name
        )
        return None, []

    # Parse data rows
    records: List[Dict[str, Any]] = []
    for line in raw_lines[header_idx + 1 :]:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Use csv reader for proper handling of quoted fields
        try:
            cells = next(csv.reader([line]))
        except StopIteration:
            continue

        if len(cells) <= col_map["date"]:
            continue

        obs_date = _parse_date(cells[col_map["date"]])
        if obs_date is None:
            continue

        row: Dict[str, Any] = {"observation_date": obs_date}

        for field in ("temp_avg", "temp_max", "temp_min", "rainfall_mm", "humidity_pct"):
            idx = col_map.get(field)
            if idx is not None and idx < len(cells):
                row[field] = _safe_float(cells[idx])
            else:
                row[field] = None

        records.append(row)

    return station_id, records


def import_to_db(
    station_id: str,
    records: List[Dict[str, Any]],
    db,
    county_lookup: Dict[str, int],
    dry_run: bool = False,
) -> Tuple[int, int]:
    """Insert/update weather records into the database.

    Returns (inserted_count, updated_count).
    """
    county_code = STATION_COUNTY_MAP.get(station_id)
    if not county_code:
        logger.warning(
            "Station %s is not in STATION_COUNTY_MAP. Skipping %d records.",
            station_id,
            len(records),
        )
        return 0, 0

    county_id = county_lookup.get(county_code)
    if not county_id:
        logger.warning(
            "County code %s (station %s) not found in DB. Skipping.",
            county_code,
            station_id,
        )
        return 0, 0

    inserted = 0
    updated = 0

    for rec in records:
        obs_date = rec["observation_date"]

        if dry_run:
            inserted += 1
            continue

        existing = (
            db.query(WeatherData)
            .filter(
                WeatherData.observation_date == obs_date,
                WeatherData.county_id == county_id,
            )
            .first()
        )

        if existing is not None:
            # Update with CSV values (overwrite)
            existing.temp_avg = rec.get("temp_avg")
            existing.temp_max = rec.get("temp_max")
            existing.temp_min = rec.get("temp_min")
            existing.rainfall_mm = rec.get("rainfall_mm")
            existing.humidity_pct = rec.get("humidity_pct")
            updated += 1
        else:
            record = WeatherData(
                observation_date=obs_date,
                county_id=county_id,
                temp_avg=rec.get("temp_avg"),
                temp_max=rec.get("temp_max"),
                temp_min=rec.get("temp_min"),
                rainfall_mm=rec.get("rainfall_mm"),
                humidity_pct=rec.get("humidity_pct"),
            )
            db.add(record)
            inserted += 1

    if not dry_run and (inserted or updated):
        db.commit()

    return inserted, updated


def build_county_lookup(db) -> Dict[str, int]:
    """Return {county_code: county.id}."""
    return {c.county_code: c.id for c in db.query(County).all()}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import CODiS historical weather CSV files into the database.",
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Directory containing CODiS CSV files.",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Import only this specific file (within --input-dir).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse CSVs and report what would be imported, without writing to DB.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        logger.error("Input directory does not exist: %s", input_dir)
        sys.exit(1)

    # Collect CSV files
    if args.file:
        csv_files = [input_dir / args.file]
        if not csv_files[0].is_file():
            logger.error("File not found: %s", csv_files[0])
            sys.exit(1)
    else:
        csv_files = sorted(input_dir.glob("*.csv"))

    if not csv_files:
        logger.error("No CSV files found in %s", input_dir)
        sys.exit(1)

    logger.info("Found %d CSV file(s) to process.", len(csv_files))

    if args.dry_run:
        logger.info("*** DRY RUN — no data will be written to the database ***")

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    county_lookup = build_county_lookup(db)

    total_inserted = 0
    total_updated = 0
    total_skipped = 0

    try:
        for i, csv_file in enumerate(csv_files, 1):
            logger.info(
                "[%d/%d] Processing %s ...", i, len(csv_files), csv_file.name
            )

            station_id, records = parse_codis_csv(csv_file)

            if not station_id or not records:
                logger.warning("  -> Skipped (no station ID or no records).")
                total_skipped += 1
                continue

            logger.info(
                "  -> Station %s: %d daily records (date range: %s ~ %s)",
                station_id,
                len(records),
                records[0]["observation_date"],
                records[-1]["observation_date"],
            )

            inserted, updated = import_to_db(
                station_id, records, db, county_lookup, dry_run=args.dry_run,
            )
            total_inserted += inserted
            total_updated += updated

            action = "would insert" if args.dry_run else "inserted"
            logger.info(
                "  -> %s %d, updated %d records.", action, inserted, updated
            )
    except KeyboardInterrupt:
        logger.warning("Interrupted by user.")
    finally:
        db.close()

    logger.info("=" * 60)
    logger.info("Import complete.")
    logger.info("  Files processed : %d", len(csv_files) - total_skipped)
    logger.info("  Files skipped   : %d", total_skipped)
    logger.info("  Records inserted: %d", total_inserted)
    logger.info("  Records updated : %d", total_updated)
    if args.dry_run:
        logger.info("  (DRY RUN — nothing was written)")


if __name__ == "__main__":
    main()
