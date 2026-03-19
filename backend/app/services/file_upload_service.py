"""File upload, parsing, validation, and import service.

Three-step flow:
1. Upload & parse: read CSV/Excel, detect encoding, return headers + samples + auto-mapping
2. Preview & validate: apply user mapping, validate each row, return preview
3. Confirm & import: write valid rows to the appropriate DB table
"""
from __future__ import annotations

import logging
import time
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session

from ..config import load_crop_configs
from ..models import County, Crop, Market, ProductionData, TradingData, WeatherData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Target schema definitions with aliases for auto-mapping
# ---------------------------------------------------------------------------
TARGET_SCHEMAS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "trading": {
        "trade_date": {
            "label": "交易日期",
            "required": True,
            "type": "date",
            "aliases": ["交易日期", "日期", "date", "trade_date", "TradeDate", "Date"],
        },
        "crop_name_raw": {
            "label": "作物名稱",
            "required": True,
            "type": "str",
            "aliases": ["作物名稱", "品名", "crop_name", "crop", "CropName", "作物"],
        },
        "market_code": {
            "label": "市場代號",
            "required": False,
            "type": "str",
            "aliases": ["市場代號", "市場", "market_code", "market", "MarketCode", "市場名稱"],
        },
        "price_high": {
            "label": "上價",
            "required": False,
            "type": "float",
            "aliases": ["上價", "price_high", "PriceHigh", "最高價"],
        },
        "price_mid": {
            "label": "中價",
            "required": False,
            "type": "float",
            "aliases": ["中價", "price_mid", "PriceMid", "中間價"],
        },
        "price_low": {
            "label": "下價",
            "required": False,
            "type": "float",
            "aliases": ["下價", "price_low", "PriceLow", "最低價"],
        },
        "price_avg": {
            "label": "平均價",
            "required": False,
            "type": "float",
            "aliases": ["平均價", "price_avg", "PriceAvg", "均價", "平均"],
        },
        "volume": {
            "label": "交易量",
            "required": False,
            "type": "float",
            "aliases": ["交易量", "volume", "Volume", "數量", "交易量(公斤)"],
        },
    },
    "production": {
        "year": {
            "label": "年份",
            "required": True,
            "type": "int",
            "aliases": ["年份", "年度", "year", "Year", "YEAR", "民國年"],
        },
        "month": {
            "label": "月份",
            "required": False,
            "type": "int",
            "aliases": ["月份", "month", "Month", "MONTH"],
        },
        "county_name": {
            "label": "縣市",
            "required": False,
            "type": "str",
            "aliases": [
                "縣市", "縣市別", "county", "County", "COUNTY",
                "地區", "區域", "縣市名稱", "county_name",
            ],
        },
        "crop_name": {
            "label": "作物名稱",
            "required": False,
            "type": "str",
            "aliases": ["作物", "作物名稱", "品名", "crop", "crop_name"],
        },
        "planted_area_ha": {
            "label": "種植面積(公頃)",
            "required": False,
            "type": "float",
            "aliases": [
                "種植面積", "種植面積(公頃)", "planted_area_ha",
                "planted_area", "PlantedArea", "種植面積（公頃）",
            ],
        },
        "harvest_area_ha": {
            "label": "收穫面積(公頃)",
            "required": False,
            "type": "float",
            "aliases": [
                "收穫面積", "收獲面積", "收穫面積(公頃)", "收獲面積(公頃)",
                "harvest_area_ha", "harvest_area", "HarvestArea",
                "收穫面積（公頃）", "收獲面積（公頃）",
            ],
        },
        "production_tonnes": {
            "label": "產量(公噸)",
            "required": True,
            "type": "float",
            "aliases": [
                "產量", "產量(公噸)", "production_tonnes",
                "production", "Production", "產量（公噸）",
            ],
        },
        "yield_per_ha": {
            "label": "每公頃產量",
            "required": False,
            "type": "float",
            "aliases": [
                "每公頃產量", "單位面積產量", "yield_per_ha",
                "yield", "Yield", "每公頃產量(公斤)", "每公頃產量（公斤）",
            ],
        },
    },
    "weather": {
        "observation_date": {
            "label": "觀測日期",
            "required": True,
            "type": "date",
            "aliases": ["觀測日期", "日期", "date", "observation_date", "Date"],
        },
        "county_name": {
            "label": "縣市",
            "required": False,
            "type": "str",
            "aliases": ["縣市", "站名", "county", "station", "county_name", "地區"],
        },
        "temp_avg": {
            "label": "平均溫度",
            "required": False,
            "type": "float",
            "aliases": ["平均溫度", "均溫", "temp_avg", "temperature", "氣溫"],
        },
        "temp_max": {
            "label": "最高溫度",
            "required": False,
            "type": "float",
            "aliases": ["最高溫度", "最高溫", "temp_max", "max_temp"],
        },
        "temp_min": {
            "label": "最低溫度",
            "required": False,
            "type": "float",
            "aliases": ["最低溫度", "最低溫", "temp_min", "min_temp"],
        },
        "rainfall_mm": {
            "label": "降雨量(mm)",
            "required": False,
            "type": "float",
            "aliases": ["降雨量", "降水量", "rainfall_mm", "rainfall", "雨量"],
        },
        "humidity_pct": {
            "label": "濕度(%)",
            "required": False,
            "type": "float",
            "aliases": ["濕度", "相對溼度", "humidity_pct", "humidity", "溼度"],
        },
    },
}

# ---------------------------------------------------------------------------
# Temporary upload storage (in-memory with TTL)
# ---------------------------------------------------------------------------
_upload_store: Dict[str, Dict[str, Any]] = {}
_UPLOAD_TTL_SECONDS = 30 * 60  # 30 minutes


def _cleanup_expired() -> None:
    """Remove expired upload entries."""
    now = time.time()
    expired = [
        uid for uid, entry in _upload_store.items()
        if now - entry["created_at"] > _UPLOAD_TTL_SECONDS
    ]
    for uid in expired:
        del _upload_store[uid]


# ---------------------------------------------------------------------------
# Helper: detect encoding
# ---------------------------------------------------------------------------
def _detect_encoding(file_bytes: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "big5", "cp950"):
        try:
            file_bytes.decode(enc)
            return enc
        except (UnicodeDecodeError, UnicodeError):
            continue
    return "utf-8"


# ---------------------------------------------------------------------------
# Helper: parse date (supports ROC and Western)
# ---------------------------------------------------------------------------
def _parse_date(value: Any) -> Optional[date]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None

    if isinstance(value, (datetime, date)):
        return value if isinstance(value, date) else value.date()

    s = str(value).strip().replace("/", ".").replace("-", ".")
    parts = s.split(".")

    # ROC date: YYY.MM.DD
    if len(parts) == 3:
        try:
            y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
            if y <= 200:  # ROC year
                y += 1911
            return date(y, m, d)
        except (ValueError, TypeError):
            pass

    # Try standard date formats
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt).date()
        except ValueError:
            continue

    return None


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s in ("", "-", "\u2026", "\u2500", "N/A", "n/a"):
        return None
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip().replace(",", "")
    if s in ("", "-", "\u2026", "\u2500", "N/A", "n/a"):
        return None
    try:
        return int(float(s))
    except (TypeError, ValueError):
        return None


def _normalize_year(raw: Any) -> Optional[int]:
    val = _safe_int(raw)
    if val is None or val <= 0:
        return None
    if val <= 200:
        return val + 1911
    return val


# ---------------------------------------------------------------------------
# Step 1: Upload & Parse
# ---------------------------------------------------------------------------
def parse_uploaded_file(
    file_bytes: bytes,
    filename: str,
    data_type: str,
) -> Dict[str, Any]:
    """Parse an uploaded CSV/Excel file and return headers + samples + suggested mapping."""
    _cleanup_expired()

    upload_id = str(uuid.uuid4())

    # Read into DataFrame
    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(pd.io.common.BytesIO(file_bytes), engine="openpyxl")
    else:
        encoding = _detect_encoding(file_bytes)
        from io import StringIO
        text = file_bytes.decode(encoding)
        df = pd.read_csv(StringIO(text))

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    headers = list(df.columns)
    row_count = len(df)

    # Sample rows (first 5)
    sample_df = df.head(5).where(df.head(5).notna(), None)
    sample_rows = sample_df.to_dict(orient="records")
    # Convert any non-serializable types
    for row in sample_rows:
        for k, v in row.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                row[k] = str(v)
            elif pd.isna(v) if isinstance(v, float) else False:
                row[k] = None

    # Auto-mapping suggestion
    schema = TARGET_SCHEMAS.get(data_type, {})
    suggested_mapping: Dict[str, Optional[str]] = {}

    for header in headers:
        matched_target = None
        header_lower = header.lower().strip()
        for target_field, field_info in schema.items():
            for alias in field_info["aliases"]:
                if alias.lower() == header_lower or alias == header:
                    matched_target = target_field
                    break
            if matched_target:
                break
        suggested_mapping[header] = matched_target

    # Build target_fields info for the frontend
    target_fields = {}
    for field_name, field_info in schema.items():
        target_fields[field_name] = {
            "label": field_info["label"],
            "required": field_info["required"],
            "type": field_info["type"],
        }

    # Store in memory
    _upload_store[upload_id] = {
        "df": df,
        "filename": filename,
        "data_type": data_type,
        "created_at": time.time(),
    }

    return {
        "upload_id": upload_id,
        "filename": filename,
        "row_count": row_count,
        "headers": headers,
        "sample_rows": sample_rows,
        "suggested_mapping": suggested_mapping,
        "target_fields": target_fields,
    }


# ---------------------------------------------------------------------------
# Step 2: Preview & Validate
# ---------------------------------------------------------------------------
def preview_import(
    upload_id: str,
    data_type: str,
    mapping: Dict[str, Optional[str]],
    db: Session,
) -> Dict[str, Any]:
    """Apply column mapping, validate each row, return preview."""
    entry = _upload_store.get(upload_id)
    if entry is None:
        raise ValueError(f"Upload {upload_id} not found or expired.")

    df = entry["df"]
    schema = TARGET_SCHEMAS.get(data_type, {})

    # Build reverse mapping: target_field -> source_column
    reverse_map: Dict[str, str] = {}
    for source_col, target_field in mapping.items():
        if target_field:
            reverse_map[target_field] = source_col

    # Store the validated mapping for later confirm step
    entry["mapping"] = mapping
    entry["reverse_map"] = reverse_map

    # Build lookups for validation
    county_map = {c.county_name_zh: c.id for c in db.query(County).all()}
    # Add 台/臺 variants
    county_map_extended = dict(county_map)
    for name, cid in county_map.items():
        if "\u81fa" in name:
            county_map_extended[name.replace("\u81fa", "\u53f0")] = cid
        if "\u53f0" in name:
            county_map_extended[name.replace("\u53f0", "\u81fa")] = cid

    market_map = {}
    try:
        market_map = {m.market_code: m.id for m in db.query(Market).all()}
    except Exception:
        pass

    crop_lookup = {}
    try:
        from ..services.data_collector import AMISDataCollector
        collector = AMISDataCollector()
        crop_lookup = collector._build_crop_lookup(db)
    except Exception:
        pass

    errors: List[Dict[str, Any]] = []
    valid_rows: List[Dict[str, Any]] = []
    duplicate_count = 0

    for idx, row in df.iterrows():
        row_num = idx + 2  # 1-based, accounting for header
        row_errors: List[str] = []
        parsed: Dict[str, Any] = {}

        # Parse each mapped field
        for target_field, field_info in schema.items():
            source_col = reverse_map.get(target_field)
            if source_col is None:
                if field_info["required"]:
                    row_errors.append(f"\u5fc5\u586b\u6b04\u4f4d '{field_info['label']}' \u672a\u6620\u5c04")
                continue

            raw_value = row.get(source_col)
            if pd.isna(raw_value) if not isinstance(raw_value, str) else False:
                raw_value = None

            field_type = field_info["type"]

            if field_type == "date":
                parsed_val = _parse_date(raw_value)
                if parsed_val is None and field_info["required"]:
                    row_errors.append(f"'{field_info['label']}' \u65e5\u671f\u683c\u5f0f\u7121\u6548: {raw_value}")
                parsed[target_field] = parsed_val
            elif field_type == "float":
                parsed_val = _safe_float(raw_value)
                if parsed_val is None and field_info["required"]:
                    row_errors.append(f"'{field_info['label']}' \u6578\u503c\u7121\u6548: {raw_value}")
                parsed[target_field] = parsed_val
            elif field_type == "int":
                if target_field == "year":
                    parsed_val = _normalize_year(raw_value)
                else:
                    parsed_val = _safe_int(raw_value)
                if parsed_val is None and field_info["required"]:
                    row_errors.append(f"'{field_info['label']}' \u6578\u503c\u7121\u6548: {raw_value}")
                parsed[target_field] = parsed_val
            else:  # str
                parsed[target_field] = str(raw_value).strip() if raw_value is not None else None
                if parsed[target_field] is None and field_info["required"]:
                    row_errors.append(f"'{field_info['label']}' \u4e0d\u53ef\u70ba\u7a7a")

        # Data-type specific validation
        if data_type == "trading":
            # Price bounds
            for pf in ("price_high", "price_mid", "price_low", "price_avg"):
                v = parsed.get(pf)
                if v is not None and (v < 0 or v > 9999):
                    row_errors.append(f"\u50f9\u683c\u8d85\u51fa\u7bc4\u570d (0-9999): {pf}={v}")
            # Volume bounds
            v = parsed.get("volume")
            if v is not None and (v < 0 or v > 5_000_000):
                row_errors.append(f"\u4ea4\u6613\u91cf\u8d85\u51fa\u7bc4\u570d: {v}")

        elif data_type == "production":
            v = parsed.get("production_tonnes")
            if v is not None and v < 0:
                row_errors.append(f"\u7522\u91cf\u4e0d\u53ef\u70ba\u8ca0: {v}")

        if row_errors:
            errors.append({"row": row_num, "errors": row_errors})
        else:
            valid_rows.append(parsed)

    # Store validated data
    entry["valid_rows"] = valid_rows
    entry["data_type"] = data_type

    # Preview data (first 20 valid rows)
    preview_data = []
    for row in valid_rows[:20]:
        preview_row = {}
        for k, v in row.items():
            if isinstance(v, date):
                preview_row[k] = v.isoformat()
            else:
                preview_row[k] = v
        preview_data.append(preview_row)

    return {
        "upload_id": upload_id,
        "total_rows": len(df),
        "valid_rows": len(valid_rows),
        "error_rows": len(errors),
        "duplicate_rows": duplicate_count,
        "errors": errors[:100],  # Limit error list
        "preview_data": preview_data,
    }


# ---------------------------------------------------------------------------
# Step 3: Confirm & Import
# ---------------------------------------------------------------------------
def confirm_import(
    upload_id: str,
    data_type: str,
    db: Session,
    skip_errors: bool = True,
) -> Dict[str, Any]:
    """Write validated rows to the database."""
    entry = _upload_store.get(upload_id)
    if entry is None:
        raise ValueError(f"Upload {upload_id} not found or expired.")

    valid_rows = entry.get("valid_rows")
    if valid_rows is None:
        raise ValueError("Preview step has not been completed.")

    # Build lookups
    county_map = {c.county_name_zh: c.id for c in db.query(County).all()}
    county_map_ext = dict(county_map)
    for name, cid in county_map.items():
        if "\u81fa" in name:
            county_map_ext[name.replace("\u81fa", "\u53f0")] = cid
        if "\u53f0" in name:
            county_map_ext[name.replace("\u53f0", "\u81fa")] = cid

    market_map = {}
    try:
        market_map = {m.market_code: m.id for m in db.query(Market).all()}
    except Exception:
        pass

    crop_lookup = {}
    try:
        from ..services.data_collector import AMISDataCollector
        collector = AMISDataCollector()
        crop_lookup = collector._build_crop_lookup(db)
    except Exception:
        pass

    inserted = 0
    skipped_dup = 0
    skipped_err = 0

    if data_type == "trading":
        for row in valid_rows:
            try:
                trade_date = row.get("trade_date")
                crop_name_raw = row.get("crop_name_raw", "")
                market_code = row.get("market_code")
                market_id = market_map.get(market_code) if market_code else None
                crop_id = None
                if crop_name_raw and crop_lookup:
                    from ..services.data_collector import AMISDataCollector
                    c = AMISDataCollector()
                    crop_id = c._match_crop_id(crop_name_raw, crop_lookup)

                existing = (
                    db.query(TradingData.id)
                    .filter(
                        TradingData.trade_date == trade_date,
                        TradingData.crop_name_raw == crop_name_raw,
                        TradingData.market_id == market_id,
                    )
                    .first()
                )
                if existing:
                    skipped_dup += 1
                    continue

                record = TradingData(
                    trade_date=trade_date,
                    crop_id=crop_id,
                    crop_name_raw=crop_name_raw,
                    market_id=market_id,
                    price_high=row.get("price_high"),
                    price_mid=row.get("price_mid"),
                    price_low=row.get("price_low"),
                    price_avg=row.get("price_avg"),
                    volume=row.get("volume"),
                )
                db.add(record)
                inserted += 1
            except Exception as exc:
                skipped_err += 1
                logger.debug("Import error: %s", exc)
                if not skip_errors:
                    raise

    elif data_type == "production":
        crop_rows = {c.crop_key: c for c in db.query(Crop).all()}

        for row in valid_rows:
            try:
                year = row.get("year")
                month = row.get("month")
                county_name = row.get("county_name")
                county_id = None
                if county_name:
                    county_id = county_map_ext.get(county_name)
                    if county_id is None:
                        for zh, cid in county_map_ext.items():
                            if county_name in zh or zh in county_name:
                                county_id = cid
                                break

                # Try to match crop
                crop_id = None
                crop_name = row.get("crop_name")
                if crop_name and crop_lookup:
                    from ..services.data_collector import AMISDataCollector
                    c = AMISDataCollector()
                    crop_id = c._match_crop_id(crop_name, crop_lookup)

                existing = (
                    db.query(ProductionData.id)
                    .filter(
                        ProductionData.year == year,
                        ProductionData.month == month,
                        ProductionData.crop_id == crop_id,
                        ProductionData.county_id == county_id,
                    )
                    .first()
                )
                if existing:
                    skipped_dup += 1
                    continue

                record = ProductionData(
                    year=year,
                    month=month,
                    crop_id=crop_id,
                    county_id=county_id,
                    planted_area_ha=row.get("planted_area_ha"),
                    harvest_area_ha=row.get("harvest_area_ha"),
                    production_tonnes=row.get("production_tonnes"),
                    yield_per_ha=row.get("yield_per_ha"),
                )
                db.add(record)
                inserted += 1
            except Exception as exc:
                skipped_err += 1
                logger.debug("Import error: %s", exc)
                if not skip_errors:
                    raise

    elif data_type == "weather":
        for row in valid_rows:
            try:
                obs_date = row.get("observation_date")
                county_name = row.get("county_name")
                county_id = None
                if county_name:
                    county_id = county_map_ext.get(county_name)
                    if county_id is None:
                        for zh, cid in county_map_ext.items():
                            if county_name in zh or zh in county_name:
                                county_id = cid
                                break

                existing = (
                    db.query(WeatherData.id)
                    .filter(
                        WeatherData.observation_date == obs_date,
                        WeatherData.county_id == county_id,
                    )
                    .first()
                )
                if existing:
                    skipped_dup += 1
                    continue

                record = WeatherData(
                    observation_date=obs_date,
                    county_id=county_id,
                    temp_avg=row.get("temp_avg"),
                    temp_max=row.get("temp_max"),
                    temp_min=row.get("temp_min"),
                    rainfall_mm=row.get("rainfall_mm"),
                    humidity_pct=row.get("humidity_pct"),
                )
                db.add(record)
                inserted += 1
            except Exception as exc:
                skipped_err += 1
                logger.debug("Import error: %s", exc)
                if not skip_errors:
                    raise

    if inserted > 0:
        db.commit()

    # Clean up upload entry
    if upload_id in _upload_store:
        del _upload_store[upload_id]

    return {
        "upload_id": upload_id,
        "inserted": inserted,
        "skipped_duplicate": skipped_dup,
        "skipped_error": skipped_err,
        "total_processed": inserted + skipped_dup + skipped_err,
    }
