"""Data export endpoints — CSV, Excel, and SQLite database download."""
import csv
import io
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...config import settings
from ...database import get_db
from ...models.crop import Crop
from ...models.trading import TradingData
from ...models.prediction import Prediction
from ...models.model_registry import ModelRegistry

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


def _csv_response(rows, headers, filename):
    """Build a StreamingResponse for CSV with UTF-8 BOM."""
    buf = io.StringIO()
    buf.write("\ufeff")  # UTF-8 BOM for Excel compatibility
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/predictions/{crop_key}")
def export_predictions(
    crop_key: str,
    format: str = Query("csv", description="Export format: csv"),
    horizon: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Export prediction results as CSV."""
    crop = _get_crop_or_404(db, crop_key)

    query = (
        db.query(Prediction)
        .filter(Prediction.crop_id == crop.id)
        .order_by(desc(Prediction.forecast_date))
    )
    if horizon:
        query = query.filter(Prediction.horizon_label == horizon)

    rows = query.all()

    headers = [
        "forecast_date", "target_metric", "model_name", "horizon_label",
        "region_type", "region_id", "forecast_value", "lower_bound",
        "upper_bound", "generated_at",
    ]
    data = [
        [
            str(r.forecast_date), r.target_metric, r.model_name, r.horizon_label,
            r.region_type, r.region_id, r.forecast_value, r.lower_bound,
            r.upper_bound, str(r.generated_at) if r.generated_at else "",
        ]
        for r in rows
    ]

    ts = datetime.utcnow().strftime("%Y%m%d")
    return _csv_response(data, headers, f"{crop_key}_predictions_{ts}.csv")


@router.get("/historical/{crop_key}")
def export_historical(
    crop_key: str,
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Export historical trading data as CSV."""
    crop = _get_crop_or_404(db, crop_key)

    rows = (
        db.query(TradingData)
        .filter(TradingData.crop_id == crop.id)
        .order_by(TradingData.trade_date)
        .all()
    )

    headers = [
        "trade_date", "price_high", "price_mid", "price_low",
        "price_avg", "volume", "market_id",
    ]
    data = [
        [
            str(r.trade_date), r.price_high, r.price_mid, r.price_low,
            r.price_avg, r.volume, r.market_id,
        ]
        for r in rows
    ]

    ts = datetime.utcnow().strftime("%Y%m%d")
    return _csv_response(data, headers, f"{crop_key}_historical_{ts}.csv")


@router.get("/model-performance")
def export_model_performance(
    format: str = Query("csv"),
    db: Session = Depends(get_db),
):
    """Export model performance metrics as CSV."""
    rows = (
        db.query(ModelRegistry, Crop.crop_key)
        .join(Crop, ModelRegistry.crop_id == Crop.id)
        .order_by(desc(ModelRegistry.trained_at))
        .all()
    )

    headers = [
        "crop_key", "model_type", "region_type", "region_id",
        "target_metric", "mae", "rmse", "mape",
        "training_rows", "trained_at", "is_active",
    ]
    data = [
        [
            crop_key, r.model_type, r.region_type, r.region_id,
            r.target_metric, r.mae, r.rmse, r.mape,
            r.training_rows, str(r.trained_at) if r.trained_at else "", r.is_active,
        ]
        for r, crop_key in rows
    ]

    ts = datetime.utcnow().strftime("%Y%m%d")
    return _csv_response(data, headers, f"model_performance_{ts}.csv")


@router.get("/database")
def export_database():
    """Download the SQLite database file directly."""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "..",
        "agriculture.db",
    )
    db_path = os.path.abspath(db_path)

    if not os.path.exists(db_path):
        raise HTTPException(status_code=404, detail="Database file not found")

    ts = datetime.utcnow().strftime("%Y%m%d")
    return FileResponse(
        db_path,
        media_type="application/x-sqlite3",
        filename=f"agriculture_{ts}.db",
    )
