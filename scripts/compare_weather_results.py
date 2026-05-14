from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BASE_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_python_results"
WEATHER_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_weather_results"
OUT_DIR = ROOT / "AFA-other" / "model_ready" / "forecast_weather_results"


def main() -> None:
    base = pd.read_csv(BASE_DIR / "metrics.csv")
    weather = pd.read_csv(WEATHER_DIR / "metrics.csv")
    keys = ["crop", "model"]
    compare = base.merge(weather, on=keys, suffixes=("_base", "_weather"))
    for metric in ["MAE", "RMSE", "MAPE_percent", "R2"]:
        compare[f"{metric}_delta"] = compare[f"{metric}_weather"] - compare[f"{metric}_base"]
    compare["RMSE_improvement_percent"] = (
        (compare["RMSE_base"] - compare["RMSE_weather"]) / compare["RMSE_base"] * 100
    )
    compare["MAPE_improvement_percent"] = (
        (compare["MAPE_percent_base"] - compare["MAPE_percent_weather"]) / compare["MAPE_percent_base"] * 100
    )
    compare = compare.sort_values(["crop", "RMSE_weather"])
    compare.to_csv(OUT_DIR / "weather_vs_base_metrics.csv", index=False, encoding="utf-8-sig")

    best_base = base.sort_values(["crop", "RMSE"]).groupby("crop", as_index=False).first()
    best_weather = weather.sort_values(["crop", "RMSE"]).groupby("crop", as_index=False).first()
    best = best_base.merge(best_weather, on="crop", suffixes=("_base", "_weather"))
    best["RMSE_improvement_percent"] = (best["RMSE_base"] - best["RMSE_weather"]) / best["RMSE_base"] * 100
    best["MAPE_improvement_percent"] = (
        (best["MAPE_percent_base"] - best["MAPE_percent_weather"]) / best["MAPE_percent_base"] * 100
    )
    best.to_csv(OUT_DIR / "best_model_weather_vs_base.csv", index=False, encoding="utf-8-sig")

    lines = [
        "# Weather feature comparison report",
        "",
        "This report compares the original forecast models with models retrained after adding weather features.",
        "",
        "Positive improvement means the weather-enhanced model reduced error.",
        "",
        "## Best model comparison",
        "",
        "| crop | base best | base RMSE | base MAPE | weather best | weather RMSE | weather MAPE | RMSE improvement | MAPE improvement |",
        "| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for _, row in best.iterrows():
        lines.append(
            f"| {row['crop']} | {row['model_base']} | {row['RMSE_base']:.4f} | "
            f"{row['MAPE_percent_base']:.4f}% | {row['model_weather']} | "
            f"{row['RMSE_weather']:.4f} | {row['MAPE_percent_weather']:.4f}% | "
            f"{row['RMSE_improvement_percent']:.2f}% | {row['MAPE_improvement_percent']:.2f}% |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Weather features include national daily temperature, rainfall, humidity, lagged weather values, rolling rainfall, and heavy-rain flags.",
        "- If improvement is negative, the weather-enhanced model performed worse under the current feature set and hyperparameters.",
        "- Weather may still help after crop-specific regional weighting or tuned lag windows.",
    ]
    (OUT_DIR / "WEATHER_COMPARISON_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Done. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
