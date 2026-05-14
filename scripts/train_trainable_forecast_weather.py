from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "AFA-other" / "model_ready" / "trainable_forecast_weather"
OUT_DIR = ROOT / "AFA-other" / "model_ready" / "trainable_forecast_weather_results"

CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"]
HORIZONS = [1, 5, 7, 14]
MODEL_NAMES = ["ridge", "random_forest", "xgboost", "lightgbm"]


def load_feature_cols(crop: str, horizon: int) -> list[str]:
    path = DATA_DIR / crop / f"{crop}_h{horizon}_features.txt"
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_data(crop: str, horizon: int) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    train = pd.read_csv(DATA_DIR / crop / f"{crop}_h{horizon}_train.csv", parse_dates=["ds", "target_date"])
    test = pd.read_csv(DATA_DIR / crop / f"{crop}_h{horizon}_test.csv", parse_dates=["ds", "target_date"])
    features = load_feature_cols(crop, horizon)
    return train, test, features


def build_model(name: str):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=10.0))
    if name == "random_forest":
        return RandomForestRegressor(
            n_estimators=300,
            max_depth=14,
            min_samples_leaf=3,
            random_state=42,
            n_jobs=-1,
        )
    if name == "xgboost":
        return XGBRegressor(
            n_estimators=700,
            max_depth=4,
            learning_rate=0.03,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=42,
            n_jobs=-1,
        )
    if name == "lightgbm":
        return LGBMRegressor(
            n_estimators=700,
            learning_rate=0.03,
            num_leaves=31,
            subsample=0.85,
            colsample_bytree=0.85,
            random_state=42,
            n_jobs=-1,
            verbose=-1,
        )
    raise ValueError(f"Unknown model: {name}")


def regression_metrics(crop: str, horizon: int, model: str, y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    mask = np.isfinite(y_true) & np.isfinite(y_pred) & (y_true != 0)
    y_true = y_true[mask]
    y_pred = y_pred[mask]
    return {
        "crop": crop,
        "horizon": horizon,
        "model": model,
        "n_test": len(y_true),
        "MAE": mean_absolute_error(y_true, y_pred),
        "RMSE": mean_squared_error(y_true, y_pred) ** 0.5,
        "MAPE_percent": np.mean(np.abs((y_true - y_pred) / y_true)) * 100,
        "R2": r2_score(y_true, y_pred),
    }


def classification_metrics(crop: str, horizon: int, model: str, task: str, y_true, y_pred) -> dict:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "crop": crop,
        "horizon": horizon,
        "model": model,
        "task": task,
        "support_positive": int(y_true.sum()),
        "support_total": int(len(y_true)),
        "accuracy": accuracy_score(y_true, y_pred),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1_score": f1_score(y_true, y_pred, zero_division=0),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn),
        "tp": int(tp),
    }


def pred_to_classes(test: pd.DataFrame, pred: np.ndarray, horizon: int) -> dict[str, np.ndarray]:
    current = test["current_price"].to_numpy(dtype=float)
    change = (pred - current) / current
    return {
        f"target_up_h{horizon}": (change >= 0).astype(int),
        f"target_rise_ge_5pct_h{horizon}": (change >= 0.05).astype(int),
        f"target_rise_ge_10pct_h{horizon}": (change >= 0.10).astype(int),
    }


def write_report(reg: pd.DataFrame, cls: pd.DataFrame) -> None:
    best_reg = reg.sort_values(["crop", "horizon", "RMSE"]).groupby(["crop", "horizon"], as_index=False).first()
    best_cls = cls.sort_values(
        ["crop", "horizon", "task", "f1_score", "recall"],
        ascending=[True, True, True, False, False],
    ).groupby(["crop", "horizon", "task"], as_index=False).first()

    lines = [
        "# Trainable Forecast Weather Training Report",
        "",
        "Data source: `AFA-other/model_ready/trainable_forecast_weather`.",
        "",
        "Each model predicts future price using information available at `ds` only.",
        "",
        "## Best Price Prediction Models",
        "",
        "| crop | horizon | best model | MAE | RMSE | MAPE (%) | R2 |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best_reg.iterrows():
        lines.append(
            f"| {row['crop']} | {int(row['horizon'])} | {row['model']} | "
            f"{row['MAE']:.4f} | {row['RMSE']:.4f} | {row['MAPE_percent']:.4f} | {row['R2']:.4f} |"
        )

    lines += [
        "",
        "## Best Classification Models by F1",
        "",
        "| crop | horizon | task | best model | accuracy | precision | recall | f1_score | positives |",
        "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best_cls.iterrows():
        lines.append(
            f"| {row['crop']} | {int(row['horizon'])} | {row['task']} | {row['model']} | "
            f"{row['accuracy']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1_score']:.4f} | {int(row['support_positive'])}/{int(row['support_total'])} |"
        )

    lines += [
        "",
        "## Output Files",
        "",
        "- `regression_metrics.csv`: MAE/RMSE/MAPE/R2 for all models.",
        "- `classification_metrics.csv`: Accuracy/Precision/Recall/F1 for all warning targets.",
        "- `<crop>_h<horizon>_predictions.csv`: date-level actual and predicted prices.",
    ]
    (OUT_DIR / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    reg_rows = []
    cls_rows = []

    for crop in CROPS:
        for horizon in HORIZONS:
            train, test, features = load_data(crop, horizon)
            target = f"target_h{horizon}"
            pred_df = test[["ds", "target_date", "current_price", target]].copy()
            pred_df = pred_df.rename(columns={target: "actual_target"})

            print(f"Training {crop} h{horizon}...")
            for model_name in MODEL_NAMES:
                model = build_model(model_name)
                model.fit(train[features], train[target])
                pred = np.clip(model.predict(test[features]), 0, None)
                pred_df[model_name] = pred
                reg_rows.append(regression_metrics(crop, horizon, model_name, test[target], pred))

                pred_classes = pred_to_classes(test, pred, horizon)
                for task_col, cls_pred in pred_classes.items():
                    cls_rows.append(
                        classification_metrics(
                            crop,
                            horizon,
                            model_name,
                            task_col,
                            test[task_col].to_numpy(),
                            cls_pred,
                        )
                    )

            pred_df.to_csv(OUT_DIR / f"{crop}_h{horizon}_predictions.csv", index=False, encoding="utf-8-sig")

    reg = pd.DataFrame(reg_rows).sort_values(["crop", "horizon", "RMSE"])
    cls = pd.DataFrame(cls_rows).sort_values(["crop", "horizon", "task", "f1_score"], ascending=[True, True, True, False])
    reg.to_csv(OUT_DIR / "regression_metrics.csv", index=False, encoding="utf-8-sig")
    cls.to_csv(OUT_DIR / "classification_metrics.csv", index=False, encoding="utf-8-sig")
    write_report(reg, cls)
    print(f"Done. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
