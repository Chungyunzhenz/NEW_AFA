import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...models.region import County
from ...models.prediction import Prediction
from ...models.model_registry import ModelRegistry
from ...schemas.prediction import (
    PredictionResponse,
    PredictionByCounty,
    ModelInfoResponse,
)

router = APIRouter()


def _get_crop_or_404(db: Session, crop_key: str) -> Crop:
    """Fetch a crop by its key or raise 404."""
    crop = db.query(Crop).filter(Crop.crop_key == crop_key).first()
    if not crop:
        raise HTTPException(status_code=404, detail=f"Crop '{crop_key}' not found")
    return crop


@router.get("/{crop_key}/forecast", response_model=List[PredictionResponse])
def get_forecast(
    crop_key: str,
    metric: Optional[str] = Query(
        None, description="Target metric to filter (e.g., price_avg, volume)"
    ),
    horizon: Optional[str] = Query(
        None, description="Horizon label to filter (e.g., 1m, 3m, 6m)"
    ),
    region_type: Optional[str] = Query(
        None, description="Region type filter (e.g., county, market, national)"
    ),
    region_id: Optional[int] = Query(None, description="Region ID filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get the latest predictions for a crop.
    Supports filtering by metric, horizon, region type, and region ID.
    """
    crop = _get_crop_or_404(db, crop_key)

    query = db.query(Prediction).filter(Prediction.crop_id == crop.id)

    if metric:
        query = query.filter(Prediction.target_metric == metric)
    if horizon:
        query = query.filter(Prediction.horizon_label == horizon)
    if region_type:
        query = query.filter(Prediction.region_type == region_type)
    if region_id is not None:
        query = query.filter(Prediction.region_id == region_id)

    query = query.order_by(desc(Prediction.forecast_date), desc(Prediction.generated_at))

    rows = query.offset(skip).limit(limit).all()

    results = []
    for p in rows:
        # Parse ensemble_weights from JSON string if present
        ensemble_weights = None
        if p.ensemble_weights:
            try:
                ensemble_weights = json.loads(p.ensemble_weights)
            except json.JSONDecodeError:
                ensemble_weights = None

        results.append(
            PredictionResponse(
                id=p.id,
                crop_key=crop.crop_key,
                region_type=p.region_type,
                region_id=p.region_id,
                target_metric=p.target_metric,
                forecast_date=p.forecast_date,
                forecast_value=p.forecast_value,
                lower_bound=p.lower_bound or 0.0,
                upper_bound=p.upper_bound or 0.0,
                model_name=p.model_name,
                ensemble_weights=ensemble_weights,
                generated_at=p.generated_at,
                horizon_label=p.horizon_label or "",
            )
        )
    return results


@router.get("/{crop_key}/by-county", response_model=List[PredictionByCounty])
def get_predictions_by_county(
    crop_key: str,
    metric: str = Query(
        "price_avg", description="Target metric (e.g., price_avg, volume)"
    ),
    forecast_date: Optional[date] = Query(
        None,
        description="Specific forecast date to query. Defaults to the latest available.",
    ),
    db: Session = Depends(get_db),
):
    """
    Get county-level predictions for choropleth map display.
    Returns the latest prediction per county for the given metric.
    """
    crop = _get_crop_or_404(db, crop_key)

    # If no forecast_date provided, find the latest one
    if forecast_date is None:
        latest = (
            db.query(Prediction.forecast_date)
            .filter(Prediction.crop_id == crop.id)
            .filter(Prediction.region_type == "county")
            .filter(Prediction.target_metric == metric)
            .order_by(desc(Prediction.forecast_date))
            .first()
        )
        if not latest:
            return []
        forecast_date = latest.forecast_date

    query = (
        db.query(
            County.county_code,
            County.county_name_zh,
            Prediction.forecast_value,
            Prediction.lower_bound,
            Prediction.upper_bound,
        )
        .select_from(Prediction)
        .join(County, Prediction.region_id == County.id)
        .filter(Prediction.crop_id == crop.id)
        .filter(Prediction.region_type == "county")
        .filter(Prediction.target_metric == metric)
        .filter(Prediction.forecast_date == forecast_date)
    )

    rows = query.all()

    results = []
    for row in rows:
        results.append(
            PredictionByCounty(
                county_code=row.county_code,
                county_name_zh=row.county_name_zh,
                forecast_value=row.forecast_value,
                lower_bound=row.lower_bound or 0.0,
                upper_bound=row.upper_bound or 0.0,
            )
        )
    return results


@router.get("/{crop_key}/model-info", response_model=List[ModelInfoResponse])
def get_model_info(
    crop_key: str,
    db: Session = Depends(get_db),
):
    """
    Get model performance metrics and registration info for a crop.
    Returns all registered models (active and inactive) for review.
    """
    crop = _get_crop_or_404(db, crop_key)

    models = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.crop_id == crop.id)
        .order_by(desc(ModelRegistry.trained_at))
        .all()
    )

    results = []
    for m in models:
        results.append(
            ModelInfoResponse(
                model_type=m.model_type,
                mae=m.mae or 0.0,
                rmse=m.rmse or 0.0,
                mape=m.mape or 0.0,
                trained_at=m.trained_at,
                training_rows=m.training_rows or 0,
                is_active=m.is_active,
            )
        )
    return results


@router.post("/{crop_key}/retrain")
def trigger_retrain(
    crop_key: str,
    db: Session = Depends(get_db),
):
    """
    Trigger model retraining for a specific crop.
    Currently a placeholder that acknowledges the request.
    """
    crop = _get_crop_or_404(db, crop_key)
    return {
        "status": "queued",
        "crop_key": crop.crop_key,
        "message": f"Retraining for '{crop.display_name_zh}' has been queued.",
    }
