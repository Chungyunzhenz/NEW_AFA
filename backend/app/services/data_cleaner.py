"""Data validation and cleaning utilities for trading records.

Provides IQR-based outlier detection, single-record validation, and a
batch cleaning pipeline that operates on all trading rows for a given crop.

Usage (programmatic)::

    from app.database import SessionLocal
    from app.services.data_cleaner import TradingDataCleaner

    db = SessionLocal()
    cleaner = TradingDataCleaner()
    stats = cleaner.clean_trading_data(db, crop_id=1)
    db.close()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Sequence

import numpy as np
from sqlalchemy.orm import Session

from ..models import TradingData

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
# Reasonable bounds for agricultural trading data (TWD/kg and kg)
PRICE_FLOOR: float = 0.0
PRICE_CEILING: float = 9999.0     # TWD per kg — extremely generous upper bound
VOLUME_FLOOR: float = 0.0
VOLUME_CEILING: float = 5_000_000.0  # 5 000 tonnes per day per market


@dataclass
class CleaningStats:
    """Summary statistics returned by :meth:`clean_trading_data`."""
    total_records: int = 0
    invalid_removed: int = 0
    outliers_flagged: int = 0
    duplicates_removed: int = 0
    zero_volume_removed: int = 0
    records_after_cleaning: int = 0
    details: List[str] = field(default_factory=list)


class TradingDataCleaner:
    """Validate, clean, and flag outliers in trading data."""

    # ------------------------------------------------------------------
    # Single-record validation
    # ------------------------------------------------------------------
    @staticmethod
    def validate_record(record: TradingData) -> List[str]:
        """Validate a single :class:`TradingData` record.

        Returns a (possibly empty) list of human-readable validation
        error messages.
        """
        errors: List[str] = []

        if record.trade_date is None:
            errors.append("trade_date is null")
        if not record.crop_name_raw:
            errors.append("crop_name_raw is empty")

        # Price checks
        for attr, label in [
            ("price_high", "上價"),
            ("price_mid", "中價"),
            ("price_low", "下價"),
            ("price_avg", "平均價"),
        ]:
            val = getattr(record, attr, None)
            if val is not None:
                if val < PRICE_FLOOR:
                    errors.append(f"{label} ({attr}) is negative: {val}")
                if val > PRICE_CEILING:
                    errors.append(f"{label} ({attr}) exceeds ceiling: {val}")

        # Price ordering: high >= mid >= low (when all present)
        if (
            record.price_high is not None
            and record.price_low is not None
            and record.price_high < record.price_low
        ):
            errors.append(
                f"price_high ({record.price_high}) < price_low ({record.price_low})"
            )

        # Volume checks
        if record.volume is not None:
            if record.volume < VOLUME_FLOOR:
                errors.append(f"volume is negative: {record.volume}")
            if record.volume > VOLUME_CEILING:
                errors.append(f"volume exceeds ceiling: {record.volume}")

        return errors

    # ------------------------------------------------------------------
    # Outlier detection
    # ------------------------------------------------------------------
    @staticmethod
    def detect_outliers(
        series: Sequence[float],
        method: Literal["iqr", "zscore"] = "iqr",
        threshold: float = 3.0,
    ) -> List[bool]:
        """Detect outliers in a numeric *series*.

        Parameters
        ----------
        series:
            Sequence of float values (must not be empty).
        method:
            ``"iqr"`` — flag values beyond ``threshold * IQR`` from Q1/Q3.
            ``"zscore"`` — flag values whose absolute Z-score exceeds
            *threshold*.
        threshold:
            Multiplier for the IQR (default 3.0) or the Z-score cutoff.

        Returns
        -------
        list of bool
            ``True`` at positions that are outliers.
        """
        arr = np.asarray(series, dtype=np.float64)

        if len(arr) < 4:
            # Not enough data to detect outliers reliably.
            return [False] * len(arr)

        if method == "iqr":
            q1 = float(np.nanpercentile(arr, 25))
            q3 = float(np.nanpercentile(arr, 75))
            iqr = q3 - q1
            lower_bound = q1 - threshold * iqr
            upper_bound = q3 + threshold * iqr
            return [
                bool(v < lower_bound or v > upper_bound)
                for v in arr
            ]

        elif method == "zscore":
            mean = float(np.nanmean(arr))
            std = float(np.nanstd(arr))
            if std == 0:
                return [False] * len(arr)
            return [
                bool(abs((v - mean) / std) > threshold)
                for v in arr
            ]

        else:
            raise ValueError(f"Unknown outlier method: {method!r}")

    # ------------------------------------------------------------------
    # Batch cleaning
    # ------------------------------------------------------------------
    def clean_trading_data(
        self,
        db: Session,
        crop_id: int,
        remove_zero_volume: bool = True,
        outlier_method: Literal["iqr", "zscore"] = "iqr",
        outlier_threshold: float = 3.0,
    ) -> CleaningStats:
        """Clean all trading data rows for a given *crop_id*.

        Steps performed:
        1. Validate each record; delete invalid ones.
        2. Remove exact duplicates (same date, crop name, market).
        3. Optionally remove zero-volume records.
        4. Detect and *flag* (log) price outliers using the chosen method.

        Returns
        -------
        CleaningStats
            A summary of the cleaning run.
        """
        stats = CleaningStats()

        records: List[TradingData] = (
            db.query(TradingData)
            .filter(TradingData.crop_id == crop_id)
            .order_by(TradingData.trade_date)
            .all()
        )
        stats.total_records = len(records)

        if not records:
            logger.info("No trading data found for crop_id=%d. Nothing to clean.", crop_id)
            return stats

        # ------------------------------------------------------------------
        # Step 1: Validate records
        # ------------------------------------------------------------------
        ids_to_delete: List[int] = []
        for rec in records:
            errors = self.validate_record(rec)
            if errors:
                ids_to_delete.append(rec.id)
                stats.details.append(
                    f"INVALID id={rec.id} date={rec.trade_date}: {'; '.join(errors)}"
                )

        if ids_to_delete:
            db.query(TradingData).filter(TradingData.id.in_(ids_to_delete)).delete(
                synchronize_session="fetch"
            )
            stats.invalid_removed = len(ids_to_delete)
            logger.info("Removed %d invalid records.", stats.invalid_removed)

        # ------------------------------------------------------------------
        # Step 2: Remove duplicates (keep first inserted, i.e. lowest id)
        # ------------------------------------------------------------------
        seen_keys: Dict[tuple, int] = {}
        dup_ids: List[int] = []
        surviving = (
            db.query(TradingData)
            .filter(TradingData.crop_id == crop_id)
            .order_by(TradingData.id)
            .all()
        )
        for rec in surviving:
            key = (rec.trade_date, rec.crop_name_raw, rec.market_id)
            if key in seen_keys:
                dup_ids.append(rec.id)
            else:
                seen_keys[key] = rec.id

        if dup_ids:
            db.query(TradingData).filter(TradingData.id.in_(dup_ids)).delete(
                synchronize_session="fetch"
            )
            stats.duplicates_removed = len(dup_ids)
            logger.info("Removed %d duplicate records.", stats.duplicates_removed)

        # ------------------------------------------------------------------
        # Step 3: Remove zero-volume records
        # ------------------------------------------------------------------
        if remove_zero_volume:
            zero_vol = (
                db.query(TradingData)
                .filter(
                    TradingData.crop_id == crop_id,
                    TradingData.volume == 0,
                )
                .all()
            )
            zero_ids = [r.id for r in zero_vol]
            if zero_ids:
                db.query(TradingData).filter(TradingData.id.in_(zero_ids)).delete(
                    synchronize_session="fetch"
                )
                stats.zero_volume_removed = len(zero_ids)
                logger.info("Removed %d zero-volume records.", stats.zero_volume_removed)

        # ------------------------------------------------------------------
        # Step 4: Detect and flag price outliers (do NOT delete — only log)
        # ------------------------------------------------------------------
        clean_records: List[TradingData] = (
            db.query(TradingData)
            .filter(TradingData.crop_id == crop_id)
            .order_by(TradingData.trade_date)
            .all()
        )

        if clean_records:
            avg_prices = [
                r.price_avg for r in clean_records if r.price_avg is not None
            ]
            if len(avg_prices) >= 4:
                outlier_flags = self.detect_outliers(
                    avg_prices, method=outlier_method, threshold=outlier_threshold
                )
                price_idx = 0
                for rec in clean_records:
                    if rec.price_avg is not None:
                        if outlier_flags[price_idx]:
                            stats.outliers_flagged += 1
                            stats.details.append(
                                f"OUTLIER id={rec.id} date={rec.trade_date} "
                                f"price_avg={rec.price_avg}"
                            )
                        price_idx += 1

            if stats.outliers_flagged > 0:
                logger.info(
                    "Flagged %d price outliers (method=%s, threshold=%.1f).",
                    stats.outliers_flagged,
                    outlier_method,
                    outlier_threshold,
                )

        db.commit()

        stats.records_after_cleaning = (
            db.query(TradingData)
            .filter(TradingData.crop_id == crop_id)
            .count()
        )

        logger.info(
            "Cleaning complete for crop_id=%d: %d -> %d records "
            "(invalid=%d, dups=%d, zero_vol=%d, outliers_flagged=%d).",
            crop_id,
            stats.total_records,
            stats.records_after_cleaning,
            stats.invalid_removed,
            stats.duplicates_removed,
            stats.zero_volume_removed,
            stats.outliers_flagged,
        )
        return stats
