import threading
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ...config import load_crop_configs
from ...database import SessionLocal, get_db
from ...models.crop import Crop
from ...models.production import ProductionData
from ...models.trading import TradingData

router = APIRouter()

# Module-level sync state tracking
_sync_state: Dict[str, Any] = {
    "is_running": False,
    "last_run_at": None,
    "last_status": None,  # "success" | "failed"
    "last_error": None,
    "records_fetched": 0,
    "task_type": None,
}
_sync_lock = threading.Lock()


def _run_sync_task(data_type: str, days_back: int) -> None:
    """Background task: fetch trading and/or weather data."""
    global _sync_state

    db = SessionLocal()
    try:
        total_inserted = 0

        if data_type in ("trading", "both"):
            from ...services.data_collector import AMISDataCollector
            collector = AMISDataCollector()
            end_date = date.today() - timedelta(days=1)
            start_date = end_date - timedelta(days=days_back - 1)
            inserted = collector.fetch_date_range(start_date, end_date, db)
            total_inserted += inserted

        if data_type in ("weather", "both"):
            try:
                from ...services.weather_collector import CWAWeatherCollector
                collector = CWAWeatherCollector()
                end_date = date.today() - timedelta(days=1)
                start_date = end_date - timedelta(days=days_back - 1)
                current = start_date
                while current <= end_date:
                    inserted = collector.fetch_daily_weather(current, db)
                    total_inserted += inserted
                    current += timedelta(days=1)
            except Exception as e:
                # Weather collector may fail if no API key configured
                import logging
                logging.getLogger(__name__).warning("Weather sync skipped: %s", e)

        with _sync_lock:
            _sync_state.update({
                "is_running": False,
                "last_run_at": datetime.utcnow().isoformat(),
                "last_status": "success",
                "last_error": None,
                "records_fetched": total_inserted,
            })
    except Exception as exc:
        with _sync_lock:
            _sync_state.update({
                "is_running": False,
                "last_run_at": datetime.utcnow().isoformat(),
                "last_status": "failed",
                "last_error": str(exc),
                "records_fetched": 0,
            })
    finally:
        db.close()


@router.get("/status")
def get_sync_status(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Get the current data sync status."""
    last_sync_row = db.query(func.max(TradingData.created_at)).scalar()
    last_sync_time = last_sync_row.isoformat() if last_sync_row else None

    trading_counts_query = (
        db.query(
            Crop.crop_key,
            Crop.display_name_zh,
            func.count(TradingData.id).label("trading_records"),
        )
        .outerjoin(TradingData, Crop.id == TradingData.crop_id)
        .group_by(Crop.crop_key, Crop.display_name_zh)
        .all()
    )

    production_counts_query = (
        db.query(
            Crop.crop_key,
            func.count(ProductionData.id).label("production_records"),
        )
        .outerjoin(ProductionData, Crop.id == ProductionData.crop_id)
        .group_by(Crop.crop_key)
        .all()
    )

    production_map = {row.crop_key: row.production_records for row in production_counts_query}

    crop_stats = []
    for row in trading_counts_query:
        crop_stats.append({
            "crop_key": row.crop_key,
            "display_name_zh": row.display_name_zh,
            "trading_records": row.trading_records,
            "production_records": production_map.get(row.crop_key, 0),
        })

    date_range_row = db.query(
        func.min(TradingData.trade_date).label("earliest_date"),
        func.max(TradingData.trade_date).label("latest_date"),
    ).first()

    earliest_date = (
        date_range_row.earliest_date.isoformat()
        if date_range_row and date_range_row.earliest_date
        else None
    )
    latest_date = (
        date_range_row.latest_date.isoformat()
        if date_range_row and date_range_row.latest_date
        else None
    )

    # Count unmatched records
    unmatched_count = (
        db.query(func.count(TradingData.id))
        .filter(TradingData.crop_id.is_(None))
        .scalar()
    ) or 0

    # Scheduler status
    try:
        from ...services.scheduler import get_scheduler_status
        scheduler_info = get_scheduler_status()
    except Exception:
        scheduler_info = {"running": False, "jobs": []}

    return {
        "last_sync_time": last_sync_time,
        "earliest_trade_date": earliest_date,
        "latest_trade_date": latest_date,
        "crops": crop_stats,
        "unmatched_records": unmatched_count,
        "scheduler": scheduler_info,
        "sync_task": dict(_sync_state),
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.post("/fetch-latest")
def fetch_latest_data(
    background_tasks: BackgroundTasks,
    data_type: str = Query("both", regex="^(trading|weather|both)$"),
    days_back: int = Query(1, ge=1, le=365),
) -> Dict[str, Any]:
    """Trigger a manual data fetch from external data sources."""
    with _sync_lock:
        if _sync_state["is_running"]:
            return {
                "status": "already_running",
                "message": "A sync task is already in progress.",
                "sync_task": dict(_sync_state),
            }
        _sync_state.update({
            "is_running": True,
            "task_type": data_type,
            "last_error": None,
            "records_fetched": 0,
        })

    background_tasks.add_task(_run_sync_task, data_type, days_back)

    return {
        "status": "running",
        "message": f"Sync started: {data_type}, {days_back} day(s) back.",
        "requested_at": datetime.utcnow().isoformat(),
    }


@router.post("/backfill-crop-ids")
def backfill_crop_ids(
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Re-scan trading records with NULL crop_id and try to match them."""
    from ...services.data_collector import AMISDataCollector

    collector = AMISDataCollector()
    crop_lookup = collector._build_crop_lookup(db)

    unmatched = (
        db.query(TradingData)
        .filter(TradingData.crop_id.is_(None))
        .all()
    )

    matched_count = 0
    for record in unmatched:
        crop_id = collector._match_crop_id(record.crop_name_raw, crop_lookup)
        if crop_id is not None:
            record.crop_id = crop_id
            matched_count += 1

    if matched_count > 0:
        db.commit()

    return {
        "total_unmatched": len(unmatched),
        "newly_matched": matched_count,
        "still_unmatched": len(unmatched) - matched_count,
    }
