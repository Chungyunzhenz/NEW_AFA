"""在整合交易資料上加入 3 個預測目標欄位。

讀取 csv_export/integrated/all_vegetables_trading.csv，
按 (交易日期, 縣市, 蔬菜類別) 聚合後計算：
  - target_1d:  1 個交易日後的平均價
  - target_5d:  未來 5 個交易日平均價的均值
  - target_20d: 未來 20 個交易日平均價的均值

輸出:
  csv_export/integrated/all_vegetables_daily_with_targets.csv
  csv_export/integrated/by_county_with_targets/<縣市>.csv
"""

import os
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV = os.path.join(BASE_DIR, "csv_export", "integrated", "all_vegetables_trading.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "csv_export", "integrated")
BY_COUNTY_DIR = os.path.join(OUTPUT_DIR, "by_county_with_targets")

# 品名 → 蔬菜類別 映射
CROP_KEYWORDS = {
    "甘藍": "甘藍",
    "花椰菜": "花椰菜",
    "青蔥": "青蔥",
}


def classify_crop(name: str) -> str:
    for keyword, category in CROP_KEYWORDS.items():
        if keyword in name:
            return category
    return "其他"


def forward_rolling_mean(s: pd.Series, window: int) -> pd.Series:
    """計算未來 N 個交易日的平均值（不含當日）。"""
    return s[::-1].rolling(window=window, min_periods=1).mean()[::-1].shift(-1)


def main():
    print("讀取整合資料...")
    df = pd.read_csv(INPUT_CSV, dtype={"市場代碼": str})
    print(f"  原始筆數: {len(df):,}")

    # 分類蔬菜
    df["蔬菜類別"] = df["品名"].apply(classify_crop)

    # 按 (交易日期, 縣市, 蔬菜類別) 聚合
    print("聚合為每日每縣市每蔬菜...")
    agg = df.groupby(["交易日期", "縣市", "蔬菜類別"]).agg(
        上價=("上價", "max"),
        下價=("下價", "min"),
        交易量=("交易量(公斤)", "sum"),
        _price_x_vol=("平均價", lambda x: (x * df.loc[x.index, "交易量(公斤)"]).sum()),
    ).reset_index()

    # 加權平均價 = sum(price * volume) / sum(volume)
    agg["平均價"] = np.where(agg["交易量"] > 0, agg["_price_x_vol"] / agg["交易量"], 0)
    agg["中價"] = (agg["上價"] + agg["下價"]) / 2
    agg.drop(columns=["_price_x_vol"], inplace=True)

    # 排除「未知」縣市和非目標蔬菜
    agg = agg[agg["縣市"] != "未知"]
    agg = agg[agg["蔬菜類別"] != "其他"]

    # 排序
    agg["交易日期"] = pd.to_datetime(agg["交易日期"])
    agg = agg.sort_values(["縣市", "蔬菜類別", "交易日期"]).reset_index(drop=True)

    print(f"  聚合後筆數: {len(agg):,}")

    # 計算 3 個 TARGET（按縣市+蔬菜類別分組）
    print("計算 target_1d / target_5d / target_20d...")
    targets = []
    for (county, crop), group in agg.groupby(["縣市", "蔬菜類別"]):
        g = group.copy()
        price = g["平均價"]
        g["target_1d"] = price.shift(-1)
        g["target_5d"] = forward_rolling_mean(price, 5)
        g["target_20d"] = forward_rolling_mean(price, 20)
        targets.append(g)

    result = pd.concat(targets, ignore_index=True)
    result = result.sort_values(["縣市", "蔬菜類別", "交易日期"]).reset_index(drop=True)

    # 整理欄位順序
    cols = ["交易日期", "縣市", "蔬菜類別", "上價", "中價", "下價", "平均價",
            "交易量", "target_1d", "target_5d", "target_20d"]
    result = result[cols]
    result["平均價"] = result["平均價"].round(2)
    result["中價"] = result["中價"].round(2)
    result["target_1d"] = result["target_1d"].round(2)
    result["target_5d"] = result["target_5d"].round(2)
    result["target_20d"] = result["target_20d"].round(2)

    # 輸出：全部
    os.makedirs(BY_COUNTY_DIR, exist_ok=True)
    out_all = os.path.join(OUTPUT_DIR, "all_vegetables_daily_with_targets.csv")
    result.to_csv(out_all, index=False, encoding="utf-8-sig")
    print(f"\n已輸出: {out_all}  ({len(result):,} 筆)")

    # 輸出：按縣市
    for county, group in result.groupby("縣市"):
        out_path = os.path.join(BY_COUNTY_DIR, f"{county}.csv")
        group.to_csv(out_path, index=False, encoding="utf-8-sig")

    county_count = result["縣市"].nunique()
    print(f"已輸出按縣市分檔: {BY_COUNTY_DIR}/ ({county_count} 個檔案)")

    # 摘要
    print("\n--- 各縣市 × 蔬菜 筆數 ---")
    summary = result.groupby(["縣市", "蔬菜類別"]).size().unstack(fill_value=0)
    print(summary.to_string())

    # target NaN 統計
    total = len(result)
    for col in ["target_1d", "target_5d", "target_20d"]:
        nan_pct = result[col].isna().sum() / total * 100
        print(f"  {col} NaN: {nan_pct:.2f}%")


if __name__ == "__main__":
    main()
