"""AMIS API data collector for agricultural trading data.

Fetches daily fruit/vegetable trading data from the Ministry of
Agriculture's AMIS open-data API, converts ROC (民國) dates,
and persists records via SQLAlchemy with upsert-style logic.

Usage (programmatic)::

    from datetime import date
    from app.database import SessionLocal
    from app.services.data_collector import AMISDataCollector

    db = SessionLocal()
    collector = AMISDataCollector()
    inserted = collector.fetch_single_day(date(2025, 3, 1), db)
    db.close()
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests
import urllib3
from sqlalchemy.orm import Session

from ..config import settings, load_crop_configs

# Suppress noisy InsecureRequestWarning when VERIFY_SSL is False
if not settings.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from ..models import Crop, Market, TradingData

logger = logging.getLogger(__name__)


class AMISDataCollector:
    """Collect daily trading data from the AMIS open-data REST API."""

    API_URL: str = settings.AMIS_API_BASE
    RATE_LIMIT: float = settings.FETCH_RATE_LIMIT_SECONDS
    REQUEST_TIMEOUT: int = 30

    # ------------------------------------------------------------------
    # ROC <-> Western date helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _to_roc_date(d: date) -> str:
        """Convert a western *date* to an ROC-era string ``YYY.MM.DD``.

        The ROC year equals the Gregorian year minus 1911.
        Example: ``date(2025, 3, 1)`` -> ``"114.03.01"``
        """
        roc_year = d.year - 1911
        return f"{roc_year:03d}.{d.month:02d}.{d.day:02d}"

    @staticmethod
    def _from_roc_date(roc_str: str) -> date:
        """Parse an ROC-era date string into a western :class:`date`.

        Accepted formats: ``YYY.MM.DD``, ``YYY/MM/DD``, or ``YYYMMDD``.
        """
        cleaned = roc_str.strip().replace("/", ".")
        parts = cleaned.split(".")
        if len(parts) == 3:
            roc_year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        elif len(parts) == 1 and len(cleaned) == 7:
            # Compact format: YYYMMDD (e.g. "1140102")
            roc_year = int(cleaned[:3])
            month = int(cleaned[3:5])
            day = int(cleaned[5:7])
        else:
            raise ValueError(f"Unexpected ROC date format: {roc_str!r}")
        return date(roc_year + 1911, month, day)

    # ------------------------------------------------------------------
    # Crop-name matching
    # ------------------------------------------------------------------
    def build_crop_lookup(self, db: Session) -> Dict[str, int]:
        """Build a mapping of *crop_name prefix* -> ``Crop.id``.

        The crop config files carry ``amis_crop_name_patterns`` — a list
        of Chinese prefixes.  Every AMIS ``作物名稱`` that *starts with*
        one of those prefixes is mapped to the corresponding ``Crop`` row.
        """
        configs = load_crop_configs()
        crop_rows = {c.crop_key: c for c in db.query(Crop).all()}
        lookup: Dict[str, int] = {}
        for key, cfg in configs.items():
            crop_obj = crop_rows.get(key)
            if crop_obj is None:
                continue
            for pattern in cfg.get("amis_crop_name_patterns", []):
                lookup[pattern] = crop_obj.id
        return lookup

    def _match_crop_id(
        self, crop_name_raw: str, crop_lookup: Dict[str, int]
    ) -> Optional[int]:
        """Return the ``Crop.id`` whose prefix matches *crop_name_raw*.

        Longer prefixes are checked first so that a pattern like
        ``"甘藍-初秋"`` beats the shorter ``"甘藍"`` when the raw name is
        ``"甘藍-初秋"`` exactly.
        """
        sorted_patterns = sorted(crop_lookup.keys(), key=len, reverse=True)
        for pattern in sorted_patterns:
            if crop_name_raw.startswith(pattern):
                return crop_lookup[pattern]
        return None

    # ------------------------------------------------------------------
    # Market lookup
    # ------------------------------------------------------------------
    @staticmethod
    def build_market_lookup(db: Session) -> Dict[str, int]:
        """Return a mapping of ``market_code`` -> ``Market.id``."""
        return {
            m.market_code: m.id
            for m in db.query(Market).all()
        }

    # ------------------------------------------------------------------
    # Core fetch / parse
    # ------------------------------------------------------------------
    def _fetch_api(self, target_date: date) -> List[Dict[str, Any]]:
        """Call the AMIS REST API for a single *target_date*.

        Returns the parsed JSON array or an empty list on failure.
        """
        roc_date_str = self._to_roc_date(target_date)
        params = {
            "IsTransData": "1",
            "UnitId": "039",
            "StartDate": roc_date_str,
        }
        logger.debug("Requesting AMIS data for %s (ROC %s)", target_date, roc_date_str)

        try:
            resp = requests.get(
                self.API_URL,
                params=params,
                timeout=self.REQUEST_TIMEOUT,
                verify=settings.VERIFY_SSL,
            )
            resp.raise_for_status()

            # The API may return an empty body or non-JSON on holidays.
            if not resp.text.strip():
                logger.info("Empty response for %s — likely a non-trading day.", target_date)
                return []

            data = resp.json()
            if not isinstance(data, list):
                logger.warning("Unexpected response type (%s) for %s", type(data).__name__, target_date)
                return []
            return data
        except requests.RequestException as exc:
            logger.error("HTTP error fetching %s: %s", target_date, exc)
            return []
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error("JSON decode error for %s: %s", target_date, exc)
            return []

    def _parse_amis_response(
        self,
        data: List[Dict[str, Any]],
        db: Session,
        crop_lookup: Dict[str, int],
        market_lookup: Dict[str, int],
        skip_duplicate_check: bool = False,
    ) -> int:
        """Parse the AMIS JSON array and persist to the database.

        Duplicate records (same trade_date + crop_name_raw + market_id)
        are skipped thanks to the unique constraint; we proactively check
        before inserting to avoid integrity-error noise.

        When *skip_duplicate_check* is True, the per-row DB query is
        skipped (batch dedup within the response is still performed).
        This is safe when the caller already verified the date has no
        existing data.

        Returns the number of newly inserted rows.
        """
        records_to_insert: list = []
        seen_keys: set = set()  # track keys within this batch
        for row in data:
            try:
                trade_date_str: str = row.get("交易日期") or ""
                crop_name_raw: str = (row.get("作物名稱") or "").strip()
                market_code: str = str(row.get("市場代號") or "").strip()

                if not trade_date_str or not crop_name_raw:
                    continue

                trade_date = self._from_roc_date(trade_date_str)
                market_id = market_lookup.get(market_code)
                crop_id = self._match_crop_id(crop_name_raw, crop_lookup)

                # Deduplicate within the same batch
                batch_key = (trade_date, crop_name_raw, market_id)
                if batch_key in seen_keys:
                    continue
                seen_keys.add(batch_key)

                if not skip_duplicate_check:
                    # Duplicate check (upsert-style: skip if exists in DB)
                    existing = (
                        db.query(TradingData.id)
                        .filter(
                            TradingData.trade_date == trade_date,
                            TradingData.crop_name_raw == crop_name_raw,
                            TradingData.market_id == market_id,
                        )
                        .first()
                    )
                    if existing is not None:
                        continue

                records_to_insert.append({
                    "trade_date": trade_date,
                    "crop_id": crop_id,
                    "crop_name_raw": crop_name_raw,
                    "market_id": market_id,
                    "market_code_raw": market_code or None,
                    "price_high": self._safe_float(row.get("上價")),
                    "price_mid": self._safe_float(row.get("中價")),
                    "price_low": self._safe_float(row.get("下價")),
                    "price_avg": self._safe_float(row.get("平均價")),
                    "volume": self._safe_float(row.get("交易量")),
                })
            except Exception:
                logger.exception("Error parsing AMIS row: %s", row)
                continue

        inserted = len(records_to_insert)
        if inserted > 0:
            db.bulk_insert_mappings(TradingData, records_to_insert)
            db.commit()
        return inserted

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def fetch_single_day(self, target_date: date, db: Session) -> int:
        """Fetch all trading data for *target_date* and store to DB.

        Returns the count of newly inserted rows.
        """
        crop_lookup = self.build_crop_lookup(db)
        market_lookup = self.build_market_lookup(db)
        return self.fetch_single_day_with_lookups(
            target_date, db, crop_lookup, market_lookup
        )

    def fetch_single_day_with_lookups(
        self,
        target_date: date,
        db: Session,
        crop_lookup: Dict[str, int],
        market_lookup: Dict[str, int],
        skip_duplicate_check: bool = False,
    ) -> int:
        """Fetch trading data for *target_date* using pre-built lookups.

        Same as :meth:`fetch_single_day` but avoids rebuilding the
        crop/market lookup maps on every call — useful for batch runs.
        """
        data = self._fetch_api(target_date)
        if not data:
            logger.info("No records returned for %s.", target_date)
            return 0

        inserted = self._parse_amis_response(
            data, db, crop_lookup, market_lookup,
            skip_duplicate_check=skip_duplicate_check,
        )
        logger.info(
            "Date %s: fetched %d rows, inserted %d new records.",
            target_date,
            len(data),
            inserted,
        )
        return inserted

    def fetch_date_range(
        self,
        start_date: date,
        end_date: date,
        db: Session,
    ) -> int:
        """Iterate over ``[start_date, end_date]`` day-by-day.

        Respects :pyattr:`RATE_LIMIT` between successive API calls.
        Returns the total number of newly inserted rows across all days.
        """
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date}) must not be after end_date ({end_date})."
            )

        crop_lookup = self.build_crop_lookup(db)
        market_lookup = self.build_market_lookup(db)

        total_inserted = 0
        current = start_date
        total_days = (end_date - start_date).days + 1
        day_num = 0

        while current <= end_date:
            day_num += 1
            logger.info(
                "[%d/%d] Fetching trading data for %s ...",
                day_num,
                total_days,
                current,
            )

            data = self._fetch_api(current)
            if data:
                inserted = self._parse_amis_response(
                    data, db, crop_lookup, market_lookup
                )
                total_inserted += inserted
                logger.info(
                    "  -> %d rows fetched, %d inserted.", len(data), inserted
                )
            else:
                logger.info("  -> no data (holiday / non-trading day).")

            current += timedelta(days=1)

            # Rate-limit: sleep between requests (skip after last day)
            if current <= end_date and self.RATE_LIMIT > 0:
                time.sleep(self.RATE_LIMIT)

        logger.info(
            "Date range complete: %s to %s — %d total new records.",
            start_date,
            end_date,
            total_inserted,
        )
        return total_inserted

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Convert *value* to ``float``, returning ``None`` on failure."""
        if value is None:
            return None
        try:
            result = float(value)
            return result
        except (TypeError, ValueError):
            return None
