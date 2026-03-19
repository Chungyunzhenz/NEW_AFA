"""APScheduler integration for the Taiwan Agricultural Product Prediction System.

Manages four recurring jobs:

1. **fetch_daily_trading** -- daily at 08:00 -- fetch yesterday's AMIS data.
2. **fetch_daily_weather** -- daily at 09:00 -- fetch yesterday's CWA data.
3. **retrain_models**      -- weekly Sunday 02:00 -- retrain all models.
4. **cleanup_old_predictions** -- monthly 1st 03:00 -- purge stale rows.

Usage (inside FastAPI lifespan)::

    from app.services.scheduler import start_scheduler, stop_scheduler

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        start_scheduler()
        yield
        stop_scheduler()

Stand-alone usage::

    from app.services.scheduler import start_scheduler, stop_scheduler
    scheduler = start_scheduler()
    # ... application runs ...
    stop_scheduler()
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED, JobExecutionEvent
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database import SessionLocal

logger = logging.getLogger(__name__)

# Module-level reference so callers can start / stop idempotently.
_scheduler: Optional[BackgroundScheduler] = None


# ---------------------------------------------------------------------------
# Job implementations
# ---------------------------------------------------------------------------

def _job_fetch_daily_trading() -> None:
    """Fetch yesterday's AMIS trading data."""
    from .data_collector import AMISDataCollector

    yesterday = date.today() - timedelta(days=1)
    logger.info("[Scheduler] fetch_daily_trading: fetching data for %s", yesterday)

    db = SessionLocal()
    try:
        collector = AMISDataCollector()
        inserted = collector.fetch_single_day(yesterday, db)
        logger.info(
            "[Scheduler] fetch_daily_trading: %d new records for %s.",
            inserted,
            yesterday,
        )
    except Exception:
        logger.exception("[Scheduler] fetch_daily_trading failed for %s.", yesterday)
    finally:
        db.close()


def _job_fetch_daily_weather() -> None:
    """Fetch yesterday's CWA weather observations."""
    from .weather_collector import CWAWeatherCollector

    yesterday = date.today() - timedelta(days=1)
    logger.info("[Scheduler] fetch_daily_weather: fetching data for %s", yesterday)

    db = SessionLocal()
    try:
        collector = CWAWeatherCollector()
        inserted = collector.fetch_daily_weather(yesterday, db)
        logger.info(
            "[Scheduler] fetch_daily_weather: %d new records for %s.",
            inserted,
            yesterday,
        )
    except Exception:
        logger.exception("[Scheduler] fetch_daily_weather failed for %s.", yesterday)
    finally:
        db.close()


def _job_retrain_models() -> None:
    """Retrain all active crop models (full pipeline)."""
    from .prediction_engine import PredictionEngine

    logger.info("[Scheduler] retrain_models: starting full pipeline ...")

    db = SessionLocal()
    try:
        engine = PredictionEngine()
        results = engine.run_full_pipeline(db)
        succeeded = sum(
            1 for v in results.values()
            if isinstance(v, dict) and v.get("status") == "ok"
        )
        failed = len(results) - succeeded
        logger.info(
            "[Scheduler] retrain_models: complete. %d succeeded, %d failed.",
            succeeded,
            failed,
        )
    except Exception:
        logger.exception("[Scheduler] retrain_models failed.")
    finally:
        db.close()


def _job_cleanup_old_predictions() -> None:
    """Delete predictions older than 12 months."""
    from .prediction_engine import PredictionEngine

    logger.info("[Scheduler] cleanup_old_predictions: starting ...")

    db = SessionLocal()
    try:
        deleted = PredictionEngine.cleanup_old_predictions(db, months_to_keep=12)
        logger.info(
            "[Scheduler] cleanup_old_predictions: %d rows deleted.", deleted
        )
    except Exception:
        logger.exception("[Scheduler] cleanup_old_predictions failed.")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Event listener
# ---------------------------------------------------------------------------

def _job_listener(event: JobExecutionEvent) -> None:
    """Log job execution results."""
    job_id = event.job_id
    if event.exception:
        logger.error(
            "[Scheduler] Job '%s' raised an exception: %s",
            job_id,
            event.exception,
        )
    else:
        logger.info(
            "[Scheduler] Job '%s' executed successfully (retval=%s).",
            job_id,
            event.retval,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def start_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the background scheduler.

    Calling this multiple times is safe -- subsequent calls return the
    existing scheduler instance without adding duplicate jobs.
    """
    global _scheduler

    if _scheduler is not None and _scheduler.running:
        logger.info("[Scheduler] Already running — returning existing instance.")
        return _scheduler

    _scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,          # Collapse missed runs into one
            "max_instances": 1,        # No concurrent executions of the same job
            "misfire_grace_time": 3600, # Allow up to 1 h late execution
        },
        timezone="Asia/Taipei",
    )

    # ---- Register jobs ----

    _scheduler.add_job(
        _job_fetch_daily_trading,
        trigger=CronTrigger(hour=8, minute=0),
        id="fetch_daily_trading",
        name="Fetch daily AMIS trading data",
        replace_existing=True,
    )

    _scheduler.add_job(
        _job_fetch_daily_weather,
        trigger=CronTrigger(hour=9, minute=0),
        id="fetch_daily_weather",
        name="Fetch daily CWA weather data",
        replace_existing=True,
    )

    _scheduler.add_job(
        _job_retrain_models,
        trigger=CronTrigger(day_of_week="sun", hour=2, minute=0),
        id="retrain_models",
        name="Weekly model retraining",
        replace_existing=True,
    )

    _scheduler.add_job(
        _job_cleanup_old_predictions,
        trigger=CronTrigger(day=1, hour=3, minute=0),
        id="cleanup_old_predictions",
        name="Monthly prediction cleanup",
        replace_existing=True,
    )

    # ---- Attach listener ----
    _scheduler.add_listener(
        _job_listener,
        EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
    )

    _scheduler.start()
    logger.info(
        "[Scheduler] Started with %d jobs.", len(_scheduler.get_jobs())
    )

    for job in _scheduler.get_jobs():
        logger.info(
            "[Scheduler]   - %s (next run: %s)", job.id, job.next_run_time
        )

    return _scheduler


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully.

    Waits for currently executing jobs to finish before shutting down.
    """
    global _scheduler

    if _scheduler is None:
        logger.info("[Scheduler] No scheduler instance to stop.")
        return

    if _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("[Scheduler] Shut down gracefully.")
    else:
        logger.info("[Scheduler] Scheduler was already stopped.")

    _scheduler = None


def get_scheduler_status() -> dict:
    """Return a JSON-serialisable summary of the scheduler state.

    Useful for exposing an admin / health-check endpoint.
    """
    if _scheduler is None or not _scheduler.running:
        return {"running": False, "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "name": job.name,
                "next_run_time": (
                    job.next_run_time.isoformat() if job.next_run_time else None
                ),
                "trigger": str(job.trigger),
            }
        )

    return {"running": True, "jobs": jobs}
