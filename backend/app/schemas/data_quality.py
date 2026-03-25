from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class DateRange(BaseModel):
    start: Optional[str] = None
    end: Optional[str] = None


class YearRange(BaseModel):
    start: Optional[int] = None
    end: Optional[int] = None


class TradingSummary(BaseModel):
    total_records: int
    date_range: DateRange
    null_crop_id_pct: float
    null_market_id_pct: float
    coverage_months: int
    expected_months: int
    health: str


class WeatherSummary(BaseModel):
    total_records: int
    counties_with_data: int
    counties_total: int
    missing_counties: List[str]
    null_field_pcts: Dict[str, float]
    health: str


class ProductionSummary(BaseModel):
    total_records: int
    year_range: YearRange
    coverage_years: int
    expected_years: int
    health: str


class CropQuality(BaseModel):
    crop_key: str
    display_name_zh: Optional[str] = None
    trading_months_covered: int
    trading_months_expected: int
    trading_coverage_pct: float
    production_years_covered: int
    gaps: List[str]
    health: str


class DataQualityOverview(BaseModel):
    overall_health: str
    trading: TradingSummary
    weather: WeatherSummary
    production: ProductionSummary
    per_crop: List[CropQuality]
