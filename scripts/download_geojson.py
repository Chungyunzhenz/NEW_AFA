"""Download Taiwan county TopoJSON from the taiwan-atlas GitHub repo.

Usage:
    python scripts/download_geojson.py

Downloads ``counties-10t.json`` from dkaoster/taiwan-atlas and saves it
to ``backend/app/data/geojson/taiwan_counties.json``.
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Source URL from the dkaoster/taiwan-atlas repository
# ---------------------------------------------------------------------------
GEOJSON_URL = (
    "https://raw.githubusercontent.com/dkaoster/taiwan-atlas/"
    "master/atlas/counties-10t.json"
)

OUTPUT_DIR = PROJECT_ROOT / "backend" / "app" / "data" / "geojson"
OUTPUT_FILE = OUTPUT_DIR / "taiwan_counties.json"

REQUEST_TIMEOUT = 60


def download() -> None:
    """Download the TopoJSON file and write it to disk."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Downloading Taiwan counties TopoJSON from:\n  %s", GEOJSON_URL)

    try:
        resp = requests.get(GEOJSON_URL, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.error("Download failed: %s", exc)
        sys.exit(1)

    # Validate that the response is parseable JSON (or at least non-empty)
    content = resp.text
    if not content.strip():
        logger.error("Received an empty response from %s", GEOJSON_URL)
        sys.exit(1)

    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.error("Response is not valid JSON: %s", exc)
        sys.exit(1)

    # Re-serialize with consistent formatting for diffability
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

    file_size_kb = OUTPUT_FILE.stat().st_size / 1024
    logger.info(
        "Saved to %s (%.1f KB).",
        OUTPUT_FILE,
        file_size_kb,
    )

    # Print a brief summary of the TopoJSON structure
    topo_type = data.get("type", "unknown")
    objects = list(data.get("objects", {}).keys())
    logger.info("TopoJSON type=%s, objects=%s", topo_type, objects)


if __name__ == "__main__":
    download()
