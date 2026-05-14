from __future__ import annotations

import warnings
import argparse
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "AFA-other" / "model_ready" / "forecast"
OUT_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_python_results"

CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"]

FEATURE_COLS = [
    "ln_volume_total",
    "transaction_count",
    "item_count",
    "market_count",
    "is_observed",
    "year",
    "month",
    "day_of_week",
    "day_of_year",
    "month_sin",
    "month_cos",
    "price_lag_1",
    "price_lag_3",
    "price_lag_7",
    "price_lag_14",
    "price_roll_mean_7",
    "price_roll_std_7",
    "price_roll_mean_14",
    "volume_lag_1",
    "volume_roll_mean_7",
]

WEATHER_PREFIXES = ("weather_",)


def load_crop(crop: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_csv(DATA_DIR / f"{crop}_daily_train.csv", parse_dates=["ds"])
    test = pd.read_csv(DATA_DIR / f"{crop}_daily_test.csv", parse_dates=["ds"])
    return train, test


def get_feature_cols(train: pd.DataFrame) -> list[str]:
    cols = [c for c in FEATURE_COLS if c in train.columns]
    weather_cols = [
        c for c in train.columns
        if c.startswith(WEATHER_PREFIXES)
        and pd.api.types.is_numeric_dtype(train[c])
        and train[c].notna().any()
    ]
    return cols + [c for c in weather_cols if c not in cols]


def metric_row(crop: str, model: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred) & (y_true != 0)
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    return {
        "crop": crop,
        "model": model,
        "n_test": len(y_true),
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": mean_squared_error(y_true, y_pred) ** 0.5,
        "MAPE_percent": np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
        "R2": r2_score(y_true, y_pred),
    }


def train_baselines(train: pd.DataFrame, test: pd.DataFrame) -> dict[str, np.ndarray]:
    fallback = float(train["y"].iloc[-1])
    return {
        "naive_lag1": test["price_lag_1"].fillna(fallback).to_numpy(),
        "seasonal_naive_lag7": test["price_lag_7"].fillna(fallback).to_numpy(),
        "moving_average_7": test["price_roll_mean_7"].fillna(fallback).to_numpy(),
        "moving_average_14": test["price_roll_mean_14"].fillna(fallback).to_numpy(),
    }


def train_ridge(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    feature_cols = get_feature_cols(train)
    model = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    model.fit(train[feature_cols], train["y"])
    return np.clip(model.predict(test[feature_cols]), 0, None)


def train_random_forest(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    feature_cols = get_feature_cols(train)
    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=14,
        min_samples_leaf=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[feature_cols], train["y"])
    return np.clip(model.predict(test[feature_cols]), 0, None)


def train_xgboost(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    from xgboost import XGBRegressor

    feature_cols = get_feature_cols(train)
    model = XGBRegressor(
        n_estimators=600,
        max_depth=4,
        learning_rate=0.03,
        subsample=0.85,
        colsample_bytree=0.85,
        objective="reg:squarederror",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(train[feature_cols], train["y"])
    return np.clip(model.predict(test[feature_cols]), 0, None)


def train_lightgbm(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    from lightgbm import LGBMRegressor

    feature_cols = get_feature_cols(train)
    model = LGBMRegressor(
        n_estimators=600,
        learning_rate=0.03,
        num_leaves=31,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    model.fit(train[feature_cols], train["y"])
    return np.clip(model.predict(test[feature_cols]), 0, None)


def train_prophet(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    from prophet import Prophet

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        seasonality_mode="additive",
        changepoint_prior_scale=0.05,
    )
    prophet_regressors = [
        c for c in [
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


def train_sarima(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    from statsmodels.tsa.statespace.sarimax import SARIMAX

    # Fixed weekly seasonal specification. This is much faster and more stable
    # than auto_arima for all five daily crop series.
    model = SARIMAX(
        train["y"].astype(float),
        order=(1, 1, 1),
        seasonal_order=(1, 0, 1, 7),
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    fitted = model.fit(disp=False, maxiter=120)
    pred = fitted.forecast(steps=len(test))
    return np.clip(np.asarray(pred), 0, None)


MODEL_FNS: dict[str, Callable[[pd.DataFrame, pd.DataFrame], np.ndarray]] = {
    "ridge": train_ridge,
    "random_forest": train_random_forest,
    "xgboost": train_xgboost,
    "lightgbm": train_lightgbm,
    "prophet": train_prophet,
    "sarima_weekly": train_sarima,
}


def write_report(metrics: pd.DataFrame, failures: list[dict]) -> None:
    best = metrics.sort_values(["crop", "RMSE"]).groupby("crop", as_index=False).first()
    lines = [
        "# Python forecast model report",
        "",
        "Data source: `AFA-other/model_ready/forecast`.",
        "",
        "The report compares simple baselines, classical time-series models, and machine-learning regressors.",
        "ML models use lag, rolling, calendar, and volume features prepared from past values.",
        "",
        "## Best model by crop",
        "",
        "| crop | best model | MAE | RMSE | MAPE (%) | R2 |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best.iterrows():
        lines.append(
            f"| {row['crop']} | {row['model']} | {row['MAE']:.4f} | "
            f"{row['RMSE']:.4f} | {row['MAPE_percent']:.4f} | {row['R2']:.4f} |"
        )

    lines += ["", "## Full metrics", ""]
    for crop in CROPS:
        sub = metrics[metrics["crop"] == crop].sort_values("RMSE")
        lines += [
            f"### {crop}",
            "",
            "| model | n_test | MAE | RMSE | MAPE (%) | R2 |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for _, row in sub.iterrows():
            lines.append(
                f"| {row['model']} | {int(row['n_test'])} | {row['MAE']:.4f} | "
                f"{row['RMSE']:.4f} | {row['MAPE_percent']:.4f} | {row['R2']:.4f} |"
            )
        lines.append("")

    if failures:
        lines += ["## Model failures", ""]
        for failure in failures:
            lines.append(f"- {failure['crop']} / {failure['model']}: {failure['error']}")
        lines.append("")

    lines += [
        "## Output files",
        "",
        "- `metrics.csv`: all metrics.",
        "- `<crop>_predictions.csv`: actual and predicted values by date.",
    ]
    (OUT_DIR / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=DATA_DIR)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    return parser.parse_args()


def main() -> None:
    global DATA_DIR, OUT_DIR
    args = parse_args()
    DATA_DIR = args.data_dir
    OUT_DIR = args.out_dir
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_rows = []
    failures = []

    for crop in CROPS:
        print(f"Training {crop}...")
        train, test = load_crop(crop)
        predictions = {"actual": test["y"].to_numpy()}
        model_preds = train_baselines(train, test)

        for model_name, fn in MODEL_FNS.items():
            try:
                print(f"  {model_name}")
                model_preds[model_name] = fn(train, test)
            except Exception as exc:  # keep other models running
                failures.append({"crop": crop, "model": model_name, "error": repr(exc)})
                print(f"  {model_name} failed: {exc}")

        for model_name, pred in model_preds.items():
            predictions[model_name] = pred
            metric_rows.append(metric_row(crop, model_name, test["y"].to_numpy(), pred))

        pred_df = pd.DataFrame({"crop": crop, "ds": test["ds"], **predictions})
        pred_df.to_csv(OUT_DIR / f"{crop}_predictions.csv", index=False, encoding="utf-8-sig")

    metrics = pd.DataFrame(metric_rows)
    metrics = metrics.sort_values(["crop", "RMSE"]).reset_index(drop=True)
    metrics.to_csv(OUT_DIR / "metrics.csv", index=False, encoding="utf-8-sig")
    write_report(metrics, failures)
    print(f"Done. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
