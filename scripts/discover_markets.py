"""Discover missing markets by probing the AMIS API.

Fetches recent trading data to find all distinct market codes,
then compares against the markets table to identify missing entries.
Outputs a JSON patch that can be appended to markets.json.

Usage:
    python scripts/discover_markets.py                # default 14 days
    python scripts/discover_markets.py --days 30      # wider scan
    python scripts/discover_markets.py --output-json  # print JSON patch
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Project bootstrap
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.models import Market, County  # noqa: E402
from app.services.data_collector import AMISDataCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Market name -> county_code heuristic mapping
# ---------------------------------------------------------------------------
COUNTY_NAME_ALIASES: Dict[str, str] = {
    "台北": "63000", "臺北": "63000",
    "新北": "65000", "三重": "65000", "板橋": "65000",
    "桃園": "68000",
    "台中": "66000", "臺中": "66000", "豐原": "66000",
    "彰化": "10007", "溪湖": "10007",
    "南投": "10008",
    "雲林": "10009", "西螺": "10009",
    "嘉義": "10020",
    "台南": "67000", "臺南": "67000", "永康": "67000",
    "高雄": "64000", "鳳山": "64000",
    "屏東": "10013",
    "台東": "10014", "臺東": "10014",
    "花蓮": "10015",
    "宜蘭": "10002",
    "基隆": "10017",
    "新竹": "10018",
    "苗栗": "10005",
}


def fetch_distinct_markets(
    collector: AMISDataCollector, days: int = 14
) -> Dict[str, str]:
    """Fetch recent API data to collect all (market_code, market_name) pairs.

    Returns a dict of market_code -> market_name.
    """
    end_date = date.today() - timedelta(days=1)
    start_date = end_date - timedelta(days=days - 1)

    discovered: Dict[str, str] = {}
    current = start_date

    while current <= end_date:
        data = collector._fetch_api(current)
        if data:
            for row in data:
                code = str(row.get("市場代號") or "").strip()
                name = (row.get("市場名稱") or "").strip()
                if code and code not in discovered:
                    discovered[code] = name
            logger.info(
                "  %s: %d rows, %d unique markets so far",
                current, len(data), len(discovered),
            )
        current += timedelta(days=1)

    return discovered


def guess_county_code(market_name: str, county_lookup: Dict[str, int]) -> Optional[str]:
    """Guess the county_code from a market name using heuristic aliases.

    Returns the county_code string or None if no match.
    """
    for alias, county_code in COUNTY_NAME_ALIASES.items():
        if alias in market_name:
            # Verify the county_code actually exists in the DB
            if county_code in county_lookup:
                return county_code
    return None


def compare_with_db(
    db, discovered: Dict[str, str]
) -> Tuple[List[Dict], List[Dict]]:
    """Compare discovered markets against the DB.

    Returns (known, missing) where each element is a list of dicts with
    market_code, market_name, and (for missing) guessed county_code.
    """
    existing_codes: Set[str] = {
        m.market_code for m in db.query(Market).all()
    }
    county_lookup: Dict[str, int] = {
        c.county_code: c.id for c in db.query(County).all()
    }

    known = []
    missing = []

    for code, name in sorted(discovered.items()):
        entry = {"market_code": code, "market_name": name}
        if code in existing_codes:
            known.append(entry)
        else:
            guessed = guess_county_code(name, county_lookup)
            entry["county_code"] = guessed
            missing.append(entry)

    return known, missing


def main() -> None:
    args = parse_args()

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        collector = AMISDataCollector()

        print(f"\nScanning AMIS API for the last {args.days} day(s) ...")
        discovered = fetch_distinct_markets(collector, days=args.days)
        print(f"\nDiscovered {len(discovered)} distinct market codes from API.")

        known, missing = compare_with_db(db, discovered)

        # --- Report ---
        print(f"\n{'=' * 60}")
        print(f"  MARKET DISCOVERY REPORT")
        print(f"{'=' * 60}")
        print(f"  Already in DB:  {len(known)}")
        print(f"  Missing from DB: {len(missing)}")

        if known:
            print(f"\n  --- Known Markets ---")
            for m in known:
                print(f"    {m['market_code']:6s}  {m['market_name']}")

        if missing:
            print(f"\n  --- Missing Markets (need to add) ---")
            for m in missing:
                county = m["county_code"] or "???"
                print(f"    {m['market_code']:6s}  {m['market_name']:10s}  -> county_code: {county}")

            if args.output_json:
                # Output JSON patch for markets.json
                patch = []
                for m in missing:
                    if m["county_code"]:
                        patch.append({
                            "market_code": m["market_code"],
                            "market_name": m["market_name"],
                            "county_code": m["county_code"],
                        })
                    else:
                        patch.append({
                            "market_code": m["market_code"],
                            "market_name": m["market_name"],
                            "county_code": "TODO",
                        })

                print(f"\n  --- JSON Patch (append to markets.json) ---")
                print(json.dumps(patch, ensure_ascii=False, indent=2))
        else:
            print("\n  All API markets are already in the database!")

    finally:
        db.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Discover missing markets from the AMIS API.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=14,
        help="Number of recent days to scan (default: 14).",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output a JSON patch for markets.json.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
