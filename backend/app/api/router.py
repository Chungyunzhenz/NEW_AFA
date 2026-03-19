from fastapi import APIRouter
from .endpoints import trading, production, predictions, crops, regions, data_sync, upload, traffic_light

api_router = APIRouter()
api_router.include_router(crops.router, prefix="/crops", tags=["crops"])
api_router.include_router(regions.router, prefix="/regions", tags=["regions"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(production.router, prefix="/production", tags=["production"])
api_router.include_router(
    predictions.router, prefix="/predictions", tags=["predictions"]
)
api_router.include_router(data_sync.router, prefix="/sync", tags=["data-sync"])
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(
    traffic_light.router, prefix="/alerts/traffic-light", tags=["alerts"]
)
