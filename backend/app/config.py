import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DB_PATH = _PROJECT_ROOT / "agriculture.db"


class Settings(BaseSettings):
    APP_NAME: str = "台灣農產品產銷量預測系統"
    DEBUG: bool = True
    DATABASE_URL: str = f"sqlite:///{_DB_PATH}"
    AMIS_API_BASE: str = "https://data.moa.gov.tw/Service/OpenData/FromM/FarmTransData.aspx"
    CWA_API_KEY: str = ""
    CWA_API_BASE: str = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]
    FETCH_RATE_LIMIT_SECONDS: float = 1.0
    MODEL_DIR: str = "trained_models"
    VERIFY_SSL: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

if not settings.CWA_API_KEY:
    logger.warning(
        "CWA_API_KEY 未設定！天氣資料收集將無法運作。"
        "請至 https://opendata.cwa.gov.tw 申請授權碼，"
        "並在 backend/.env 中設定 CWA_API_KEY=你的授權碼"
    )


def load_crop_configs() -> Dict[str, Any]:
    """Scan backend/app/data/crop_configs/ for all .json files and load them."""
    config_dir = Path(__file__).parent / "data" / "crop_configs"
    configs = {}
    if config_dir.exists():
        for f in config_dir.glob("*.json"):
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                configs[data["crop_key"]] = data
    return configs
