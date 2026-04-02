"""整合五種蔬菜交易資料並加入縣市欄位。

讀取 csv_export/ 下的 5 個交易 CSV，透過市場代碼映射縣市，
產出：
  1. csv_export/integrated/all_vegetables_trading.csv  (全部合併)
  2. csv_export/integrated/by_county/<縣市>.csv         (按縣市分檔)
"""

import json
import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_EXPORT = os.path.join(BASE_DIR, "csv_export")
SEED_DIR = os.path.join(BASE_DIR, "backend", "app", "data", "seed")
OUTPUT_DIR = os.path.join(CSV_EXPORT, "integrated")
BY_COUNTY_DIR = os.path.join(OUTPUT_DIR, "by_county")

TRADING_FILES = [
    "bok_choy_交易資料.csv",
    "cabbage_交易資料.csv",
    "cauliflower_交易資料.csv",
    "green_onion_交易資料.csv",
    "lettuce_交易資料.csv",
]


def build_market_county_map() -> dict:
    """建立 市場代碼 -> 縣市名稱 對照表。"""
    with open(os.path.join(SEED_DIR, "markets.json"), encoding="utf-8") as f:
        markets = json.load(f)
    with open(os.path.join(SEED_DIR, "counties.json"), encoding="utf-8") as f:
        counties = json.load(f)

    code_to_name = {c["county_code"]: c["county_name_zh"] for c in counties}

    mapping = {}
    for m in markets:
        county_name = code_to_name.get(m["county_code"], "未知")
        mapping[m["market_code"]] = county_name

    return mapping


def main():
    market_county = build_market_county_map()

    frames = []
    for fname in TRADING_FILES:
        path = os.path.join(CSV_EXPORT, fname)
        df = pd.read_csv(path, dtype={"市場代碼": str})
        frames.append(df)
        print(f"  讀取 {fname}: {len(df):,} 筆")

    all_df = pd.concat(frames, ignore_index=True)
    print(f"\n合併後總筆數: {len(all_df):,}")

    # 市場代碼為空 → 標記「未知」
    all_df["市場代碼"] = all_df["市場代碼"].fillna("").astype(str).str.strip()
    all_df["縣市"] = all_df["市場代碼"].map(market_county).fillna("未知")

    unknown_count = (all_df["縣市"] == "未知").sum()
    print(f"市場代碼為空或無法映射 → 標記「未知」: {unknown_count:,} 筆")

    # 縣市分佈
    print("\n--- 各縣市筆數 ---")
    county_counts = all_df["縣市"].value_counts().sort_values(ascending=False)
    for county, count in county_counts.items():
        print(f"  {county}: {count:,}")

    # 輸出
    os.makedirs(BY_COUNTY_DIR, exist_ok=True)

    # 1) 全部合併
    cols = ["交易日期", "縣市", "品名", "市場名稱", "市場代碼", "上價", "中價", "下價", "平均價", "交易量(公斤)"]
    all_df = all_df.sort_values(["縣市", "交易日期", "品名"]).reset_index(drop=True)
    out_all = os.path.join(OUTPUT_DIR, "all_vegetables_trading.csv")
    all_df[cols].to_csv(out_all, index=False, encoding="utf-8-sig")
    print(f"\n已輸出: {out_all}")

    # 2) 按縣市分檔
    for county, group in all_df.groupby("縣市"):
        safe_name = county.replace(" ", "_")
        out_path = os.path.join(BY_COUNTY_DIR, f"{safe_name}.csv")
        group[cols].to_csv(out_path, index=False, encoding="utf-8-sig")

    print(f"已輸出按縣市分檔: {BY_COUNTY_DIR}/ ({len(county_counts)} 個檔案)")


if __name__ == "__main__":
    main()
