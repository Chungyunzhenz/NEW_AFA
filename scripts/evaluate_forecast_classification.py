from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score, precision_score, recall_score

ROOT = Path(__file__).resolve().parents[1]
PRED_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_python_results"
OUT_DIR = PRED_DIR / "classification_metrics"

CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"]
TASKS = {
    "direction_up": 0.0,
    "rise_ge_5pct": 0.05,
    "rise_ge_10pct": 0.10,
}


def load_predictions(crop: str) -> pd.DataFrame:
    df = pd.read_csv(PRED_DIR / f"{crop}_predictions.csv", parse_dates=["ds"])
    df = df.sort_values("ds").reset_index(drop=True)
    df["actual_prev"] = df["actual"].shift(1)
    return df.dropna(subset=["actual_prev"]).reset_index(drop=True)


def classify(current: pd.Series, previous: pd.Series, threshold: float) -> np.ndarray:
    change_rate = (current.astype(float) - previous.astype(float)) / previous.astype(float)
    return (change_rate >= threshold).astype(int).to_numpy()


def metric_row(crop: str, task: str, model: str, y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    return {
        "crop": crop,
        "task": task,
        "model": model,
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


def write_report(metrics: pd.DataFrame) -> None:
    lines = [
        "# Forecast classification metrics",
        "",
        "These metrics reinterpret price forecasts as warning/classification tasks.",
        "",
        "Tasks:",
        "",
        "- `direction_up`: predicted price change >= 0%.",
        "- `rise_ge_5pct`: predicted price change >= 5%.",
        "- `rise_ge_10pct`: predicted price change >= 10%.",
        "",
        "The previous actual price is used as the reference price for both actual and predicted change rates.",
        "",
        "## Best F1 by crop and task",
        "",
        "| crop | task | best model | accuracy | precision | recall | f1_score | positives |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    best = metrics.sort_values(["crop", "task", "f1_score", "recall"], ascending=[True, True, False, False])
    best = best.groupby(["crop", "task"], as_index=False).first()
    for _, row in best.iterrows():
        lines.append(
            f"| {row['crop']} | {row['task']} | {row['model']} | "
            f"{row['accuracy']:.4f} | {row['precision']:.4f} | {row['recall']:.4f} | "
            f"{row['f1_score']:.4f} | {int(row['support_positive'])}/{int(row['support_total'])} |"
        )

    lines += ["", "## Full Metrics", ""]
    for task in TASKS:
        lines += [
            f"### {task}",
            "",
            "| crop | model | accuracy | precision | recall | f1_score | tp | fp | fn | tn |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        sub = metrics[metrics["task"] == task].sort_values(["crop", "f1_score"], ascending=[True, False])
        for _, row in sub.iterrows():
            lines.append(
                f"| {row['crop']} | {row['model']} | {row['accuracy']:.4f} | "
                f"{row['precision']:.4f} | {row['recall']:.4f} | {row['f1_score']:.4f} | "
                f"{int(row['tp'])} | {int(row['fp'])} | {int(row['fn'])} | {int(row['tn'])} |"
            )
        lines.append("")

    lines += [
        "## Notes",
        "",
        "- Recall answers: among actual warning days, how many did the model catch?",
        "- Precision answers: among predicted warning days, how many were truly warning days?",
        "- F1 balances precision and recall.",
        "- For rare events such as >=10% price jumps, accuracy can look high even when recall is poor; use F1 and recall for warning quality.",
    ]
    (OUT_DIR / "CLASSIFICATION_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = []

    for crop in CROPS:
        df = load_predictions(crop)
        model_cols = [c for c in df.columns if c not in {"crop", "ds", "actual", "actual_prev"}]
        crop_rows = []
        for task, threshold in TASKS.items():
            y_true = classify(df["actual"], df["actual_prev"], threshold)
            for model in model_cols:
                y_pred = classify(df[model], df["actual_prev"], threshold)
                row = metric_row(crop, task, model, y_true, y_pred)
                rows.append(row)
                crop_rows.append(row)

        pd.DataFrame(crop_rows).to_csv(OUT_DIR / f"{crop}_classification_metrics.csv", index=False, encoding="utf-8-sig")

    metrics = pd.DataFrame(rows)
    metrics.to_csv(OUT_DIR / "classification_metrics.csv", index=False, encoding="utf-8-sig")
    write_report(metrics)
    print(f"Done. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
