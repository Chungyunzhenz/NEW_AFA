from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_python_results"
CLASS_DIR = RESULT_DIR / "classification_metrics"
PLOT_DIR = RESULT_DIR / "plots"

CROPS = ["cabbage", "bok_choy", "cauliflower", "green_onion", "lettuce"]
MODEL_LABELS = {
    "naive_lag1": "Naive lag1",
    "seasonal_naive_lag7": "Seasonal lag7",
    "moving_average_7": "MA 7",
    "moving_average_14": "MA 14",
    "ridge": "Ridge",
    "random_forest": "Random Forest",
    "xgboost": "XGBoost",
    "lightgbm": "LightGBM",
    "prophet": "Prophet",
    "sarima_weekly": "SARIMA",
}


def setup_style() -> None:
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["savefig.dpi"] = 180
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["axes.spines.right"] = False


def savefig(name: str) -> None:
    plt.tight_layout()
    plt.savefig(PLOT_DIR / name, bbox_inches="tight")
    plt.close()


def plot_best_model_summary(metrics: pd.DataFrame) -> None:
    best = metrics.sort_values(["crop", "RMSE"]).groupby("crop", as_index=False).first()

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    axes[0].bar(best["crop"], best["MAPE_percent"], color="#2563eb")
    axes[0].set_title("Best model MAPE by crop")
    axes[0].set_ylabel("MAPE (%)")
    axes[0].tick_params(axis="x", rotation=25)

    axes[1].bar(best["crop"], best["RMSE"], color="#16a34a")
    axes[1].set_title("Best model RMSE by crop")
    axes[1].set_ylabel("RMSE")
    axes[1].tick_params(axis="x", rotation=25)

    savefig("best_model_summary.png")


def plot_metrics_by_crop(metrics: pd.DataFrame) -> None:
    for crop in CROPS:
        sub = metrics[metrics["crop"] == crop].sort_values("RMSE")
        labels = [MODEL_LABELS.get(m, m) for m in sub["model"]]

        fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
        axes[0].bar(labels, sub["RMSE"], color="#2563eb")
        axes[0].set_title(f"{crop}: RMSE by model")
        axes[0].set_ylabel("RMSE")
        axes[0].tick_params(axis="x", rotation=45)

        axes[1].bar(labels, sub["MAPE_percent"], color="#f97316")
        axes[1].set_title(f"{crop}: MAPE by model")
        axes[1].set_ylabel("MAPE (%)")
        axes[1].tick_params(axis="x", rotation=45)

        savefig(f"{crop}_model_metrics.png")


def plot_predictions(metrics: pd.DataFrame) -> None:
    for crop in CROPS:
        pred = pd.read_csv(RESULT_DIR / f"{crop}_predictions.csv", parse_dates=["ds"])
        best_model = metrics[metrics["crop"] == crop].sort_values("RMSE").iloc[0]["model"]
        recent = pred.tail(365).copy()

        plt.figure(figsize=(13, 5))
        plt.plot(recent["ds"], recent["actual"], label="Actual", color="#111827", linewidth=1.8)
        plt.plot(recent["ds"], recent[best_model], label=f"Predicted ({MODEL_LABELS.get(best_model, best_model)})", color="#2563eb", linewidth=1.5)
        plt.title(f"{crop}: actual vs predicted price, latest 365 days")
        plt.ylabel("Weighted average price")
        plt.xlabel("Date")
        plt.legend()
        savefig(f"{crop}_actual_vs_predicted.png")

        full = pred.copy()
        full["error"] = full[best_model] - full["actual"]
        plt.figure(figsize=(13, 4.5))
        plt.plot(full["ds"], full["error"], color="#dc2626", linewidth=1)
        plt.axhline(0, color="#111827", linewidth=0.8)
        plt.title(f"{crop}: prediction error over test period ({MODEL_LABELS.get(best_model, best_model)})")
        plt.ylabel("Predicted - actual")
        plt.xlabel("Date")
        savefig(f"{crop}_prediction_error.png")

        plt.figure(figsize=(5.5, 5.5))
        plt.scatter(pred["actual"], pred[best_model], s=8, alpha=0.45, color="#2563eb")
        mn = min(pred["actual"].min(), pred[best_model].min())
        mx = max(pred["actual"].max(), pred[best_model].max())
        plt.plot([mn, mx], [mn, mx], color="#111827", linewidth=1)
        plt.title(f"{crop}: actual vs predicted scatter")
        plt.xlabel("Actual")
        plt.ylabel("Predicted")
        savefig(f"{crop}_actual_predicted_scatter.png")


def plot_all_crops_together(metrics: pd.DataFrame) -> None:
    plt.figure(figsize=(14, 6))
    for crop in CROPS:
        pred = pd.read_csv(RESULT_DIR / f"{crop}_predictions.csv", parse_dates=["ds"])
        recent = pred.tail(365)
        plt.plot(recent["ds"], recent["actual"], linewidth=1.5, label=crop)
    plt.title("All crops: actual weighted average price, latest 365 days")
    plt.ylabel("Weighted average price")
    plt.xlabel("Date")
    plt.legend(ncol=3)
    savefig("all_crops_actual_lines.png")

    plt.figure(figsize=(14, 6))
    for crop in CROPS:
        pred = pd.read_csv(RESULT_DIR / f"{crop}_predictions.csv", parse_dates=["ds"])
        best_model = metrics[metrics["crop"] == crop].sort_values("RMSE").iloc[0]["model"]
        recent = pred.tail(365)
        plt.plot(recent["ds"], recent["actual"], linewidth=1.4, label=f"{crop} actual")
        plt.plot(recent["ds"], recent[best_model], linewidth=1.2, linestyle="--", label=f"{crop} predicted")
    plt.title("All crops: actual vs best-model predicted price, latest 365 days")
    plt.ylabel("Weighted average price")
    plt.xlabel("Date")
    plt.legend(ncol=2, fontsize=8)
    savefig("all_crops_actual_vs_predicted_lines.png")


def plot_classification() -> None:
    metrics_path = CLASS_DIR / "classification_metrics.csv"
    if not metrics_path.exists():
        return
    cls = pd.read_csv(metrics_path)

    for task in ["direction_up", "rise_ge_5pct", "rise_ge_10pct"]:
        best = (
            cls[cls["task"] == task]
            .sort_values(["crop", "f1_score", "recall"], ascending=[True, False, False])
            .groupby("crop", as_index=False)
            .first()
        )

        x = range(len(best))
        width = 0.36
        plt.figure(figsize=(11, 4.8))
        plt.bar([i - width / 2 for i in x], best["f1_score"], width=width, label="F1", color="#2563eb")
        plt.bar([i + width / 2 for i in x], best["recall"], width=width, label="Recall", color="#f97316")
        plt.xticks(list(x), [f"{r.crop}\n{MODEL_LABELS.get(r.model, r.model)}" for r in best.itertuples()], rotation=0)
        plt.ylim(0, 1)
        plt.title(f"Best classification performance: {task}")
        plt.ylabel("Score")
        plt.legend()
        savefig(f"classification_{task}_best_f1_recall.png")


def write_index() -> None:
    lines = [
        "# Forecast Result Plots",
        "",
        "Generated by `scripts/plot_forecast_results.py`.",
        "",
        "## Summary",
        "",
        "- `best_model_summary.png`: best model MAPE/RMSE by crop.",
        "- `<crop>_model_metrics.png`: model RMSE/MAPE comparison for each crop.",
        "- `<crop>_actual_vs_predicted.png`: latest 365 days actual vs predicted line chart.",
        "- `all_crops_actual_lines.png`: all crops' actual prices in one line chart.",
        "- `all_crops_actual_vs_predicted_lines.png`: all crops' actual and predicted prices in one line chart.",
        "- `<crop>_prediction_error.png`: prediction error across the full test period.",
        "- `<crop>_actual_predicted_scatter.png`: actual vs predicted scatter plot.",
        "- `classification_*_best_f1_recall.png`: warning-classification F1 and Recall by task.",
    ]
    (PLOT_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)
    setup_style()
    metrics = pd.read_csv(RESULT_DIR / "metrics.csv")
    plot_best_model_summary(metrics)
    plot_metrics_by_crop(metrics)
    plot_predictions(metrics)
    plot_all_crops_together(metrics)
    plot_classification()
    write_index()
    print(f"Done. Output: {PLOT_DIR}")


if __name__ == "__main__":
    main()
