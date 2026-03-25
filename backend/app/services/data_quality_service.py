"""Data quality assessment service.

Computes coverage, gap detection, and health indicators for trading,
weather, and production data.  Used by the ``/api/v1/data-quality``
endpoints and can also be called from CLI scripts.
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from ..models import Crop, TradingData, WeatherData, ProductionData
from ..models.region import County

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Health thresholds
# ---------------------------------------------------------------------------
_GREEN_THRESHOLD = 0.90  # >= 90 % coverage
_YELLOW_THRESHOLD = 0.70  # >= 70 % coverage


def _health(ratio: float) -> str:
    if ratio >= _GREEN_THRESHOLD:
        return "green"
    if ratio >= _YELLOW_THRESHOLD:
        return "yellow"
    return "red"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class DataQualityService:
    """Stateless service — pass a DB session to each method."""

    # ---- Overview ----------------------------------------------------------

    def overview(self, db: Session) -> Dict[str, Any]:
        """Return a top-level health summary across all data sources."""
        trading = self._trading_summary(db)
        weather = self._weather_summary(db)
        production = self._production_summary(db)
        per_crop = self._per_crop_summary(db)

        healths = [trading["health"], weather["health"], production["health"]]
        if "red" in healths:
            overall = "red"
        elif "yellow" in healths:
            overall = "yellow"
        else:
            overall = "green"

        return {
            "overall_health": overall,
            "trading": trading,
            "weather": weather,
            "production": production,
            "per_crop": per_crop,
        }

    # ---- Per-crop ----------------------------------------------------------

    def crop_detail(self, db: Session, crop_key: str) -> Optional[Dict[str, Any]]:
        """Return detailed quality info for a single crop."""
        crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
        if not crop:
            return None
        return self._crop_quality(crop, db)

    # ---- Internal helpers --------------------------------------------------

    def _trading_summary(self, db: Session) -> Dict[str, Any]:
        total = db.query(func.count(TradingData.id)).scalar() or 0
        date_min = db.query(func.min(TradingData.trade_date)).scalar()
        date_max = db.query(func.max(TradingData.trade_date)).scalar()

        null_crop = (
            db.query(func.count(TradingData.id))
            .filter(TradingData.crop_id.is_(None))
            .scalar() or 0
        )
        null_market = (
            db.query(func.count(TradingData.id))
            .filter(TradingData.market_id.is_(None))
            .scalar() or 0
        )

        null_crop_pct = round(null_crop / total * 100, 1) if total else 0
        null_market_pct = round(null_market / total * 100, 1) if total else 0

        # Coverage: count distinct year-months
        if date_min and date_max:
            expected_months = (
                (date_max.year - date_min.year) * 12
                + date_max.month - date_min.month + 1
            )
            actual_months_rows = (
                db.query(
                    func.strftime("%Y-%m", TradingData.trade_date)
                )
                .distinct()
                .all()
            )
            actual_months = len(actual_months_rows)
            coverage = actual_months / expected_months if expected_months else 1.0
        else:
            expected_months = 0
            actual_months = 0
            coverage = 0

        health = _health(coverage) if null_crop_pct < 15 else "yellow"

        return {
            "total_records": total,
            "date_range": {
                "start": str(date_min) if date_min else None,
                "end": str(date_max) if date_max else None,
            },
            "null_crop_id_pct": null_crop_pct,
            "null_market_id_pct": null_market_pct,
            "coverage_months": actual_months,
            "expected_months": expected_months,
            "health": health,
        }

    def _weather_summary(self, db: Session) -> Dict[str, Any]:
        total = db.query(func.count(WeatherData.id)).scalar() or 0
        counties_with_data = (
            db.query(func.count(distinct(WeatherData.county_id)))
            .filter(WeatherData.county_id.isnot(None))
            .scalar() or 0
        )
        counties_total = db.query(func.count(County.id)).scalar() or 0

        # Missing counties
        covered_ids = {
            r[0] for r in
            db.query(distinct(WeatherData.county_id))
            .filter(WeatherData.county_id.isnot(None))
            .all()
        }
        all_counties = db.query(County.id, County.county_name_zh).all()
        missing = [name for cid, name in all_counties if cid not in covered_ids]

        # Null field percentages
        null_pcts = {}
        for col_name, col in [
            ("temp_avg", WeatherData.temp_avg),
            ("rainfall_mm", WeatherData.rainfall_mm),
            ("humidity_pct", WeatherData.humidity_pct),
        ]:
            null_count = (
                db.query(func.count(WeatherData.id))
                .filter(col.is_(None))
                .scalar() or 0
            )
            null_pcts[col_name] = round(null_count / total * 100, 1) if total else 0

        coverage = counties_with_data / counties_total if counties_total else 0
        health = _health(coverage)

        return {
            "total_records": total,
            "counties_with_data": counties_with_data,
            "counties_total": counties_total,
            "missing_counties": missing,
            "null_field_pcts": null_pcts,
            "health": health,
        }

    def _production_summary(self, db: Session) -> Dict[str, Any]:
        total = db.query(func.count(ProductionData.id)).scalar() or 0

        year_min_row = db.query(func.min(ProductionData.year)).scalar()
        year_max_row = db.query(func.max(ProductionData.year)).scalar()

        year_min = year_min_row if year_min_row else None
        year_max = year_max_row if year_max_row else None

        if year_min and year_max:
            expected_years = year_max - year_min + 1
            actual_years = (
                db.query(func.count(distinct(ProductionData.year))).scalar() or 0
            )
            coverage = actual_years / expected_years if expected_years else 1.0
        else:
            expected_years = 0
            actual_years = 0
            coverage = 0

        return {
            "total_records": total,
            "year_range": {
                "start": year_min,
                "end": year_max,
            },
            "coverage_years": actual_years if year_min else 0,
            "expected_years": expected_years,
            "health": _health(coverage) if total > 0 else "red",
        }

    def _per_crop_summary(self, db: Session) -> List[Dict[str, Any]]:
        crops = db.query(Crop).filter(Crop.is_active == True).all()  # noqa: E712
        results = []
        for crop in crops:
            results.append(self._crop_quality(crop, db))
        return results

    def _crop_quality(self, crop: Crop, db: Session) -> Dict[str, Any]:
        # Trading months
        trading_months_rows = (
            db.query(func.strftime("%Y-%m", TradingData.trade_date))
            .filter(TradingData.crop_id == crop.id)
            .distinct()
            .all()
        )
        trading_months = len(trading_months_rows)

        # Trading date range
        t_min = (
            db.query(func.min(TradingData.trade_date))
            .filter(TradingData.crop_id == crop.id)
            .scalar()
        )
        t_max = (
            db.query(func.max(TradingData.trade_date))
            .filter(TradingData.crop_id == crop.id)
            .scalar()
        )
        if t_min and t_max:
            expected_trading = (
                (t_max.year - t_min.year) * 12 + t_max.month - t_min.month + 1
            )
        else:
            expected_trading = 0

        # Production years
        prod_years = (
            db.query(func.count(distinct(ProductionData.year)))
            .filter(ProductionData.crop_id == crop.id)
            .scalar() or 0
        )

        # Gaps detection (missing months in trading)
        gaps = []
        if trading_months_rows and expected_trading > 0:
            existing = {r[0] for r in trading_months_rows}
            if t_min and t_max:
                all_months = pd.date_range(
                    start=t_min.replace(day=1),
                    end=t_max.replace(day=1),
                    freq="MS",
                )
                for m in all_months:
                    key = m.strftime("%Y-%m")
                    if key not in existing:
                        gaps.append(f"{key} 交易資料缺漏")

        trading_coverage = trading_months / expected_trading if expected_trading else 0

        return {
            "crop_key": crop.crop_key,
            "display_name_zh": crop.display_name_zh,
            "trading_months_covered": trading_months,
            "trading_months_expected": expected_trading,
            "trading_coverage_pct": round(trading_coverage * 100, 1),
            "production_years_covered": prod_years,
            "gaps": gaps[:20],  # Limit to first 20
            "health": _health(trading_coverage),
        }
