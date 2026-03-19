"""Production statistics CSV importer.

Reads a local CSV file containing annual/monthly crop production data,
maps its columns to the :class:`ProductionData` model, and upserts into
the database.

Usage::

    from pathlib import Path
    from app.database import SessionLocal
    from app.services.production_collector import ProductionCSVImporter

    db = SessionLocal()
    importer = ProductionCSVImporter()
    stats = importer.import_csv(Path("data_archive/cabbage_production.csv"), "cabbage", db)
    db.close()
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from ..models import County, Crop, ProductionData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known column-name aliases (Traditional Chinese + English variants)
# ---------------------------------------------------------------------------
# Keys are the canonical DB field; values are possible column headers.
COLUMN_ALIASES: Dict[str, List[str]] = {
    "year": ["年份", "年度", "year", "Year", "YEAR", "民國年"],
    "month": ["月份", "month", "Month", "MONTH"],
    "county_name": [
        "縣市", "縣市別", "county", "County", "COUNTY", "地區", "區域",
        "縣市名稱", "county_name",
    ],
    "planted_area_ha": [
        "種植面積", "種植面積(公頃)", "planted_area_ha", "planted_area",
        "PlantedArea", "種植面積（公頃）",
    ],
    "harvest_area_ha": [
        "收穫面積", "收獲面積", "收穫面積(公頃)", "收獲面積(公頃)",
        "harvest_area_ha", "harvest_area", "HarvestArea",
        "收穫面積（公頃）", "收獲面積（公頃）",
    ],
    "production_tonnes": [
        "產量", "產量(公噸)", "production_tonnes", "production",
        "Production", "產量（公噸）",
    ],
    "yield_per_ha": [
        "每公頃產量", "單位面積產量", "yield_per_ha", "yield",
        "Yield", "每公頃產量(公斤)", "每公頃產量（公斤）",
    ],
}


@dataclass
class ImportStats:
    """Summary returned by :meth:`import_csv`."""
    file_path: str = ""
    crop_key: str = ""
    total_rows: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    skipped_error: int = 0
    errors: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


class ProductionCSVImporter:
    """Import production data from CSV files into the database."""

    # ------------------------------------------------------------------
    # Column mapping
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_column_map(header: List[str]) -> Dict[str, Optional[str]]:
        """Given the CSV *header*, build ``{canonical_field: csv_column}``."""
        mapping: Dict[str, Optional[str]] = {
            key: None for key in COLUMN_ALIASES
        }
        header_stripped = [h.strip() for h in header]

        for canonical, aliases in COLUMN_ALIASES.items():
            for alias in aliases:
                if alias in header_stripped:
                    mapping[canonical] = alias
                    break

        return mapping

    # ------------------------------------------------------------------
    # Year normalization (ROC or Western)
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_year(raw: str) -> Optional[int]:
        """Convert a year string (possibly ROC era) to a western year.

        If the integer value is <= 200 it is assumed to be an ROC year
        and 1911 is added.
        """
        raw = raw.strip().replace(",", "")
        if not raw:
            return None
        try:
            val = int(float(raw))
        except ValueError:
            return None
        if val <= 0:
            return None
        if val <= 200:
            return val + 1911
        return val

    # ------------------------------------------------------------------
    # Numeric helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(raw: Any) -> Optional[float]:
        if raw is None:
            return None
        raw_str = str(raw).strip().replace(",", "")
        if raw_str in ("", "-", "…", "─", "N/A", "n/a"):
            return None
        try:
            return float(raw_str)
        except ValueError:
            return None

    @staticmethod
    def _safe_int(raw: Any) -> Optional[int]:
        if raw is None:
            return None
        raw_str = str(raw).strip().replace(",", "")
        if raw_str in ("", "-", "…", "─", "N/A", "n/a"):
            return None
        try:
            return int(float(raw_str))
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # CSV detection
    # ------------------------------------------------------------------
    @staticmethod
    def _detect_encoding(filepath: Path) -> str:
        """Try to detect file encoding. Defaults to ``utf-8-sig``."""
        for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
            try:
                with open(filepath, "r", encoding=enc) as f:
                    f.read(4096)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return "utf-8-sig"

    # ------------------------------------------------------------------
    # Main import
    # ------------------------------------------------------------------
    def import_csv(
        self,
        filepath: Path,
        crop_key: str,
        db: Session,
    ) -> ImportStats:
        """Read *filepath* CSV and insert rows into ``production_data``.

        Parameters
        ----------
        filepath:
            Path to the CSV file.
        crop_key:
            The crop key (e.g. ``"cabbage"``) used to look up the
            ``Crop`` row.
        db:
            An active SQLAlchemy session.

        Returns
        -------
        ImportStats
        """
        stats = ImportStats(file_path=str(filepath), crop_key=crop_key)

        # Resolve crop
        crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
        if crop is None:
            msg = f"Crop with key '{crop_key}' not found in database."
            logger.error(msg)
            stats.errors.append(msg)
            return stats

        # Resolve county lookup: county_name_zh -> county.id
        county_map: Dict[str, int] = {
            c.county_name_zh: c.id for c in db.query(County).all()
        }

        # Detect encoding and read CSV
        encoding = self._detect_encoding(filepath)
        logger.info("Reading %s with encoding=%s", filepath, encoding)

        with open(filepath, "r", encoding=encoding, newline="") as f:
            # Attempt to sniff the dialect
            sample = f.read(8192)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
            except csv.Error:
                dialect = csv.excel  # type: ignore[assignment]

            reader = csv.DictReader(f, dialect=dialect)
            if reader.fieldnames is None:
                msg = f"Could not parse header from {filepath}."
                logger.error(msg)
                stats.errors.append(msg)
                return stats

            col_map = self._resolve_column_map(list(reader.fieldnames))
            logger.info("Column mapping: %s", col_map)

            if col_map["year"] is None:
                msg = "Could not locate a 'year' column in the CSV."
                logger.error(msg)
                stats.errors.append(msg)
                return stats

            if col_map["production_tonnes"] is None:
                msg = "Could not locate a 'production_tonnes' column in the CSV."
                logger.error(msg)
                stats.errors.append(msg)
                return stats

            for row_num, row in enumerate(reader, start=2):
                stats.total_rows += 1
                try:
                    year = self._normalize_year(row.get(col_map["year"], ""))
                    if year is None:
                        stats.skipped_error += 1
                        stats.errors.append(f"Row {row_num}: unparseable year")
                        continue

                    month: Optional[int] = None
                    if col_map["month"] is not None:
                        month = self._safe_int(row.get(col_map["month"]))

                    # County resolution
                    county_id: Optional[int] = None
                    if col_map["county_name"] is not None:
                        county_name_raw = row.get(col_map["county_name"], "").strip()
                        county_id = county_map.get(county_name_raw)
                        if county_id is None and county_name_raw:
                            # Try partial matching (e.g. "台北市" vs "臺北市")
                            for zh_name, cid in county_map.items():
                                if (
                                    county_name_raw in zh_name
                                    or zh_name in county_name_raw
                                ):
                                    county_id = cid
                                    break

                    production_val = self._safe_float(
                        row.get(col_map["production_tonnes"])
                    )
                    if production_val is None:
                        stats.skipped_error += 1
                        stats.errors.append(
                            f"Row {row_num}: missing production_tonnes"
                        )
                        continue

                    planted = self._safe_float(
                        row.get(col_map["planted_area_ha"]) if col_map["planted_area_ha"] else None
                    )
                    harvest = self._safe_float(
                        row.get(col_map["harvest_area_ha"]) if col_map["harvest_area_ha"] else None
                    )
                    yield_val = self._safe_float(
                        row.get(col_map["yield_per_ha"]) if col_map["yield_per_ha"] else None
                    )

                    # Duplicate check
                    existing = (
                        db.query(ProductionData.id)
                        .filter(
                            ProductionData.year == year,
                            ProductionData.month == month,
                            ProductionData.crop_id == crop.id,
                            ProductionData.county_id == county_id,
                        )
                        .first()
                    )
                    if existing is not None:
                        stats.skipped_existing += 1
                        continue

                    record = ProductionData(
                        year=year,
                        month=month,
                        crop_id=crop.id,
                        county_id=county_id,
                        planted_area_ha=planted,
                        harvest_area_ha=harvest,
                        production_tonnes=production_val,
                        yield_per_ha=yield_val,
                    )
                    db.add(record)
                    stats.inserted += 1

                except Exception as exc:
                    stats.skipped_error += 1
                    stats.errors.append(f"Row {row_num}: {exc}")
                    logger.debug("Error on row %d: %s", row_num, exc)
                    continue

        if stats.inserted > 0:
            db.commit()

        logger.info(
            "CSV import '%s' for crop '%s': %d rows read, %d inserted, "
            "%d skipped (existing), %d skipped (error).",
            filepath,
            crop_key,
            stats.total_rows,
            stats.inserted,
            stats.skipped_existing,
            stats.skipped_error,
        )
        return stats
