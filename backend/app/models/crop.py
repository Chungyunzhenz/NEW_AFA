from typing import List, Optional
from sqlalchemy import String, Integer, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    display_name_zh: Mapped[str] = mapped_column(String, nullable=False)
    display_name_en: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    category_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    config_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    trading_data: Mapped[List["TradingData"]] = relationship(
        "TradingData", back_populates="crop"
    )
    production_data: Mapped[List["ProductionData"]] = relationship(
        "ProductionData", back_populates="crop"
    )
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="crop"
    )
    model_registries: Mapped[List["ModelRegistry"]] = relationship(
        "ModelRegistry", back_populates="crop"
    )

    def __repr__(self) -> str:
        return f"<Crop(id={self.id}, key={self.crop_key}, name={self.display_name_zh})>"
