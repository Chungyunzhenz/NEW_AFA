"""CWA API 測試腳本 — 驗證即時與歷史 dataset 的行為。

用法：
    cd backend
    python -m scripts.test_cwa_api

或直接：
    python scripts/test_cwa_api.py

需要在 backend/.env 設定 CWA_API_KEY。
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# 載入 API Key
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent.parent / "backend" / ".env"

def _load_api_key() -> str:
    """Try .env file, then environment variable."""
    # Try .env
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("CWA_API_KEY=") and not line.startswith("#"):
                val = line.split("=", 1)[1].strip().strip('"').strip("'")
                if val:
                    return val
    # Fallback to env var
    val = os.environ.get("CWA_API_KEY", "")
    if not val:
        print("ERROR: CWA_API_KEY 未設定。請在 backend/.env 或環境變數中設定。")
        sys.exit(1)
    return val


API_KEY = _load_api_key()
BASE_URL = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
VERIFY_SSL = False

# 測站對照表（與 weather_collector.py 一致）
STATION_COUNTY_MAP = {
    "466920": "臺北", "466910": "新北(鞍部)", "C0A520": "新北(板橋)",
    "467050": "基隆", "C0C700": "宜蘭", "C0D100": "桃園",
    "C0E520": "新竹縣", "467571": "新竹市", "C0E400": "苗栗",
    "467490": "臺中", "C0F9A0": "彰化", "C0G730": "南投",
    "C0K330": "雲林", "C0M790": "嘉義縣", "467480": "嘉義市",
    "467410": "臺南", "467440": "高雄", "467590": "屏東",
    "467660": "臺東", "466990": "花蓮", "467300": "澎湖",
    "467110": "金門", "467990": "連江",
}

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def fetch_dataset(dataset_id: str, extra_params: dict | None = None) -> dict:
    """Call CWA API and return the full JSON response."""
    params = {"Authorization": API_KEY, "format": "JSON"}
    if extra_params:
        params.update(extra_params)
    url = f"{BASE_URL}/{dataset_id}"
    print(f"\n{'='*70}")
    print(f"GET {url}")
    print(f"  params: {params}")
    resp = requests.get(url, params=params, timeout=30, verify=VERIFY_SSL)
    resp.raise_for_status()
    return resp.json()


def print_json_structure(obj, prefix="", depth=0, max_depth=4):
    """Recursively print JSON structure (keys and types)."""
    if depth > max_depth:
        print(f"{prefix}... (max depth)")
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict):
                print(f"{prefix}{k}: {{dict, {len(v)} keys}}")
                print_json_structure(v, prefix + "  ", depth + 1, max_depth)
            elif isinstance(v, list):
                print(f"{prefix}{k}: [list, {len(v)} items]")
                if v:
                    print_json_structure(v[0], prefix + "  [0].", depth + 1, max_depth)
            else:
                val_str = str(v)[:60]
                print(f"{prefix}{k}: {type(v).__name__} = {val_str}")
    elif isinstance(obj, list):
        if obj:
            print_json_structure(obj[0], prefix + "[0].", depth + 1, max_depth)


# ===================================================================
# Test 1: 即時觀測 O-A0003-001
# ===================================================================
def test_realtime():
    print("\n" + "=" * 70)
    print("TEST 1: 即時觀測 O-A0003-001")
    print("=" * 70)

    data = fetch_dataset("O-A0003-001")

    print("\n--- JSON 頂層結構 ---")
    print_json_structure(data, max_depth=2)

    records = data.get("records", {})
    stations = records.get("Station", records.get("station", []))
    print(f"\n共回傳 {len(stations)} 個測站")

    # 顯示第一個測站的完整結構
    if stations:
        print("\n--- 第一個測站完整結構 ---")
        print_json_structure(stations[0], max_depth=5)

        # 列出所有測站 ID
        api_station_ids = set()
        for s in stations:
            sid = s.get("StationId", s.get("stationId", ""))
            api_station_ids.add(sid)

        # 驗證 STATION_COUNTY_MAP
        print("\n--- 測站 ID 驗證 ---")
        our_ids = set(STATION_COUNTY_MAP.keys())
        found = our_ids & api_station_ids
        missing = our_ids - api_station_ids
        print(f"STATION_COUNTY_MAP 中有 {len(our_ids)} 個測站")
        print(f"API 回傳中找到: {len(found)} 個")
        if missing:
            print(f"API 中找不到的測站 ID: {missing}")
            print("  *** 這些測站可能已退役或 ID 變更 ***")
        else:
            print("所有測站 ID 都在 API 回應中找到！")

        # 顯示 weather elements
        print("\n--- 天氣欄位示例（前3個測站）---")
        for s in stations[:3]:
            sid = s.get("StationId", "?")
            name = s.get("StationName", "?")
            we = s.get("WeatherElement", s)
            print(f"\n  測站 {sid} ({name}):")
            print(f"    WeatherElement keys: {list(we.keys()) if isinstance(we, dict) else 'N/A'}")

    return api_station_ids


# ===================================================================
# Test 2: 歷史逐日資料 C-B0024-002
# ===================================================================
def test_historical():
    print("\n" + "=" * 70)
    print("TEST 2: 歷史逐日資料 C-B0024-002")
    print("=" * 70)

    # 嘗試不同的日期參數名稱
    test_date = (date.today() - timedelta(days=7)).isoformat()
    test_date2 = (date.today() - timedelta(days=14)).isoformat()

    # 嘗試 1: dataDate 參數
    print(f"\n--- 嘗試 dataDate={test_date} ---")
    try:
        data = fetch_dataset("C-B0024-002", {"dataDate": test_date})
        print("\n--- JSON 頂層結構 ---")
        print_json_structure(data, max_depth=2)

        records = data.get("records", {})
        # 嘗試各種可能的 key
        for key in ["Station", "station", "data", "Data", "location", "locations"]:
            if key in records:
                items = records[key]
                print(f"\nrecords.{key}: {type(items).__name__}, ", end="")
                if isinstance(items, list):
                    print(f"{len(items)} items")
                    if items:
                        print(f"\n--- records.{key}[0] 結構 ---")
                        print_json_structure(items[0], max_depth=5)
                elif isinstance(items, dict):
                    print(f"{len(items)} keys")
                    print_json_structure(items, max_depth=5)
                break
        else:
            print(f"\nrecords keys: {list(records.keys())}")
            print_json_structure(records, max_depth=3)

    except requests.HTTPError as e:
        print(f"HTTP Error: {e}")
        print("C-B0024-002 可能需要不同的參數格式")

    # 嘗試 2: 驗證不同日期回傳不同結果
    print(f"\n--- 嘗試第二個日期 dataDate={test_date2} ---")
    try:
        data2 = fetch_dataset("C-B0024-002", {"dataDate": test_date2})
        records2 = data2.get("records", {})
        for key in ["Station", "station", "data", "Data", "location", "locations"]:
            if key in records2:
                items2 = records2[key]
                if isinstance(items2, list):
                    print(f"第二個日期回傳 {len(items2)} 筆 records.{key}")
                break

    except requests.HTTPError as e:
        print(f"HTTP Error: {e}")

    # 嘗試 3: 用 StationId 篩選
    print(f"\n--- 嘗試加入 StationId 篩選 (466920=臺北) ---")
    try:
        data3 = fetch_dataset("C-B0024-002", {
            "dataDate": test_date,
            "StationId": "466920",
        })
        records3 = data3.get("records", {})
        print(f"records keys: {list(records3.keys())}")
        print_json_structure(records3, max_depth=4)
    except requests.HTTPError as e:
        print(f"HTTP Error: {e}")


# ===================================================================
# Test 3: 嘗試其他可能的歷史 dataset
# ===================================================================
def test_alternative_datasets():
    print("\n" + "=" * 70)
    print("TEST 3: 嘗試替代歷史 dataset")
    print("=" * 70)

    test_date = (date.today() - timedelta(days=7)).isoformat()

    # C-B0024-001: 也是地面測站的氣候資料
    alternatives = [
        ("C-B0024-001", "地面氣候資料(日)"),
        ("C-B0025-001", "地面氣候資料(月)"),
    ]

    for ds_id, desc in alternatives:
        print(f"\n--- {ds_id}: {desc} ---")
        try:
            data = fetch_dataset(ds_id, {"dataDate": test_date})
            records = data.get("records", {})
            print(f"records keys: {list(records.keys())}")
            for key in records:
                val = records[key]
                if isinstance(val, list):
                    print(f"  {key}: list[{len(val)}]")
                    if val:
                        print_json_structure(val[0], prefix="    ", max_depth=4)
                        break
                elif isinstance(val, dict):
                    print(f"  {key}: dict[{len(val)} keys]")
        except requests.HTTPError as e:
            print(f"  HTTP Error: {e}")
        except Exception as e:
            print(f"  Error: {e}")


# ===================================================================
# Main
# ===================================================================
if __name__ == "__main__":
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    print(f"CWA API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    print(f"Base URL: {BASE_URL}")

    realtime_ids = test_realtime()
    test_historical()
    test_alternative_datasets()

    print("\n" + "=" * 70)
    print("測試完成！")
    print("=" * 70)
    print("""
下一步：
1. 檢查 C-B0024-002 的 JSON 結構，確認天氣欄位路徑
2. 確認 dataDate 參數是否正確
3. 更新 weather_collector.py 的 _fetch_observations() 和 _extract_weather_elements()
""")
