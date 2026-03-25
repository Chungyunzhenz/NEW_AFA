"""Generate human-readable forecast summaries in Traditional Chinese.

Compares current predictions against recent historical data to produce
plain-language insights such as trend direction, year-over-year change,
confidence level, and seasonal context.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

from ..models import Crop, TradingData
from ..models.prediction import Prediction
from ..models.typhoon import TyphoonEvent

logger = logging.getLogger(__name__)

# Month ranges for seasonal context
_SEASON_MAP = {
    1: "冬季", 2: "冬季", 3: "春季", 4: "春季",
    5: "春季", 6: "夏季", 7: "夏季", 8: "夏季",
    9: "秋季", 10: "秋季", 11: "冬季", 12: "冬季",
}


def generate_summary(
    db: Session,
    crop_key: str,
    horizon: str = "1m",
) -> Dict[str, Any]:
    """Build a forecast summary dict for the given crop and horizon.

    Returns a dict with keys:
    - ``trend`` : "up" | "down" | "flat"
    - ``trend_pct`` : float (percentage change vs recent average)
    - ``yoy_pct`` : float | None (vs same month last year)
    - ``confidence`` : "high" | "medium" | "low"
    - ``season`` : str (current season name)
    - ``typhoon_risk`` : bool (any typhoons historically in next 3 months?)
    - ``summary_text`` : str (full Chinese summary paragraph)
    """
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        return {"summary_text": "找不到此作物資料。"}

    # --- Latest ensemble prediction ---
    latest_pred = (
        db.query(Prediction)
        .filter(
            Prediction.crop_id == crop.id,
            Prediction.target_metric == "price_avg",
            Prediction.model_name == "ensemble",
            Prediction.horizon_label == horizon,
            Prediction.region_type == "national",
        )
        .order_by(desc(Prediction.forecast_date))
        .first()
    )

    if not latest_pred:
        return {"summary_text": "尚無預測資料。"}

    forecast_value = latest_pred.forecast_value
    lower = latest_pred.lower_bound or forecast_value
    upper = latest_pred.upper_bound or forecast_value

    # --- Recent average price: use last month's monthly average ---
    # Instead of averaging all raw records over 90 days (which double-counts
    # markets and skews the result), we find the most recent month with data
    # and use its monthly average price.
    from sqlalchemy import extract as sa_extract

    last_month_avg_row = (
        db.query(func.avg(TradingData.price_avg).label("avg_price"))
        .filter(TradingData.crop_id == crop.id)
        .group_by(
            sa_extract("year", TradingData.trade_date),
            sa_extract("month", TradingData.trade_date),
        )
        .order_by(
            sa_extract("year", TradingData.trade_date).desc(),
            sa_extract("month", TradingData.trade_date).desc(),
        )
        .first()
    )
    recent_avg = float(last_month_avg_row.avg_price) if last_month_avg_row and last_month_avg_row.avg_price else None

    # --- Year-over-year ---
    forecast_month = latest_pred.forecast_date.month
    forecast_year = latest_pred.forecast_date.year
    last_year_avg_row = (
        db.query(func.avg(TradingData.price_avg))
        .filter(
            TradingData.crop_id == crop.id,
            func.strftime("%Y", TradingData.trade_date) == str(forecast_year - 1),
            func.strftime("%m", TradingData.trade_date) == f"{forecast_month:02d}",
        )
        .scalar()
    )
    last_year_avg = float(last_year_avg_row) if last_year_avg_row else None

    # --- Compute metrics ---
    trend = "flat"
    trend_pct = 0.0
    if recent_avg and recent_avg > 0:
        trend_pct = round((forecast_value - recent_avg) / recent_avg * 100, 1)
        if trend_pct > 3:
            trend = "up"
        elif trend_pct < -3:
            trend = "down"

    yoy_pct = None
    if last_year_avg and last_year_avg > 0:
        yoy_pct = round((forecast_value - last_year_avg) / last_year_avg * 100, 1)

    # Confidence from CI width
    ci_width = upper - lower
    ci_ratio = ci_width / forecast_value if forecast_value > 0 else 1.0
    if ci_ratio < 0.10:
        confidence = "high"
    elif ci_ratio < 0.25:
        confidence = "medium"
    else:
        confidence = "low"

    # Season
    now_month = datetime.utcnow().month
    season = _SEASON_MAP.get(now_month, "")

    # Typhoon risk: any historical typhoons in next 3 months?
    upcoming_months = [(now_month + i - 1) % 12 + 1 for i in range(1, 4)]
    typhoon_risk = False
    try:
        for m in upcoming_months:
            count = (
                db.query(func.count(TyphoonEvent.id))
                .filter(
                    func.cast(func.strftime("%m", TyphoonEvent.warning_start), type_=None)
                    .in_([f"{m:02d}"])
                )
                .scalar() or 0
            )
            if count > 0:
                typhoon_risk = True
                break
    except Exception:
        # Typhoon table might not exist
        pass

    # --- Build summary text ---
    crop_name = crop.display_name_zh or crop_key
    parts = []

    horizon_text = {"1m": "1 個月", "3m": "3 個月", "6m": "6 個月"}.get(horizon, horizon)

    if trend == "up":
        parts.append(f"預計未來 {horizon_text} {crop_name}平均價格將上漲約 {abs(trend_pct)}%")
    elif trend == "down":
        parts.append(f"預計未來 {horizon_text} {crop_name}平均價格將下跌約 {abs(trend_pct)}%")
    else:
        parts.append(f"預計未來 {horizon_text} {crop_name}平均價格維持穩定")

    if yoy_pct is not None:
        if yoy_pct > 0:
            parts.append(f"與去年同期相比高 {abs(yoy_pct)}%")
        elif yoy_pct < 0:
            parts.append(f"與去年同期相比低 {abs(yoy_pct)}%")
        else:
            parts.append("與去年同期持平")

    conf_text = {"high": "高", "medium": "中等", "low": "低"}.get(confidence, "")
    parts.append(f"預測信心度：{conf_text}")

    parts.append(f"目前處於{season}")

    if typhoon_risk:
        parts.append("未來數月有颱風風險，可能影響供應與價格")

    summary_text = "。".join(parts) + "。"

    return {
        "trend": trend,
        "trend_pct": trend_pct,
        "yoy_pct": yoy_pct,
        "confidence": confidence,
        "season": season,
        "typhoon_risk": typhoon_risk,
        "forecast_value": round(forecast_value, 2),
        "summary_text": summary_text,
    }
