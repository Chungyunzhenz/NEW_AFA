"""CWA (Central Weather Administration) daily weather observation collector.

Fetches per-station daily observations from the CWA open-data API and
stores aggregated daily weather records per county.

Usage (programmatic)::

    from datetime import date
    from app.database import SessionLocal
    from app.services.weather_collector import CWAWeatherCollector

    db = SessionLocal()
    collector = CWAWeatherCollector()
    inserted = collector.fetch_daily_weather(date(2025, 3, 1), db)
    db.close()
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests
import urllib3
from sqlalchemy.orm import Session

from ..config import settings

# Suppress noisy InsecureRequestWarning when VERIFY_SSL is False
if not settings.VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from ..models import County, WeatherData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Station -> County mapping
# ---------------------------------------------------------------------------
# Each CWA weather station is associated with a county.  The mapping uses
# the station ID as key and the corresponding county_code (matching the
# counties seed data) as value.
STATION_COUNTY_MAP: Dict[str, str] = {
    # Northern Taiwan
    "466920": "63000",   # 臺北 (Taipei)
    "466910": "65000",   # 鞍部/新北
    "C0A520": "65000",   # 板橋/新北
    "467050": "10017",   # 基隆 (Keelung)
    "C0C700": "10002",   # 宜蘭 (Yilan)
    "C0D100": "68000",   # 桃園 (Taoyuan)
    "C0E520": "10004",   # 新竹縣
    "467571": "10018",   # 新竹市
    "C0E400": "10005",   # 苗栗 (Miaoli)
    # Central Taiwan
    "467490": "66000",   # 臺中 (Taichung)
    "C0F9A0": "10007",   # 彰化 (Changhua)
    "C0G730": "10008",   # 南投 (Nantou)
    "C0K330": "10009",   # 雲林 (Yunlin)
    # Southern Taiwan
    "C0M790": "10010",   # 嘉義縣 (朴子站)
    "467480": "10020",   # 嘉義市
    "467410": "67000",   # 臺南 (Tainan)
    "467440": "64000",   # 高雄 (Kaohsiung)
    "467590": "10013",   # 屏東 (Pingtung / Hengchun)
    # Eastern Taiwan
    "467660": "10014",   # 臺東 (Taitung)
    "466990": "10015",   # 花蓮 (Hualien)
    # Offshore
    "467300": "10016",   # 澎湖 (Penghu)
    "467110": "09020",   # 金門 (Kinmen)
    "467990": "09007",   # 連江 (Lienchiang / Matsu)
}

# CWA daily observation dataset ID
CWA_DAILY_DATASET_ID = "O-A0003-001"


class CWAWeatherCollector:
    """Collect daily weather observations from CWA open-data API."""

    RATE_LIMIT: float = settings.FETCH_RATE_LIMIT_SECONDS
    REQUEST_TIMEOUT: int = 30

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.api_key = api_key or settings.CWA_API_KEY
        if not self.api_key:
            logger.warning(
                "CWA_API_KEY is not set.  Weather collection will fail."
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _build_county_lookup(db: Session) -> Dict[str, int]:
        """Return ``{county_code: county.id}``."""
        return {
            c.county_code: c.id for c in db.query(County).all()
        }

    def _fetch_observations(self, target_date: date) -> List[Dict[str, Any]]:
        """Call CWA API and return the station-level observations list.

        The daily observation endpoint returns a JSON structure rooted at
        ``records.Station``.  Each station element contains ``StationId``
        and various weather elements.
        """
        url = f"{settings.CWA_API_BASE}/{CWA_DAILY_DATASET_ID}"
        params = {
            "Authorization": self.api_key,
            "format": "JSON",
        }
        logger.debug("Requesting CWA observations for %s", target_date)

        try:
            resp = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT, verify=settings.VERIFY_SSL)
            resp.raise_for_status()
            payload = resp.json()

            # Navigate the CWA response structure
            records = payload.get("records", {})
            stations = records.get("Station", records.get("station", []))
            if not isinstance(stations, list):
                logger.warning("Unexpected CWA response structure for %s.", target_date)
                return []
            return stations
        except requests.RequestException as exc:
            logger.error("HTTP error fetching CWA data for %s: %s", target_date, exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("Error parsing CWA response for %s: %s", target_date, exc)
            return []

    @staticmethod
    def _extract_weather_elements(
        station: Dict[str, Any],
    ) -> Tuple[Optional[float], Optional[float], Optional[float], Optional[float], Optional[float]]:
        """Extract (temp_avg, temp_max, temp_min, rainfall_mm, humidity_pct)
        from a single CWA station record.

        The CWA daily observation JSON nests weather values under
        ``WeatherElement`` or ``ObsTime`` sub-structures.  This helper
        is intentionally lenient — missing fields yield ``None``.
        """

        def _safe(val: Any) -> Optional[float]:
            if val is None or val == "" or val == "-999" or val == "-999.0":
                return None
            try:
                f = float(val)
                return None if f <= -999 else f
            except (TypeError, ValueError):
                return None

        weather = station.get("WeatherElement", station)

        # Temperature
        temp_info = weather.get("AirTemperature", {})
        temp_avg = _safe(temp_info.get("Average"))
        temp_max = _safe(temp_info.get("Maximum"))
        temp_min = _safe(temp_info.get("Minimum"))

        # Fallback: direct keys at top level or under DailyExtreme
        if temp_avg is None:
            temp_avg = _safe(weather.get("TEMP"))
        if temp_max is None:
            daily_high = weather.get("DailyExtreme", {}).get("DailyHigh", {})
            temp_max = _safe(daily_high.get("TemperatureInfo", {}).get("AirTemperature"))
        if temp_min is None:
            daily_low = weather.get("DailyExtreme", {}).get("DailyLow", {})
            temp_min = _safe(daily_low.get("TemperatureInfo", {}).get("AirTemperature"))

        # Rainfall
        precip_info = weather.get("Now", {}).get("Precipitation", {})
        rainfall = _safe(precip_info.get("Accumulation"))
        if rainfall is None:
            rainfall = _safe(weather.get("RAIN"))
        if rainfall is None:
            rainfall = _safe(weather.get("Precipitation"))

        # Humidity
        humidity_info = weather.get("RelativeHumidity", {})
        humidity = _safe(humidity_info.get("Average"))
        if humidity is None:
            humidity = _safe(weather.get("HUMD"))
        # CWA sometimes returns humidity as a 0-1 ratio
        if humidity is not None and humidity <= 1.0:
            humidity = humidity * 100.0

        return temp_avg, temp_max, temp_min, rainfall, humidity

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def fetch_daily_weather(self, target_date: date, db: Session) -> int:
        """Fetch daily weather for all mapped stations and store per-county.

        Returns the number of newly inserted (or updated) weather rows.
        """
        county_lookup = self._build_county_lookup(db)
        stations = self._fetch_observations(target_date)

        if not stations:
            logger.info("No weather station data returned for %s.", target_date)
            return 0

        # Aggregate per county: collect readings, then average.
        county_readings: Dict[int, List[Tuple[
            Optional[float], Optional[float], Optional[float],
            Optional[float], Optional[float],
        ]]] = {}

        for station in stations:
            station_id = station.get("StationId", station.get("stationId", ""))
            county_code = STATION_COUNTY_MAP.get(station_id)
            if county_code is None:
                continue
            county_id = county_lookup.get(county_code)
            if county_id is None:
                continue

            elements = self._extract_weather_elements(station)
            county_readings.setdefault(county_id, []).append(elements)

        inserted = 0
        for county_id, readings in county_readings.items():
            temp_avg = self._avg_non_none([r[0] for r in readings])
            temp_max = self._max_non_none([r[1] for r in readings])
            temp_min = self._min_non_none([r[2] for r in readings])
            rainfall = self._sum_non_none_or_max([r[3] for r in readings])
            humidity = self._avg_non_none([r[4] for r in readings])

            # Upsert: skip if already exists
            existing = (
                db.query(WeatherData.id)
                .filter(
                    WeatherData.observation_date == target_date,
                    WeatherData.county_id == county_id,
                )
                .first()
            )
            if existing is not None:
                # Update existing record with fresh data
                db.query(WeatherData).filter(WeatherData.id == existing.id).update(
                    {
                        WeatherData.temp_avg: temp_avg,
                        WeatherData.temp_max: temp_max,
                        WeatherData.temp_min: temp_min,
                        WeatherData.rainfall_mm: rainfall,
                        WeatherData.humidity_pct: humidity,
                    }
                )
            else:
                record = WeatherData(
                    observation_date=target_date,
                    county_id=county_id,
                    temp_avg=temp_avg,
                    temp_max=temp_max,
                    temp_min=temp_min,
                    rainfall_mm=rainfall,
                    humidity_pct=humidity,
                )
                db.add(record)
                inserted += 1

        if county_readings:
            db.commit()

        logger.info(
            "Date %s: processed %d stations across %d counties, %d new rows.",
            target_date,
            len(stations),
            len(county_readings),
            inserted,
        )
        return inserted

    def fetch_date_range(
        self,
        start_date: date,
        end_date: date,
        db: Session,
    ) -> int:
        """Fetch weather observations for each day in ``[start_date, end_date]``.

        Returns total newly inserted rows.
        """
        if start_date > end_date:
            raise ValueError(
                f"start_date ({start_date}) must not be after end_date ({end_date})."
            )

        total_inserted = 0
        current = start_date
        total_days = (end_date - start_date).days + 1
        day_num = 0

        while current <= end_date:
            day_num += 1
            logger.info(
                "[%d/%d] Fetching weather for %s ...",
                day_num,
                total_days,
                current,
            )

            inserted = self.fetch_daily_weather(current, db)
            total_inserted += inserted

            current += timedelta(days=1)
            if current <= end_date and self.RATE_LIMIT > 0:
                time.sleep(self.RATE_LIMIT)

        logger.info(
            "Weather date range complete: %s to %s — %d new records.",
            start_date,
            end_date,
            total_inserted,
        )
        return total_inserted

    # ------------------------------------------------------------------
    # Numeric aggregation helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _avg_non_none(values: List[Optional[float]]) -> Optional[float]:
        """Return the mean of non-None values, or None if all are None."""
        valid = [v for v in values if v is not None]
        return sum(valid) / len(valid) if valid else None

    @staticmethod
    def _max_non_none(values: List[Optional[float]]) -> Optional[float]:
        valid = [v for v in values if v is not None]
        return max(valid) if valid else None

    @staticmethod
    def _min_non_none(values: List[Optional[float]]) -> Optional[float]:
        valid = [v for v in values if v is not None]
        return min(valid) if valid else None

    @staticmethod
    def _sum_non_none_or_max(values: List[Optional[float]]) -> Optional[float]:
        """For rainfall: average across stations in the same county.

        Each station independently reports cumulative daily rainfall,
        so averaging gives a representative county-level estimate.
        """
        valid = [v for v in values if v is not None]
        return sum(valid) / len(valid) if valid else None
