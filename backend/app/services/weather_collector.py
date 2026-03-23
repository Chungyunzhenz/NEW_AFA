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
    "C0A520": "65000",   # 板橋/新北 (realtime)
    "466881": "65000",   # 板橋/新北 (historical C-B0024-001)
    "467050": "10017",   # 基隆 (Keelung, realtime)
    "466940": "10017",   # 基隆 (historical C-B0024-001)
    "C0C700": "10002",   # 宜蘭 (Yilan, realtime)
    "467080": "10002",   # 宜蘭 (historical C-B0024-001)
    "C0D100": "68000",   # 桃園 (Taoyuan)
    "C0E520": "10004",   # 新竹縣
    "467571": "10018",   # 新竹市
    "C0E400": "10005",   # 苗栗 (Miaoli, realtime)
    "467280": "10005",   # 苗栗/後龍 (historical C-B0024-001)
    # Central Taiwan
    "467490": "66000",   # 臺中 (Taichung)
    "C0F9A0": "10007",   # 彰化 (Changhua, realtime)
    "467270": "10007",   # 彰化/田中 (historical C-B0024-001)
    "C0G730": "10008",   # 南投 (Nantou, realtime)
    "467650": "10008",   # 南投/日月潭 (historical C-B0024-001)
    "C0K330": "10009",   # 雲林 (Yunlin, realtime)
    "467290": "10009",   # 雲林/古坑 (historical C-B0024-001)
    # Southern Taiwan
    "C0M790": "10010",   # 嘉義縣 (朴子站, realtime)
    "467480": "10020",   # 嘉義市
    "467410": "67000",   # 臺南 (Tainan)
    "467440": "64000",   # 高雄 (Kaohsiung, realtime)
    "467441": "64000",   # 高雄 (historical C-B0024-001)
    "467590": "10013",   # 屏東 (Pingtung / Hengchun)
    # Eastern Taiwan
    "467660": "10014",   # 臺東 (Taitung)
    "466990": "10015",   # 花蓮 (Hualien)
    # Offshore
    "467300": "10016",   # 澎湖/東吉島 (Penghu)
    "467350": "10016",   # 澎湖 (historical C-B0024-001)
    "467110": "09020",   # 金門 (Kinmen)
    "467990": "09007",   # 連江 (Lienchiang / Matsu)
}

# CWA dataset IDs
CWA_REALTIME_DATASET_ID = "O-A0003-001"    # 即時觀測（最新資料）
CWA_HISTORICAL_DATASET_ID = "C-B0024-001"  # 歷史逐日氣候資料（地面氣候日報）

# 即時 dataset 只回傳最近的觀測值，超過此天數應改用歷史 dataset
_REALTIME_CUTOFF_DAYS = 2


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

    def _is_recent(self, target_date: date) -> bool:
        """Return True if *target_date* is within the realtime cutoff window."""
        return (date.today() - target_date).days <= _REALTIME_CUTOFF_DAYS

    def _fetch_observations(self, target_date: date) -> List[Dict[str, Any]]:
        """Call CWA API and return the station-level observations list.

        Uses the realtime dataset (``O-A0003-001``) for recent dates (within
        the cutoff window) and the daily climate dataset (``C-B0024-001``)
        as a fallback.

        **Important**: C-B0024-001 does *not* support arbitrary historical
        dates — it always returns the latest available day regardless of
        ``dataDate``.  This method validates that the returned data actually
        matches *target_date* and returns an empty list when it does not.
        """
        use_realtime = self._is_recent(target_date)
        dataset_id = CWA_REALTIME_DATASET_ID if use_realtime else CWA_HISTORICAL_DATASET_ID

        params: Dict[str, str] = {
            "Authorization": self.api_key,
            "format": "JSON",
        }

        url = f"{settings.CWA_API_BASE}/{dataset_id}"
        logger.debug(
            "Requesting CWA observations for %s (dataset=%s)", target_date, dataset_id,
        )

        try:
            resp = requests.get(url, params=params, timeout=self.REQUEST_TIMEOUT, verify=settings.VERIFY_SSL)
            resp.raise_for_status()
            payload = resp.json()

            records = payload.get("records", {})

            if use_realtime:
                # Realtime: records.Station (list of station dicts)
                stations = records.get("Station", records.get("station", []))
                if not isinstance(stations, list):
                    logger.warning(
                        "Unexpected CWA response structure for %s (dataset=%s).",
                        target_date, dataset_id,
                    )
                    return []
                return stations

            # C-B0024-001: records.location (list of location dicts)
            locations = records.get("location", [])
            if not isinstance(locations, list) or not locations:
                logger.warning(
                    "No locations in CWA daily-climate response for %s.", target_date,
                )
                return []

            # Validate: C-B0024-001 ignores dataDate and returns the latest
            # available day.  Only proceed if that day matches target_date.
            actual_date = self._extract_response_date(locations)
            if actual_date and actual_date != target_date:
                logger.warning(
                    "CWA C-B0024-001 returned data for %s but target was %s. "
                    "Historical backfill via API is not supported — "
                    "the CWA open-data API only provides recent observations.",
                    actual_date, target_date,
                )
                return []

            return self._normalize_historical(locations, target_date)

        except requests.RequestException as exc:
            logger.error("HTTP error fetching CWA data for %s: %s", target_date, exc)
            return []
        except (ValueError, KeyError) as exc:
            logger.error("Error parsing CWA response for %s: %s", target_date, exc)
            return []

    @staticmethod
    def _extract_response_date(locations: List[Dict[str, Any]]) -> Optional[date]:
        """Extract the actual observation date from a C-B0024-001 response."""
        try:
            daily = (
                locations[0]
                .get("stationObsStatistics", {})
                .get("AirTemperature", {})
                .get("daily", [])
            )
            if daily:
                return datetime.strptime(daily[0]["Date"], "%Y-%m-%d").date()
        except (IndexError, KeyError, ValueError):
            pass
        return None

    # ------------------------------------------------------------------
    # Historical data normalisation
    # ------------------------------------------------------------------
    @staticmethod
    def _normalize_historical(
        locations: List[Dict[str, Any]], target_date: date,
    ) -> List[Dict[str, Any]]:
        """Convert C-B0024-001 location records into flat station dicts.

        C-B0024-001 returns hourly observations and daily statistics per
        station.  We aggregate hourly values (rainfall sum, humidity avg)
        and use the daily statistics for temperature, producing a dict
        that ``_extract_weather_elements()`` can process via its fallback
        paths.
        """
        target_str = target_date.isoformat()
        normalised: List[Dict[str, Any]] = []

        for loc in locations:
            station_info = loc.get("station", {})
            station_id = station_info.get("StationID", "")

            # --- daily temperature stats ---
            stats = loc.get("stationObsStatistics", {})
            temp_daily_list = stats.get("AirTemperature", {}).get("daily", [])

            # Pick the entry matching target_date (API may return multiple)
            temp_daily: Dict[str, Any] = {}
            for entry in temp_daily_list:
                if entry.get("Date", "") == target_str:
                    temp_daily = entry
                    break
            if not temp_daily and temp_daily_list:
                temp_daily = temp_daily_list[0]

            mean_temp = temp_daily.get("Mean")
            max_temp = temp_daily.get("Maximum")
            min_temp = temp_daily.get("Minimum")

            # --- aggregate hourly observations ---
            obs_times = loc.get("stationObsTimes", {}).get("stationObsTime", [])
            total_precip = 0.0
            precip_count = 0
            humidity_values: List[float] = []

            for obs in obs_times:
                elements = obs.get("weatherElements", {})
                p = elements.get("Precipitation")
                if p not in (None, "", "-999", "X", "T"):
                    try:
                        total_precip += float(p)
                        precip_count += 1
                    except (ValueError, TypeError):
                        pass
                h = elements.get("RelativeHumidity")
                if h not in (None, "", "-999", "X"):
                    try:
                        humidity_values.append(float(h))
                    except (ValueError, TypeError):
                        pass

            avg_humidity = (
                sum(humidity_values) / len(humidity_values)
                if humidity_values else None
            )

            # Build a flat dict using keys that _extract_weather_elements()
            # picks up through its fallback chains.
            normalised.append({
                "StationId": station_id,
                "WeatherElement": {
                    "Mean": mean_temp,
                    "Maximum": max_temp,
                    "Minimum": min_temp,
                    "Precipitation": total_precip if precip_count else None,
                    "MeanRH": avg_humidity,
                    # empty dicts so .get() calls don't fail on None
                    "AirTemperature": {},
                    "RelativeHumidity": {},
                    "DailyExtreme": {},
                    "Now": {},
                },
            })

        return normalised

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

        # Temperature — try multiple paths for realtime / historical formats
        # Realtime O-A0003-001: AirTemperature is a plain string ("18.3")
        # Historical normalised: AirTemperature is an empty dict
        temp_info = weather.get("AirTemperature")
        if isinstance(temp_info, dict):
            temp_avg = _safe(temp_info.get("Average"))
            temp_max = _safe(temp_info.get("Maximum"))
            temp_min = _safe(temp_info.get("Minimum"))
        else:
            # Realtime: AirTemperature is the current reading (use as avg)
            temp_avg = _safe(temp_info)
            temp_max = None
            temp_min = None

        # Fallback: direct keys at top level or under DailyExtreme
        if temp_avg is None:
            temp_avg = _safe(weather.get("TEMP"))
        if temp_avg is None:
            temp_avg = _safe(weather.get("Mean"))
        if temp_avg is None:
            temp_avg = _safe(weather.get("MeanTemperature"))

        if temp_max is None:
            de = weather.get("DailyExtreme")
            if isinstance(de, dict):
                daily_high = de.get("DailyHigh", {})
                temp_max = _safe(daily_high.get("TemperatureInfo", {}).get("AirTemperature"))
        if temp_max is None:
            temp_max = _safe(weather.get("Maximum"))
        if temp_max is None:
            temp_max = _safe(weather.get("MaxTemperature"))

        if temp_min is None:
            de = weather.get("DailyExtreme")
            if isinstance(de, dict):
                daily_low = de.get("DailyLow", {})
                temp_min = _safe(daily_low.get("TemperatureInfo", {}).get("AirTemperature"))
        if temp_min is None:
            temp_min = _safe(weather.get("Minimum"))
        if temp_min is None:
            temp_min = _safe(weather.get("MinTemperature"))

        # Rainfall — try multiple paths
        # Realtime: Now.Precipitation is a string ("1.0"), not a dict
        now = weather.get("Now")
        if isinstance(now, dict):
            precip_val = now.get("Precipitation")
            if isinstance(precip_val, dict):
                rainfall = _safe(precip_val.get("Accumulation"))
            else:
                rainfall = _safe(precip_val)
        else:
            rainfall = None
        if rainfall is None:
            rainfall = _safe(weather.get("RAIN"))
        if rainfall is None:
            rainfall = _safe(weather.get("Precipitation"))
        if rainfall is None:
            rainfall = _safe(weather.get("Rainfall"))
        if rainfall is None:
            rainfall = _safe(weather.get("TotalRainfall"))

        # Humidity — try multiple paths
        # Realtime: RelativeHumidity is a string ("85"), not a dict
        humidity_val = weather.get("RelativeHumidity")
        if isinstance(humidity_val, dict):
            humidity = _safe(humidity_val.get("Average"))
        else:
            humidity = _safe(humidity_val)
        if humidity is None:
            humidity = _safe(weather.get("HUMD"))
        if humidity is None:
            humidity = _safe(weather.get("MeanRH"))
        if humidity is None:
            humidity = _safe(weather.get("RH"))
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
