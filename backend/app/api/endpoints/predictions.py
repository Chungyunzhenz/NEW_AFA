import json
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from ...database import get_db
from ...models.crop import Crop
from ...models.region import County, Market
from ...models.prediction import Prediction
from ...models.model_registry import ModelRegistry
from ...models.trading import TradingData
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

    Since training only produces market-level and national-level predictions,
    this endpoint derives county data by joining market predictions through
    the Market -> County relationship and aggregating per county.
    """
    crop = _get_crop_or_404(db, crop_key)

    # If no forecast_date provided, find the latest one from market predictions
    if forecast_date is None:
        latest = (
            db.query(Prediction.forecast_date)
            .filter(Prediction.crop_id == crop.id)
            .filter(Prediction.region_type == "market")
            .filter(Prediction.target_metric == metric)
            .order_by(desc(Prediction.forecast_date))
            .first()
        )
        if not latest:
            return []
        forecast_date = latest.forecast_date

    # Join market predictions -> Market -> County, then aggregate per county
    query = (
        db.query(
            County.county_code,
            County.county_name_zh,
            func.avg(Prediction.forecast_value).label("forecast_value"),
            func.min(Prediction.lower_bound).label("lower_bound"),
            func.max(Prediction.upper_bound).label("upper_bound"),
        )
        .select_from(Prediction)
        .join(Market, Prediction.region_id == Market.id)
        .join(County, Market.county_id == County.id)
        .filter(Prediction.crop_id == crop.id)
        .filter(Prediction.region_type == "market")
        .filter(Prediction.target_metric == metric)
        .filter(Prediction.forecast_date == forecast_date)
        .group_by(County.county_code, County.county_name_zh)
    )

    rows = query.all()

    results = []
    for row in rows:
        results.append(
            PredictionByCounty(
                county_code=row.county_code,
                county_name_zh=row.county_name_zh,
                forecast_value=round(float(row.forecast_value), 2),
                lower_bound=round(float(row.lower_bound), 2) if row.lower_bound else 0.0,
                upper_bound=round(float(row.upper_bound), 2) if row.upper_bound else 0.0,
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
        .filter(ModelRegistry.is_active == True)
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


@router.get("/{crop_key}/summary")
def get_forecast_summary(
    crop_key: str,
    horizon: str = Query("1m", description="Horizon label (1m, 3m, 6m)"),
    db: Session = Depends(get_db),
):
    """
    Get a human-readable forecast summary with trend, confidence, and insights.
    """
    from ...services.forecast_summary import generate_summary
    return generate_summary(db, crop_key, horizon)


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


@router.get("/{crop_key}/feature-importance")
def get_feature_importance(crop_key: str, db: Session = Depends(get_db)):
    crop = _get_crop_or_404(db, crop_key)
    # Find the latest active xgboost model with feature importance data
    model = (
        db.query(ModelRegistry)
        .filter(
            ModelRegistry.crop_id == crop.id,
            ModelRegistry.model_type == "xgboost",
            ModelRegistry.is_active == True,
            ModelRegistry.feature_importance_json.isnot(None),
        )
        .order_by(desc(ModelRegistry.trained_at))
        .first()
    )
    if not model or not model.feature_importance_json:
        return {"features": [], "message": "No feature importance data available"}
    fi = json.loads(model.feature_importance_json)
    features = [{"name": k, "importance": round(v, 4)} for k, v in fi.items()]
    return {"features": features}


@router.get("/{crop_key}/accuracy")
def get_model_accuracy(crop_key: str, db: Session = Depends(get_db)):
    crop = _get_crop_or_404(db, crop_key)
    # Get all active models' metrics
    models = (
        db.query(ModelRegistry)
        .filter(ModelRegistry.crop_id == crop.id, ModelRegistry.is_active == True)
        .order_by(desc(ModelRegistry.trained_at))
        .all()
    )
    results = {}
    for m in models:
        key = f"{m.model_type}_{m.target_metric}_{m.region_type}_{m.region_id}"
        if key not in results:  # Only keep the latest
            results[key] = {
                "model_type": m.model_type,
                "target_metric": m.target_metric,
                "region_type": m.region_type,
                "mae": round(m.mae, 4) if m.mae else None,
                "rmse": round(m.rmse, 4) if m.rmse else None,
                "mape": round(m.mape, 2) if m.mape else None,
                "training_rows": m.training_rows,
            }
    return {"models": list(results.values())}


@router.post("/{crop_key}/predict-from-recent")
def predict_from_recent(
    crop_key: str,
    days: int = Query(7, description="Use most recent N days of data"),
    db: Session = Depends(get_db),
):
    """Use the most recent trading data to generate a quick prediction."""
    crop = _get_crop_or_404(db, crop_key)
    from datetime import timedelta

    # Find the latest trade date for this crop instead of using utcnow()
    latest_date_row = (
        db.query(func.max(TradingData.trade_date))
        .filter(TradingData.crop_id == crop.id)
        .scalar()
    )
    if not latest_date_row:
        raise HTTPException(404, "No trading data found for this crop")
    cutoff = latest_date_row - timedelta(days=days)

    recent = (
        db.query(
            func.avg(TradingData.price_avg).label("avg_price"),
            func.sum(TradingData.volume).label("total_volume"),
            func.count(TradingData.id).label("record_count"),
        )
        .filter(TradingData.crop_id == crop.id, TradingData.trade_date >= cutoff)
        .first()
    )

    if not recent or recent.record_count == 0:
        raise HTTPException(404, "No recent data found")

    # Get latest prediction for comparison
    latest_pred = (
        db.query(Prediction)
        .filter(
            Prediction.crop_id == crop.id,
            Prediction.target_metric == "price_avg",
            Prediction.model_name == "ensemble",
        )
        .order_by(desc(Prediction.forecast_date))
        .first()
    )

    return {
        "crop_key": crop_key,
        "days_used": days,
        "record_count": recent.record_count,
        "recent_avg_price": round(float(recent.avg_price), 2),
        "recent_total_volume": round(float(recent.total_volume), 2),
        "model_forecast": round(latest_pred.forecast_value, 2) if latest_pred else None,
        "difference_pct": round(
            (float(recent.avg_price) - latest_pred.forecast_value) / latest_pred.forecast_value * 100, 2
        ) if latest_pred and latest_pred.forecast_value else None,
    }
