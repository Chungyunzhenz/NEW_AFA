"""One-click database rebuild for the Agriculture Prediction System.

Rebuilds the database by:
1. Backing up agriculture.db
2. Clearing polluted tables (trading_data, weather_data, predictions, model_registry)
3. Clearing trained_models/ directory
4. Re-collecting trading data from AMIS API
5. (Optionally) Re-training all models via PredictionEngine.run_full_pipeline()
6. Printing a verification summary

Usage:
    cd backend
    python ../scripts/rebuild_database.py
    python ../scripts/rebuild_database.py --start 2020-01-01 --end 2026-03-19
    python ../scripts/rebuild_database.py --skip-training
"""
from __future__ import annotations

import argparse
import glob as glob_mod
import logging
import os
import shutil
import signal
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# Project bootstrap — must run from backend/ directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.database import engine, SessionLocal, Base  # noqa: E402
from app.config import settings  # noqa: E402

if not settings.VERIFY_SSL:
    logging.getLogger(__name__).warning(
        "SSL verification is DISABLED (VERIFY_SSL=False). "
        "API requests will not verify server certificates."
    )

from app.models import (  # noqa: E402
    Crop,
    Market,
    TradingData,
    WeatherData,
    Prediction,
    ModelRegistry,
)
from app.services.data_collector import AMISDataCollector  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DB_PATH = PROJECT_ROOT / "agriculture.db"
TRAINED_MODELS_DIR = BACKEND_DIR / settings.MODEL_DIR  # backend/trained_models/

# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_requested: bool = False


def _signal_handler(signum: int, frame: object) -> None:
    global _shutdown_requested
    _shutdown_requested = True
    logger.warning("\nInterrupt received — finishing current day then stopping.")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild the agriculture database: clear polluted data, "
        "re-collect from APIs, and optionally retrain models.",
    )
    parser.add_argument(
        "--start",
        type=str,
        default=None,
        help="Start date for trading data collection (YYYY-MM-DD). Default: 20 years ago.",
    )
    parser.add_argument(
        "--end",
        type=str,
        default=None,
        help="End date for trading data collection (YYYY-MM-DD). Default: yesterday.",
    )
    parser.add_argument(
        "--skip-training",
        action="store_true",
        help="Skip model training — only re-collect data.",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Skip database backup step.",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=None,
        help="Seconds between API calls (overrides config). Default: 1.0",
    )
    return parser.parse_args()


# ===========================================================================
# Step 1: Backup
# ===========================================================================
def backup_database() -> Path | None:
    """Copy agriculture.db to agriculture.db.backup.YYYYMMDD."""
    if not DB_PATH.exists():
        logger.info("No existing database at %s — skipping backup.", DB_PATH)
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = DB_PATH.with_suffix(f".db.backup.{timestamp}")
    shutil.copy2(DB_PATH, backup_path)
    size_mb = backup_path.stat().st_size / (1024 * 1024)
    logger.info("Backed up database to %s (%.1f MB).", backup_path.name, size_mb)
    return backup_path


# ===========================================================================
# Step 2: Clear tables
# ===========================================================================
def clear_tables(db) -> dict[str, int]:
    """DELETE all rows from the 4 polluted tables. Returns row counts deleted."""
    tables = [
        ("predictions", Prediction),
        ("model_registry", ModelRegistry),
        ("trading_data", TradingData),
        ("weather_data", WeatherData),
    ]
    counts = {}
    for name, model in tables:
        deleted = db.query(model).delete(synchronize_session="fetch")
        counts[name] = deleted
        logger.info("  Cleared %s: %d rows deleted.", name, deleted)
    db.commit()
    return counts


# ===========================================================================
# Step 3: Clear trained_models/
# ===========================================================================
def clear_trained_models() -> int:
    """Remove all files from the trained_models/ directory."""
    if not TRAINED_MODELS_DIR.exists():
        TRAINED_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        logger.info("  Created %s/ (was missing).", TRAINED_MODELS_DIR.name)
        return 0

    files = list(TRAINED_MODELS_DIR.glob("*"))
    removed = 0
    for f in files:
        if f.is_file():
            f.unlink()
            removed += 1
        elif f.is_dir() and f.name != "__pycache__":
            shutil.rmtree(f)
            removed += 1
    logger.info("  Cleared trained_models/: %d files removed.", removed)
    return removed


# ===========================================================================
# Step 4: Re-collect trading data
# ===========================================================================
def collect_trading_data(
    start_date: date,
    end_date: date,
    db,
    rate_limit: float | None = None,
) -> int:
    """Fetch trading data day-by-day from AMIS API. Returns total inserted."""
    collector = AMISDataCollector()
    if rate_limit is not None:
        collector.RATE_LIMIT = rate_limit

    total_days = (end_date - start_date).days + 1
    total_inserted = 0
    days_processed = 0
    current = start_date
    last_progress = 0

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info(
        "Collecting trading data: %s to %s (%d days, ~%.1f hours at %.1fs/req).",
        start_date, end_date, total_days,
        total_days * (rate_limit or collector.RATE_LIMIT) / 3600,
        rate_limit or collector.RATE_LIMIT,
    )

    while current <= end_date:
        if _shutdown_requested:
            logger.info(
                "Shutdown requested after %d days. Data already collected is safe.",
                days_processed,
            )
            break

        days_processed += 1

        try:
            inserted = collector.fetch_single_day(current, db)
            total_inserted += inserted
        except Exception:
            logger.exception("ERROR on %s — continuing.", current)
            db.rollback()

        # Progress every 100 days
        if days_processed - last_progress >= 100 or current == end_date:
            pct = days_processed / total_days * 100
            logger.info(
                "[%d/%d  %.1f%%] %s — %d records so far.",
                days_processed, total_days, pct, current, total_inserted,
            )
            last_progress = days_processed

        current += timedelta(days=1)

        if current <= end_date and not _shutdown_requested:
            time.sleep(rate_limit or collector.RATE_LIMIT)

    return total_inserted


# ===========================================================================
# Step 5: Re-train models
# ===========================================================================
def train_all_models(db) -> dict:
    """Run the full prediction pipeline. Returns the pipeline result dict."""
    from app.services.prediction_engine import PredictionEngine

    logger.info("Starting model training (this may take a while)...")
    pe = PredictionEngine()
    results = pe.run_full_pipeline(db)
    return results


# ===========================================================================
# Step 6: Verification summary
# ===========================================================================
def print_summary(db, training_results: dict | None = None) -> None:
    """Print a verification summary of the rebuilt database."""
    from sqlalchemy import func as sqlfunc, extract

    sep = "=" * 60
    logger.info(sep)
    logger.info("VERIFICATION SUMMARY")
    logger.info(sep)

    # --- Trading data ---
    total_trading = db.query(sqlfunc.count(TradingData.id)).scalar() or 0
    logger.info("trading_data total rows: %d", total_trading)

    # Per-crop counts
    crop_counts = (
        db.query(Crop.crop_key, sqlfunc.count(TradingData.id))
        .outerjoin(TradingData, Crop.id == TradingData.crop_id)
        .group_by(Crop.crop_key)
        .order_by(sqlfunc.count(TradingData.id).desc())
        .all()
    )
    logger.info("  Per-crop record counts:")
    for crop_key, count in crop_counts:
        logger.info("    %-20s %d", crop_key, count)

    # --- NULL crop_id (unmatched crop names) ---
    null_crop_count = (
        db.query(sqlfunc.count(TradingData.id))
        .filter(TradingData.crop_id.is_(None))
        .scalar()
    ) or 0
    null_crop_pct = (null_crop_count / total_trading * 100) if total_trading else 0
    logger.info("  NULL crop_id: %d rows (%.1f%%)", null_crop_count, null_crop_pct)

    if null_crop_count > 0:
        unmatched_crops = (
            db.query(TradingData.crop_name_raw, sqlfunc.count(TradingData.id))
            .filter(TradingData.crop_id.is_(None))
            .group_by(TradingData.crop_name_raw)
            .order_by(sqlfunc.count(TradingData.id).desc())
            .limit(20)
            .all()
        )
        logger.warning("  Top unmatched crop names (crop_id IS NULL):")
        for name, count in unmatched_crops:
            logger.warning("    %-30s %d rows", name, count)

    # --- NULL market_id (unmatched market codes) ---
    null_market_count = (
        db.query(sqlfunc.count(TradingData.id))
        .filter(TradingData.market_id.is_(None))
        .scalar()
    ) or 0
    null_market_pct = (null_market_count / total_trading * 100) if total_trading else 0
    logger.info("  NULL market_id: %d rows (%.1f%%)", null_market_count, null_market_pct)

    if null_market_count > 0:
        # Report raw market codes that didn't match — stored implicitly via crop_name_raw grouping
        logger.warning(
            "  WARNING: %d rows have NULL market_id — these records "
            "cannot be linked to weather data.",
            null_market_count,
        )

    # --- Field NULL rates ---
    if total_trading > 0:
        null_fields = {
            "price_avg": TradingData.price_avg,
            "price_high": TradingData.price_high,
            "price_mid": TradingData.price_mid,
            "price_low": TradingData.price_low,
            "volume": TradingData.volume,
        }
        logger.info("  Field NULL rates:")
        for fname, col in null_fields.items():
            null_cnt = (
                db.query(sqlfunc.count(TradingData.id))
                .filter(col.is_(None))
                .scalar()
            ) or 0
            pct = null_cnt / total_trading * 100
            logger.info("    %-15s %d NULL (%.1f%%)", fname, null_cnt, pct)

    # --- Monthly data coverage per crop (24-month threshold check) ---
    logger.info("  Monthly coverage per crop (MINIMUM_MONTHS=24):")
    for crop_key, _ in crop_counts:
        if _ == 0:
            logger.info("    %-20s   0 months  ** NO DATA **", crop_key)
            continue
        # Count distinct year-month combinations for this crop
        crop_obj = db.query(Crop).filter(Crop.crop_key == crop_key).first()
        if crop_obj is None:
            continue
        month_count = (
            db.query(
                sqlfunc.count(
                    sqlfunc.distinct(
                        extract("year", TradingData.trade_date) * 100
                        + extract("month", TradingData.trade_date)
                    )
                )
            )
            .filter(TradingData.crop_id == crop_obj.id)
            .scalar()
        ) or 0
        status = "OK" if month_count >= 24 else "** BELOW THRESHOLD **"
        logger.info("    %-20s %3d months  %s", crop_key, month_count, status)

    # --- Weather data ---
    total_weather = db.query(sqlfunc.count(WeatherData.id)).scalar() or 0
    logger.info("weather_data total rows: %d", total_weather)

    # --- Model registry ---
    total_models = db.query(sqlfunc.count(ModelRegistry.id)).scalar() or 0
    logger.info("model_registry total models: %d", total_models)

    if total_models > 0:
        avg_mape = (
            db.query(sqlfunc.avg(ModelRegistry.mape))
            .filter(ModelRegistry.mape.isnot(None))
            .scalar()
        )
        logger.info("  Average MAPE: %.2f%%", (avg_mape or 0) * 100)

        # Per model-type breakdown
        type_stats = (
            db.query(
                ModelRegistry.model_type,
                sqlfunc.count(ModelRegistry.id),
                sqlfunc.avg(ModelRegistry.mape),
            )
            .group_by(ModelRegistry.model_type)
            .all()
        )
        for mtype, cnt, avg_m in type_stats:
            logger.info(
                "    %-10s %3d models, avg MAPE: %.2f%%",
                mtype, cnt, (avg_m or 0) * 100,
            )

    # --- Predictions ---
    total_preds = db.query(sqlfunc.count(Prediction.id)).scalar() or 0
    logger.info("predictions total rows: %d", total_preds)

    # --- Date range ---
    if total_trading > 0:
        min_date = db.query(sqlfunc.min(TradingData.trade_date)).scalar()
        max_date = db.query(sqlfunc.max(TradingData.trade_date)).scalar()
        logger.info("Trading data date range: %s to %s", min_date, max_date)

    # --- Training summary ---
    if training_results:
        ok_count = sum(1 for v in training_results.values() if v.get("status") == "ok")
        err_count = sum(1 for v in training_results.values() if v.get("status") == "error")
        logger.info("Training results: %d crops OK, %d errors.", ok_count, err_count)

    logger.info(sep)


# ===========================================================================
# Main
# ===========================================================================
def main() -> None:
    args = parse_args()

    today = date.today()
    start_date = (
        datetime.strptime(args.start, "%Y-%m-%d").date()
        if args.start
        else date(today.year - 20, today.month, today.day)
    )
    end_date = (
        datetime.strptime(args.end, "%Y-%m-%d").date()
        if args.end
        else today - timedelta(days=1)
    )

    if start_date > end_date:
        logger.error("start_date (%s) > end_date (%s). Aborting.", start_date, end_date)
        sys.exit(1)

    total_days = (end_date - start_date).days + 1
    est_hours = total_days * (args.rate_limit or 1.0) / 3600

    logger.info("=" * 60)
    logger.info("AGRICULTURE DATABASE REBUILD")
    logger.info("=" * 60)
    logger.info("Date range : %s to %s (%d days)", start_date, end_date, total_days)
    logger.info("Est. time  : ~%.1f hours for data collection", est_hours)
    logger.info("Training   : %s", "SKIP" if args.skip_training else "YES")
    logger.info("DB path    : %s", DB_PATH)
    logger.info("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    # Step 1: Backup
    if not args.skip_backup:
        logger.info("[Step 1/6] Backing up database...")
        backup_database()
    else:
        logger.info("[Step 1/6] Backup skipped (--skip-backup).")

    db = SessionLocal()
    try:
        # Step 2: Clear tables
        logger.info("[Step 2/6] Clearing polluted tables...")
        deleted = clear_tables(db)

        # Step 3: Clear trained models
        logger.info("[Step 3/6] Clearing trained_models/ directory...")
        clear_trained_models()

        # Step 4: Re-collect trading data
        logger.info("[Step 4/6] Collecting trading data from AMIS API...")
        total_inserted = collect_trading_data(
            start_date=start_date,
            end_date=end_date,
            db=db,
            rate_limit=args.rate_limit,
        )
        logger.info("Trading data collection done: %d records inserted.", total_inserted)

        # Step 4b: Weather data (skip if no API key)
        if settings.CWA_API_KEY:
            logger.info("[Step 4b] CWA_API_KEY found — collecting weather data...")
            from app.services.weather_collector import CWAWeatherCollector

            weather_collector = CWAWeatherCollector()
            if args.rate_limit is not None:
                weather_collector.RATE_LIMIT = args.rate_limit

            weather_current = start_date
            weather_inserted = 0
            weather_days = 0
            while weather_current <= end_date:
                if _shutdown_requested:
                    break
                weather_days += 1
                try:
                    ins = weather_collector.fetch_daily_weather(weather_current, db)
                    weather_inserted += ins
                except Exception:
                    logger.exception("Weather ERROR on %s — continuing.", weather_current)
                    db.rollback()

                if weather_days % 100 == 0:
                    pct = weather_days / total_days * 100
                    logger.info(
                        "[Weather %d/%d  %.1f%%] %s — %d records.",
                        weather_days, total_days, pct, weather_current, weather_inserted,
                    )
                weather_current += timedelta(days=1)
                if weather_current <= end_date and not _shutdown_requested:
                    time.sleep(args.rate_limit or 1.0)

            logger.info("Weather data collection done: %d records inserted.", weather_inserted)
        else:
            logger.info(
                "[Step 4b] Skipping weather data collection (no CWA_API_KEY). "
                "XGBoost weather features will be empty. "
                "Run backfill_weather.py later when you have the key."
            )

        # Step 5: Re-train models
        training_results = None
        if not args.skip_training:
            if _shutdown_requested:
                logger.info("[Step 5/6] Skipping training — shutdown was requested.")
            else:
                logger.info("[Step 5/6] Training all models...")
                training_results = train_all_models(db)
        else:
            logger.info("[Step 5/6] Training skipped (--skip-training).")

        # Step 6: Summary
        logger.info("[Step 6/6] Verification summary...")
        print_summary(db, training_results)

    except Exception:
        logger.exception("Fatal error during rebuild.")
        sys.exit(1)
    finally:
        db.close()

    logger.info("Database rebuild complete!")


if __name__ == "__main__":
    main()
