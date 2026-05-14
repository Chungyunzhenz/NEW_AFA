"""驗證 regression_ready 輸出"""
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent / "AFA-other" / "regression_ready"
CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"]

print(f"{'crop':<12} {'train':>8} {'test':>8} {'ratio':>10} {'cols':>5} {'y_NA':>5} {'time_split':>11}")
print("-" * 70)

all_ok = True
for c in CROPS:
    tr = pd.read_csv(OUT / f"{c}_train.csv")
    te = pd.read_csv(OUT / f"{c}_test.csv")
    n = len(tr) + len(te)
    ratio = f"{len(tr)/n*100:.1f}/{len(te)/n*100:.1f}"
    y_na = int(tr["target_5d"].isna().sum() + te["target_5d"].isna().sum())
    train_max = pd.to_datetime(tr["交易日期"]).max()
    test_min = pd.to_datetime(te["交易日期"]).min()
    leak_ok = train_max < test_min
    cols_ok = tr.shape[1] == te.shape[1]
    if y_na > 0 or not leak_ok or not cols_ok:
        all_ok = False
    print(f"{c:<12} {len(tr):>8} {len(te):>8} {ratio:>10} {tr.shape[1]:>5} {y_na:>5} {'OK' if leak_ok else 'LEAK!':>11}")

# 啞變數覆蓋率：每列的 market_* 加總應為 0 或 1
# 0 表示是參照組，1 表示是其中一個非參照市場
# 不應該有 >1 的情況
print("\n=== Dummy coverage check ===")
for c in CROPS:
    tr = pd.read_csv(OUT / f"{c}_train.csv")
    market_cols = [col for col in tr.columns if col.startswith("market_")]
    variety_cols = [col for col in tr.columns if col.startswith("variety_")]
    market_sum = tr[market_cols].sum(axis=1)
    variety_sum = tr[variety_cols].sum(axis=1)
    n_ref_market = (market_sum == 0).sum()
    n_other_market = (market_sum == 1).sum()
    n_invalid_market = (market_sum > 1).sum()
    n_ref_variety = (variety_sum == 0).sum()
    n_other_variety = (variety_sum == 1).sum()
    n_invalid_variety = (variety_sum > 1).sum()
    print(f"  {c}: market[ref={n_ref_market}, other={n_other_market}, invalid={n_invalid_market}], "
          f"variety[ref={n_ref_variety}, other={n_other_variety}, invalid={n_invalid_variety}]")

print(f"\n{'ALL OK' if all_ok else 'FAILED'}")
