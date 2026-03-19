from typing import Optional
from datetime import date, datetime
from sqlalchemy import (
    String,
    Integer,
    Float,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    __table_args__ = (
        Index(
            "ix_prediction_crop_metric_date",
            "crop_id",
            "target_metric",
            "forecast_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    crop_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("crops.id"), nullable=True
    )
    region_type: Mapped[str] = mapped_column(String, nullable=False)
    region_id: Mapped[int] = mapped_column(Integer, nullable=False)
    target_metric: Mapped[str] = mapped_column(String, nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_value: Mapped[float] = mapped_column(Float, nullable=False)
    lower_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    upper_bound: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_name: Mapped[str] = mapped_column(String, nullable=False)
    ensemble_weights: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    horizon_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    crop: Mapped[Optional["Crop"]] = relationship("Crop", back_populates="predictions")

    def __repr__(self) -> str:
        return (
            f"<Prediction(id={self.id}, crop_id={self.crop_id}, "
            f"metric={self.target_metric}, date={self.forecast_date}, "
            f"value={self.forecast_value})>"
        )
