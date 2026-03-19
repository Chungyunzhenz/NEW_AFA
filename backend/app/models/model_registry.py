from typing import Optional
from datetime import datetime
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class ModelRegistry(Base):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("crops.id"), nullable=True
    )
    region_type: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_metric: Mapped[str] = mapped_column(String, nullable=False)
    model_type: Mapped[str] = mapped_column(String, nullable=False)
    artifact_path: Mapped[str] = mapped_column(String, nullable=False)
    mae: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mape: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trained_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    training_rows: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    crop: Mapped[Optional["Crop"]] = relationship(
        "Crop", back_populates="model_registries"
    )

    def __repr__(self) -> str:
        return (
            f"<ModelRegistry(id={self.id}, crop_id={self.crop_id}, "
            f"type={self.model_type}, active={self.is_active})>"
        )
