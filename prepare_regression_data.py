"""
整理 5 個作物的交易資料為回歸用格式（模仿老師示範的 ERC 樣式）。

輸入: AFA-other/<crop>_交易資料_with_targets.csv (5 檔)
輸出: AFA-other/regression_ready/
  - <crop>_train.csv / <crop>_test.csv (70/30 時序切)
  - <crop>_codebook.txt (啞變數對照)
  - README.txt
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).parent
SRC = ROOT / "AFA-other"
OUT = SRC / "regression_ready"

CROPS = {
    "cabbage":     ("cabbage_交易資料_with_targets.csv",     "甘藍"),
    "bok_choy":    ("bok_choy_交易資料_with_targets.csv",    "小白菜"),
    "cauliflower": ("cauliflower_交易資料_with_targets.csv", "花椰菜"),
    "green_onion": ("green_onion_交易資料_with_targets.csv", "青蔥"),
    "lettuce":     ("lettuce_交易資料_with_targets.csv",     "萵苣"),
}


def write_codebook(name, zh_name, variety_ref, variety_map, market_ref, market_map,
                   n_train, n_test, cut_date, date_min, date_max):
    lines = [
        f"=== {name} ({zh_name}) 回歸資料 codebook ===",
        "",
        "【資料概況】",
        f"  原始資料日期範圍: {date_min} ~ {date_max}",
        f"  訓練集 (前 70%): {n_train} 筆,  日期 < {cut_date}",
        f"  測試集 (後 30%): {n_test} 筆,  日期 >= {cut_date}",
        "",
        "【y (依變數)】",
        "  target_5d : 未來 5 日平均價格 (元/公斤)",
        "",
        "【連續變數 X】",
        "  上價, 中價, 下價, 平均價 : 當日價格 (元/公斤)",
        "  交易量(公斤)              : 當日交易量原值",
        "  ln_volume                 : log(交易量+1)，對數轉換版",
        "",
        f"【品名啞變數 (variety dummies)，共 {len(variety_map)} 個 (n-1)】",
        f"  參照組 (reference): {variety_ref}",
    ]
    for col, val in variety_map.items():
        lines.append(f"  {col} = 1 if 品名 == \"{val}\", else 0")
    lines += [
        "",
        f"【市場啞變數 (market dummies)，共 {len(market_map)} 個 (n-1)】",
        f"  參照組 (reference): {market_ref}",
    ]
    for col, val in market_map.items():
        lines.append(f"  {col} = 1 if 市場名稱 == \"{val}\", else 0")
    lines += [
        "",
        "【參考欄】",
        "  交易日期 : YYYY-MM-DD，僅供對照，不要放進回歸",
        "",
    ]
    (OUT / f"{name}_codebook.txt").write_text("\n".join(lines), encoding="utf-8")


def prepare(name, fname, zh_name):
    df = pd.read_csv(SRC / fname, low_memory=False)
    date_min = df["交易日期"].min()
    date_max = df["交易日期"].max()
    df["交易日期"] = pd.to_datetime(df["交易日期"])
    df = df.sort_values("交易日期").reset_index(drop=True)
    df = df.drop(columns=["target_1d", "target_20d"])
    df = df.dropna(subset=["target_5d"]).reset_index(drop=True)
    df["ln_volume"] = np.log1p(df["交易量(公斤)"].astype(float))

    # 品名啞變數 (n-1, 第一個為參照組)
    # 用 sorted() 確保結果可重現
    varieties = sorted(df["品名"].dropna().unique().tolist())
    variety_ref, *variety_others = varieties
    variety_map = {}
    for i, v in enumerate(variety_others, 1):
        col = f"variety_{i}"
        df[col] = (df["品名"] == v).astype(int)
        variety_map[col] = v

    # 市場啞變數 — 改用 市場代碼 (無缺值) 為主，市場名稱 只作為 codebook 顯示用
    # 注意: 當 市場名稱 為 NaN 時，市場代碼 會被原始資料填為字串 "unknown"
    # 我們把它視為獨立群組「(市場資訊不全)」，避免被誤分到參照組
    def display_name(code, names_for_code):
        if str(code).lower() == "unknown":
            return "(市場資訊不全)"
        if len(names_for_code) > 0:
            return names_for_code.mode().iloc[0]
        return f"代碼{code}"

    code_to_name = {}
    for code, sub in df.groupby("市場代碼"):
        code_to_name[code] = display_name(code, sub["市場名稱"].dropna())

    # 排序: 數值代碼優先排序，'unknown' 放最後
    numeric_codes = sorted([c for c in df["市場代碼"].unique() if str(c).lower() != "unknown"])
    other_codes = [c for c in df["市場代碼"].unique() if str(c).lower() == "unknown"]
    market_codes = numeric_codes + other_codes
    market_ref_code, *market_other_codes = market_codes
    market_ref = f"{code_to_name[market_ref_code]} (代碼 {market_ref_code})"
    market_map = {}
    for i, code in enumerate(market_other_codes, 1):
        col = f"market_{i}"
        df[col] = (df["市場代碼"] == code).astype(int)
        market_map[col] = f"{code_to_name[code]} (代碼 {code})"

    # 丟文字欄
    df = df.drop(columns=["品名", "市場名稱", "市場代碼"])

    # 重排
    cols = (
        ["交易日期", "上價", "中價", "下價", "平均價", "交易量(公斤)", "ln_volume"]
        + list(variety_map.keys())
        + list(market_map.keys())
        + ["target_5d"]
    )
    df = df[cols]

    # 70/30 時序切（依 unique 日期，避免同日切兩半）
    udates = df["交易日期"].drop_duplicates().sort_values().reset_index(drop=True)
    cut = udates.iloc[int(len(udates) * 0.7)]
    train = df[df["交易日期"] < cut]
    test = df[df["交易日期"] >= cut]

    # 輸出（utf-8-sig 讓 Excel 開中文不亂碼）
    train.to_csv(OUT / f"{name}_train.csv", index=False, encoding="utf-8-sig")
    test.to_csv(OUT / f"{name}_test.csv", index=False, encoding="utf-8-sig")

    write_codebook(
        name, zh_name,
        variety_ref, variety_map,
        market_ref, market_map,
        len(train), len(test),
        cut.date(),
        date_min, date_max,
    )

    return {
        "name": name,
        "zh": zh_name,
        "rows": len(df),
        "train": len(train),
        "test": len(test),
        "cut": cut.date(),
        "varieties": len(varieties),
        "markets": len(market_codes),
        "n_dummies": len(variety_map) + len(market_map),
        "n_cols": len(cols),
    }


def write_readme(stats):
    lines = [
        "=== 回歸資料說明 (regression_ready) ===",
        "",
        "資料來源: AFA-other/<crop>_交易資料_with_targets.csv",
        "整理腳本: prepare_regression_data.py",
        "",
        "【格式】",
        "  - 純數值矩陣，類別變數已預先編碼成 0/1 啞變數",
        "  - 連續變數: 上價/中價/下價/平均價/交易量(公斤)/ln_volume",
        "  - 啞變數: variety_* (品名), market_* (市場)",
        "  - y: target_5d (最後一欄，未來 5 日均價)",
        "  - 交易日期: 僅供對照，不要放進回歸",
        "",
        "【切分】",
        "  - 70/30 依日期時序切（前 70% 訓練、後 30% 測試）",
        "  - 用 unique 日期切以避免同日資料被切兩半",
        "",
        "【各作物統計】",
    ]
    for s in stats:
        lines.append(
            f"  {s['name']:<12} ({s['zh']}): "
            f"train={s['train']:>6}, test={s['test']:>6}, "
            f"cut={s['cut']}, "
            f"variety_dummy={s['varieties']-1}, market_dummy={s['markets']-1}, "
            f"總欄位={s['n_cols']}"
        )
    lines += [
        "",
        "【使用注意】",
        "  1. 詳細的啞變數對照請看各作物的 <crop>_codebook.txt",
        "  2. 上價/中價/下價/平均價之間相關性很高，做 OLS 時建議：",
        "     - 只留 平均價 一個，或",
        "     - 改用 Ridge / Lasso，或",
        "     - 跑 VIF 檢驗篩選變數",
        "  3. 同時放入 交易量(公斤) 與 ln_volume 會有完全共線性，",
        "     請挑一個（建議用 ln_volume）",
        "  4. 啞變數有「參照組」(被省略的那個類別)，係數要相對於它解讀",
        "  5. CSV 為 UTF-8 BOM 編碼，Excel 直接開不會亂碼",
        "",
    ]
    (OUT / "README.txt").write_text("\n".join(lines), encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"Output dir: {OUT}\n")
    stats = []
    for name, (fname, zh) in CROPS.items():
        print(f"Processing {name} ({zh}) ...")
        s = prepare(name, fname, zh)
        stats.append(s)
        print(
            f"  rows={s['rows']}, train={s['train']}, test={s['test']}, "
            f"cut={s['cut']}, varieties={s['varieties']}, markets={s['markets']}"
        )
    write_readme(stats)
    print(f"\nDone. {len(stats)} crops, output in: {OUT}")


if __name__ == "__main__":
    main()
