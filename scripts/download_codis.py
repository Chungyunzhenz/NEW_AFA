"""Download historical weather data from CODiS (Climate Observation Data Inquiry System).

CODiS is the official climate data portal of Taiwan's Central Weather Administration.
This script automates downloading daily observation data for 18 major stations
covering 2005-2025, producing CSV files compatible with import_codis_csv.py.

Usage:
    python scripts/download_codis.py probe
    python scripts/download_codis.py download --start-year 2005 --end-year 2025
    python scripts/download_codis.py download --station 466920 --start-year 2024 --end-year 2024
    python scripts/download_codis.py status
"""
from __future__ import annotations

import argparse
import calendar
import csv
import io
import json
import logging
import signal
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BASE_URL = "https://codis.cwa.gov.tw"

# Browser-like headers for the initial page GET
PAGE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Headers for XHR API calls (form-encoded POST)
API_HEADERS = {
    "User-Agent": PAGE_HEADERS["User-Agent"],
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/StationData",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

TARGET_STATIONS: Dict[str, str] = {
    "466920": "台北",
    "466910": "鞍部",
    "466940": "基隆",
    "467080": "宜蘭",
    "467571": "新竹",
    "467280": "苗栗",
    "467490": "台中",
    "467270": "田中",
    "467650": "日月潭",
    "467290": "古坑",
    "467480": "嘉義",
    "467410": "台南",
    "467441": "高雄",
    "467590": "恆春",
    "467660": "台東",
    "466990": "花蓮",
    "467350": "澎湖",
    "467110": "金門",
    "467990": "馬祖",
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "codis_downloads"
PROGRESS_FILE = OUTPUT_DIR / ".progress.json"


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_requested = False


def _signal_handler(signum, frame):
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("Interrupt received, will stop after current request...")


signal.signal(signal.SIGINT, _signal_handler)


# ---------------------------------------------------------------------------
# ProgressTracker
# ---------------------------------------------------------------------------
class ProgressTracker:
    """Track download progress for resume capability."""

    def __init__(self, path: Path = PROGRESS_FILE):
        self.path = path
        self._data: Dict[str, Any] = {"completed": {}, "failed": {}}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                logger.warning("Progress file corrupted, starting fresh")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def is_done(self, station: str, year: int, month: int) -> bool:
        key = f"{station}_{year}_{month:02d}"
        return key in self._data.get("completed", {})

    def mark_done(self, station: str, year: int, month: int, rows: int):
        key = f"{station}_{year}_{month:02d}"
        self._data.setdefault("completed", {})[key] = {
            "rows": rows,
            "ts": datetime.now().isoformat(),
        }
        self._data.get("failed", {}).pop(key, None)
        self.save()

    def mark_failed(self, station: str, year: int, month: int, reason: str):
        key = f"{station}_{year}_{month:02d}"
        self._data.setdefault("failed", {})[key] = {
            "reason": reason,
            "ts": datetime.now().isoformat(),
        }
        self.save()

    def summary(self) -> Dict[str, Any]:
        completed = self._data.get("completed", {})
        failed = self._data.get("failed", {})
        total_rows = sum(v.get("rows", 0) for v in completed.values())
        return {
            "completed_chunks": len(completed),
            "failed_chunks": len(failed),
            "total_rows": total_rows,
            "failed_details": failed,
        }


# ---------------------------------------------------------------------------
# CODiSClient
# ---------------------------------------------------------------------------
class CODiSClient:
    """HTTP client for the CODiS /api/station endpoint.

    Uses form-encoded POST with X-Requested-With header (mimicking jQuery $.ajax).
    """

    def __init__(self, delay: float = 1.5):
        self.delay = delay
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        s = requests.Session()
        s.verify = False
        # Get initial cookies by loading the page
        try:
            resp = s.get(
                f"{BASE_URL}/StationData", headers=PAGE_HEADERS, timeout=15
            )
            resp.raise_for_status()
            logger.info("CODiS session cookies acquired")
        except requests.RequestException as e:
            logger.warning("Failed to get session cookies: %s (continuing)", e)
        return s

    def _post_form(self, endpoint: str, form_data: dict, timeout: int = 30) -> dict:
        """Send form-encoded POST and return parsed JSON."""
        url = f"{BASE_URL}{endpoint}"
        resp = self.session.post(
            url, data=form_data, headers=API_HEADERS, timeout=timeout
        )
        resp.raise_for_status()
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type and "javascript" not in content_type:
            raise ValueError(
                f"Non-JSON response (Content-Type: {content_type}): "
                + resp.text[:200]
            )
        return resp.json()

    def probe(self) -> Dict[str, Any]:
        """Test the API with a known station/month and report results."""
        form_data = {
            "date": "2024-01",
            "type": "report_month",
            "stn_ID": "466920",
            "stn_type": "cwb",
            "start": "2024-01-01T00:00:00",
            "end": "2024-01-31T23:59:00",
        }
        result: Dict[str, Any] = {"endpoint": "/api/station", "body": form_data}
        try:
            data = self._post_form("/api/station", form_data)
            result["status"] = "OK"
            result["api_code"] = data.get("code")
            result["message"] = data.get("message", "")

            if (
                isinstance(data.get("data"), list)
                and data["data"]
                and isinstance(data["data"][0], dict)
            ):
                station_block = data["data"][0]
                dts = station_block.get("dts", [])
                result["has_data"] = len(dts) > 0
                result["record_count"] = len(dts)
                if dts and isinstance(dts[0], dict):
                    result["sample_keys"] = list(dts[0].keys())[:10]
                    # Show a parsed sample
                    sample = self._extract_daily(dts[0])
                    result["sample_record"] = sample
            else:
                result["has_data"] = False
        except requests.exceptions.HTTPError as e:
            result["status"] = f"HTTP {e.response.status_code}"
            result["has_data"] = False
        except Exception as e:
            result["status"] = f"ERROR: {e}"
            result["has_data"] = False

        return result

    def fetch_month(
        self, station_id: str, year: int, month: int
    ) -> List[Dict[str, Any]]:
        """Fetch daily data for one station/month.

        Returns list of dicts with keys: date, temp_avg, temp_max, temp_min,
        rainfall_mm, humidity_pct.
        """
        last_day = calendar.monthrange(year, month)[1]
        form_data = {
            "date": f"{year}-{month:02d}",
            "type": "report_month",
            "stn_ID": station_id,
            "stn_type": "cwb",
            "start": f"{year}-{month:02d}-01T00:00:00",
            "end": f"{year}-{month:02d}-{last_day:02d}T23:59:00",
        }

        data = self._post_form("/api/station", form_data)

        if data.get("code") != 200:
            msg = data.get("message", "unknown error")
            raise ValueError(f"API error code {data.get('code')}: {msg}")

        if not isinstance(data.get("data"), list) or not data["data"]:
            return []

        station_block = data["data"][0]
        dts = station_block.get("dts", [])

        records = []
        for entry in dts:
            if not isinstance(entry, dict):
                continue
            rec = self._extract_daily(entry)
            if rec:
                records.append(rec)
        return records

    @staticmethod
    def _extract_daily(entry: dict) -> Optional[Dict[str, Any]]:
        """Extract weather fields from a CODiS daily record.

        CODiS response fields are nested objects, e.g.:
            AirTemperature: {Mean, Maximum, Minimum, ...}
            Precipitation: {Accumulation, ...}
            RelativeHumidity: {Mean, ...}
        """
        # Parse date
        raw_date = entry.get("DataDate", "")
        if not raw_date:
            return None
        try:
            obs_date = datetime.strptime(
                str(raw_date)[:10], "%Y-%m-%d"
            ).date()
        except ValueError:
            return None

        def _nested_float(
            obj_key: str, field_key: str, min_valid: float = -50.0
        ) -> Optional[float]:
            obj = entry.get(obj_key)
            if not isinstance(obj, dict):
                return None
            val = obj.get(field_key)
            if val is None:
                return None
            try:
                f = float(val)
                return None if f < min_valid else f
            except (ValueError, TypeError):
                return None

        return {
            "date": obs_date.isoformat(),
            "temp_avg": _nested_float("AirTemperature", "Mean", -50),
            "temp_max": _nested_float("AirTemperature", "Maximum", -50),
            "temp_min": _nested_float("AirTemperature", "Minimum", -50),
            "rainfall_mm": _nested_float("Precipitation", "Accumulation", 0),
            "humidity_pct": _nested_float("RelativeHumidity", "Mean", 0),
        }


# ---------------------------------------------------------------------------
# CSV Writer
# ---------------------------------------------------------------------------
def save_station_csv(
    station_id: str,
    station_name: str,
    year: int,
    all_records: List[Dict[str, Any]],
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Append/merge records into {station_id}_{year}.csv.

    Output format is compatible with import_codis_csv.py.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{station_id}_{year}.csv"

    # Load existing records for merging partial downloads
    existing: Dict[str, Dict[str, Any]] = {}
    if filepath.exists():
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
            header_idx = -1
            for i, line in enumerate(lines):
                if "\u89c0\u6e2c\u6642\u9593" in line:  # 觀測時間
                    header_idx = i
                    break
            if header_idx >= 0:
                reader = csv.DictReader(lines[header_idx:])
                for row in reader:
                    d = row.get("\u89c0\u6e2c\u6642\u9593", "").strip()
                    if d:
                        existing[d] = row
        except Exception:
            pass

    # Merge new records
    for rec in all_records:
        existing[rec["date"]] = {
            "\u89c0\u6e2c\u6642\u9593": rec["date"],
            "\u6c23\u6eab(\u2103)": _fmt(rec.get("temp_avg")),
            "\u6700\u9ad8\u6c23\u6eab(\u2103)": _fmt(rec.get("temp_max")),
            "\u6700\u4f4e\u6c23\u6eab(\u2103)": _fmt(rec.get("temp_min")),
            "\u964d\u6c34\u91cf(mm)": _fmt(rec.get("rainfall_mm")),
            "\u76f8\u5c0d\u6ebc\u5ea6(%)": _fmt(rec.get("humidity_pct")),
        }

    sorted_records = sorted(existing.values(), key=lambda r: r["\u89c0\u6e2c\u6642\u9593"])

    fieldnames = [
        "\u89c0\u6e2c\u6642\u9593",     # 觀測時間
        "\u6c23\u6eab(\u2103)",           # 氣溫(℃)
        "\u6700\u9ad8\u6c23\u6eab(\u2103)", # 最高氣溫(℃)
        "\u6700\u4f4e\u6c23\u6eab(\u2103)", # 最低氣溫(℃)
        "\u964d\u6c34\u91cf(mm)",         # 降水量(mm)
        "\u76f8\u5c0d\u6ebc\u5ea6(%)",    # 相對溼度(%)
    ]

    buf = io.StringIO()
    buf.write(f"\u7ad9\u865f,{station_id}\n")  # 站號
    buf.write(f"\u7ad9\u540d,{station_name}\n")  # 站名
    buf.write("\n")

    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(sorted_records)

    filepath.write_text(buf.getvalue(), encoding="utf-8")
    return filepath


def _fmt(val: Optional[float]) -> str:
    if val is None:
        return ""
    return f"{val:.1f}"


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------
def cmd_probe(args):
    """Probe CODiS API endpoint."""
    logger.info("=== CODiS API Probe ===")
    client = CODiSClient()
    result = client.probe()

    print("\n" + "=" * 60)
    print("Probe Result")
    print("=" * 60)
    print(f"  Endpoint: {result['endpoint']}")
    print(f"  Status:   {result.get('status', '?')}")

    if result.get("has_data"):
        print(f"  Records:  {result.get('record_count', '?')}")
        print(f"  Fields:   {result.get('sample_keys', [])}")
        if result.get("sample_record"):
            print(f"  Sample:   {result['sample_record']}")
        print("\n  >> API is working! Ready to download.")
    else:
        print(f"  API Code: {result.get('api_code', '?')}")
        print(f"  Message:  {result.get('message', '?')}")
        print("\n  >> API not returning data.")
        print("  Possible: WAF block, IP restriction, or API change")
    print()


def cmd_download(args):
    """Download historical data for all target stations."""
    start_year = args.start_year
    end_year = args.end_year
    delay = args.delay

    stations = TARGET_STATIONS
    if args.station:
        if args.station not in TARGET_STATIONS:
            logger.error("Station %s not in target list", args.station)
            sys.exit(1)
        stations = {args.station: TARGET_STATIONS[args.station]}

    tracker = ProgressTracker()
    client = CODiSClient(delay=delay)

    # Probe first
    logger.info("Probing API...")
    probe_result = client.probe()
    if not probe_result.get("has_data"):
        logger.error("API probe failed: %s", probe_result.get("status"))
        logger.error("Run: python scripts/download_codis.py probe")
        sys.exit(1)
    logger.info("API OK, starting download")

    # Calculate total work
    total_chunks = len(stations) * (end_year - start_year + 1) * 12
    done_count = sum(
        1
        for sid in stations
        for y in range(start_year, end_year + 1)
        for m in range(1, 13)
        if tracker.is_done(sid, y, m)
    )

    logger.info(
        "=== Download: %d stations x %d years x 12 months = %d requests (done: %d) ===",
        len(stations), end_year - start_year + 1, total_chunks, done_count,
    )

    downloaded = done_count
    errors = 0

    for station_id, station_name in stations.items():
        for year in range(start_year, end_year + 1):
            year_records: List[Dict[str, Any]] = []
            year_had_new = False

            for month in range(1, 13):
                if _shutdown_requested:
                    logger.info("User interrupted, saving progress...")
                    tracker.save()
                    _print_status(tracker)
                    sys.exit(0)

                today = date.today()
                if year > today.year or (year == today.year and month > today.month):
                    continue

                if tracker.is_done(station_id, year, month):
                    continue

                downloaded += 1
                logger.info(
                    "[%d/%d] %s(%s) %d-%02d ...",
                    downloaded, total_chunks, station_name, station_id, year, month,
                )

                try:
                    records = _fetch_with_retry(client, station_id, year, month)
                    year_records.extend(records)
                    tracker.mark_done(station_id, year, month, len(records))
                    year_had_new = True

                    if records:
                        logger.info("  -> %d daily records", len(records))
                    else:
                        logger.info("  -> no data (station may not exist for this period)")

                except Exception as e:
                    errors += 1
                    tracker.mark_failed(station_id, year, month, str(e))
                    logger.warning("  -> FAILED: %s", e)

                time.sleep(delay)

            if year_had_new and year_records:
                filepath = save_station_csv(station_id, station_name, year, year_records)
                logger.info("Saved %s (%d records)", filepath.name, len(year_records))

    tracker.save()
    logger.info("=" * 60)
    logger.info("Download complete!")
    _print_status(tracker)
    if errors:
        logger.warning("%d failed requests, re-run download to retry", errors)


def _fetch_with_retry(
    client: CODiSClient, station_id: str, year: int, month: int, max_retries: int = 3
) -> List[Dict[str, Any]]:
    """Fetch with exponential backoff retry."""
    last_err = None
    for attempt in range(max_retries):
        try:
            return client.fetch_month(station_id, year, month)
        except requests.exceptions.HTTPError as e:
            last_err = e
            status = e.response.status_code if e.response is not None else 0
            if status == 403:
                logger.warning("  WAF 403 block, waiting 30s...")
                time.sleep(30)
                if attempt >= 1:
                    raise
            elif status in (429, 503):
                wait = min(5 * (2 ** attempt), 60)
                logger.warning("  HTTP %d, retrying in %ds...", status, wait)
                time.sleep(wait)
            else:
                raise
        except requests.exceptions.ConnectionError as e:
            last_err = e
            wait = 5 * (2 ** attempt)
            logger.warning("  Connection error, retrying in %ds...", wait)
            time.sleep(wait)
        except ValueError as e:
            # API returned error code
            last_err = e
            if attempt < max_retries - 1:
                wait = 5 * (2 ** attempt)
                logger.warning("  API error, retrying in %ds...", wait)
                time.sleep(wait)
            else:
                raise

    raise last_err  # type: ignore[misc]


def cmd_status(args):
    """Show download progress."""
    tracker = ProgressTracker()
    _print_status(tracker)


def _print_status(tracker: ProgressTracker):
    """Print formatted progress summary."""
    s = tracker.summary()
    total_possible = len(TARGET_STATIONS) * 21 * 12

    print("\n" + "=" * 60)
    print("Download Progress")
    print("=" * 60)
    print(f"  Completed: {s['completed_chunks']} / {total_possible} chunks")
    print(f"  Failed:    {s['failed_chunks']} chunks")
    print(f"  Total:     {s['total_rows']} daily records")

    if s["failed_details"]:
        print("\n  Failed details:")
        for key, detail in sorted(s["failed_details"].items()):
            print(f"    {key}: {detail['reason'][:80]}")

    print("\n  Per-station progress:")
    for sid, name in TARGET_STATIONS.items():
        done = sum(
            1 for y in range(2005, 2026) for m in range(1, 13)
            if tracker.is_done(sid, y, m)
        )
        total = 21 * 12
        bar_len = 20
        filled = int(bar_len * done / total) if total else 0
        bar = "#" * filled + "." * (bar_len - filled)
        pct = done / total * 100 if total else 0
        print(f"    {name:4s}({sid}): [{bar}] {pct:5.1f}% ({done}/{total})")

    csv_files = sorted(OUTPUT_DIR.glob("*.csv")) if OUTPUT_DIR.exists() else []
    if csv_files:
        total_size = sum(f.stat().st_size for f in csv_files)
        print(f"\n  CSV files: {len(csv_files)} / {total_size / 1024:.1f} KB")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download historical weather data from CODiS.",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("probe", help="Test CODiS API endpoint")

    dl = sub.add_parser("download", help="Download historical weather data")
    dl.add_argument("--start-year", type=int, default=2005)
    dl.add_argument("--end-year", type=int, default=2025)
    dl.add_argument("--station", type=str, default=None, help="Single station ID")
    dl.add_argument("--delay", type=float, default=1.5, help="Seconds between requests")

    sub.add_parser("status", help="Show download progress")

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == "probe":
        cmd_probe(args)
    elif args.command == "download":
        cmd_download(args)
    elif args.command == "status":
        cmd_status(args)
    else:
        print("Usage: python scripts/download_codis.py {probe|download|status}")
        print("  probe    - Test API endpoint")
        print("  download - Download historical data")
        print("  status   - Show download progress")
        sys.exit(1)


if __name__ == "__main__":
    main()
