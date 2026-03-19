from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings, load_crop_configs
from .database import engine, Base, SessionLocal
from .api.router import api_router
from .services.scheduler import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from . import models  # noqa: F401 — ensure all models are imported for table creation

    Base.metadata.create_all(bind=engine)

    # Sync crop configs to DB
    crop_configs = load_crop_configs()
    db = SessionLocal()
    try:
        import json
        from .models.crop import Crop

        for key, config in crop_configs.items():
            existing = db.query(Crop).filter(Crop.crop_key == key).first()
            if not existing:
                crop = Crop(
                    crop_key=config["crop_key"],
                    display_name_zh=config["display_name_zh"],
                    display_name_en=config["display_name_en"],
                    category_code=config["category_code"],
                    config_json=json.dumps(config, ensure_ascii=False),
                    is_active=True,
                )
                db.add(crop)
            else:
                existing.config_json = json.dumps(config, ensure_ascii=False)
                existing.display_name_zh = config["display_name_zh"]
                existing.display_name_en = config["display_name_en"]
        db.commit()

        # Seed counties from JSON
        from pathlib import Path
        from .models.region import County, Market

        seed_dir = Path(__file__).resolve().parent / "data" / "seed"

        counties_file = seed_dir / "counties.json"
        if counties_file.exists():
            counties_data = json.load(open(counties_file, "r", encoding="utf-8"))
            for item in counties_data:
                existing = db.query(County).filter(County.county_code == item["county_code"]).first()
                if not existing:
                    db.add(County(
                        county_code=item["county_code"],
                        county_name_zh=item["county_name_zh"],
                        county_name_en=item.get("county_name_en", ""),
                    ))
            db.commit()
            logger.info("Seeded %d counties.", db.query(County).count())

        # Seed markets from JSON (needs county_id lookup)
        markets_file = seed_dir / "markets.json"
        if markets_file.exists():
            markets_data = json.load(open(markets_file, "r", encoding="utf-8"))
            county_lookup = {c.county_code: c.id for c in db.query(County).all()}
            for item in markets_data:
                existing = db.query(Market).filter(Market.market_code == item["market_code"]).first()
                if not existing:
                    db.add(Market(
                        market_code=item["market_code"],
                        market_name=item["market_name"],
                        county_id=county_lookup.get(item.get("county_code")),
                    ))
            db.commit()
            logger.info("Seeded %d markets.", db.query(Market).count())

        # Check for trading records with NULL market_id (need re-sync)
        from .models.trading import TradingData
        null_market_count = db.query(TradingData).filter(TradingData.market_id.is_(None)).count()
        if null_market_count > 0:
            logger.warning(
                "Found %d trading records with NULL market_id. "
                "Re-run data sync to backfill (POST /api/v1/data-sync/fetch-latest).",
                null_market_count,
            )
    finally:
        db.close()

    # Start background scheduler
    start_scheduler()

    logger.info(
        f"{settings.APP_NAME} started. Loaded {len(crop_configs)} crop configs."
    )
    yield
    # Shutdown
    stop_scheduler()
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"app": settings.APP_NAME, "version": "1.0.0"}
