from __future__ import annotations

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from prophet import Prophet

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "AFA-other" / "model_ready" / "forecast"


def load_crop(data_dir: Path, crop: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(data_dir / f"{crop}_daily_train.csv", parse_dates=["ds"])
    test = pd.read_csv(data_dir / f"{crop}_daily_test.csv", parse_dates=["ds"])
    return train, test


def train_prophet(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.05,
    )
    prophet_regressors = [
        c
        for c in [
            "ln_volume_total",
            "is_observed",
            "transaction_count",
            "weather_temp_avg",
            "weather_rainfall_mean",
            "weather_rainfall_max",
            "weather_humidity_avg",
            "weather_heavy_rain_7d_flag",
        ]
        if c in train.columns
    ]
    for regressor in prophet_regressors:
        model.add_regressor(regressor)

    prophet_train = train[["ds", "y"] + prophet_regressors].copy()
    model.fit(prophet_train)
    future = test[["ds"] + prophet_regressors].copy()
    forecast = model.predict(future)
    return np.clip(forecast["yhat"].to_numpy(), 0, None)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crop", required=True)
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--out-file", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train, test = load_crop(args.data_dir, args.crop)
    pred = train_prophet(train, test)
    args.out_file.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "crop": args.crop,
            "ds": test["ds"],
            "prophet": pred,
        }
    ).to_csv(args.out_file, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
