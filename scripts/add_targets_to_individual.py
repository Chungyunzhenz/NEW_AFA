"""為五種蔬菜的個別交易資料 CSV 補齊 target_1d, target_5d, target_20d。

按 (品名, 市場代碼) 分組，依交易日期排序後計算：
  - target_1d:  下一個交易日的平均價
  - target_5d:  未來 5 個交易日平均價的均值（不含當日）
  - target_20d: 未來 20 個交易日平均價的均值（不含當日）
"""

import os
import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = os.path.join(BASE_DIR, "csv_export")

FILES = [
    "bok_choy_交易資料.csv",
    "cabbage_交易資料.csv",
    "cauliflower_交易資料.csv",
    "green_onion_交易資料.csv",
    "lettuce_交易資料.csv",
]


def forward_rolling_mean(s: pd.Series, window: int) -> pd.Series:
    """計算未來 N 個交易日的平均值（不含當日）。"""
    return s[::-1].rolling(window=window, min_periods=1).mean()[::-1].shift(-1)


def add_targets(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df["市場代碼"] = df["市場代碼"].fillna("unknown").astype(str)
    df = df.sort_values(["品名", "市場代碼", "交易日期"]).reset_index(drop=True)

    targets = []
    for (_crop, _market), group in df.groupby(["品名", "市場代碼"]):
        g = group.copy()
        price = g["平均價"]
        g["target_1d"] = price.shift(-1)
        g["target_5d"] = forward_rolling_mean(price, 5)
        g["target_20d"] = forward_rolling_mean(price, 20)
        targets.append(g)

    result = pd.concat(targets, ignore_index=True)
    result = result.sort_values(["品名", "市場代碼", "交易日期"]).reset_index(drop=True)
    result["target_1d"] = result["target_1d"].round(2)
    result["target_5d"] = result["target_5d"].round(2)
    result["target_20d"] = result["target_20d"].round(2)
    return result


def main():
    for fname in FILES:
        path = os.path.join(CSV_DIR, fname)
        print(f"\n處理: {fname}")
        df = pd.read_csv(path, dtype={"市場代碼": str})
        print(f"  原始筆數: {len(df):,}")

        result = add_targets(df)

        out_path = path.replace(".csv", "_with_targets.csv")
        result.to_csv(out_path, index=False, encoding="utf-8-sig")
        print(f"  已輸出: {out_path}")
        print(f"  已寫入 {len(result):,} 筆（含 target 欄位）")

        for col in ["target_1d", "target_5d", "target_20d"]:
            nan_pct = result[col].isna().sum() / len(result) * 100
            print(f"  {col} NaN: {nan_pct:.2f}%")


if __name__ == "__main__":
    main()
