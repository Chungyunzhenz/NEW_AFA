from typing import Optional
from datetime import date
from sqlalchemy import (
    Integer,
    Float,
    Date,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class WeatherData(Base):
    __tablename__ = "weather_data"

    __table_args__ = (
        UniqueConstraint(
            "observation_date", "county_id", name="uq_weather_date_county"
        ),
        Index("ix_weather_county_date", "county_id", "observation_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    observation_date: Mapped[date] = mapped_column(Date, nullable=False)
    county_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("counties.id"), nullable=True
    )
    temp_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_max: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    temp_min: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_mm: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    humidity_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    county: Mapped[Optional["County"]] = relationship(
        "County", back_populates="weather_data"
    )

    def __repr__(self) -> str:
        return (
            f"<WeatherData(id={self.id}, date={self.observation_date}, "
            f"temp_avg={self.temp_avg}, rainfall={self.rainfall_mm})>"
        )
