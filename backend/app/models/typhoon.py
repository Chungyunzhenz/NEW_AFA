from typing import Optional
from datetime import date, datetime
from sqlalchemy import (
    Integer,
    Float,
    String,
    Date,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class TyphoonEvent(Base):
    """Historical typhoon events that triggered warnings for Taiwan.

    Data source: CWA Typhoon Database (rdc28.cwa.gov.tw/TDB)
    """

    __tablename__ = "typhoon_events"

    __table_args__ = (
        Index("ix_typhoon_year", "year"),
        Index("ix_typhoon_dates", "warning_start", "warning_end"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    cwa_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    typhoon_name_zh: Mapped[str] = mapped_column(String, nullable=False)
    typhoon_name_en: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    warning_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    intensity: Mapped[str] = mapped_column(String, nullable=False)  # mild/moderate/severe
    invasion_path: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    min_pressure_hpa: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_wind_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storm_radius_7_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    storm_radius_10_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    warning_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    affected_counties = relationship(
        "TyphoonAffectedCounty", back_populates="typhoon", cascade="all, delete-orphan"
    )


class TyphoonAffectedCounty(Base):
    """Counties affected by a specific typhoon event."""

    __tablename__ = "typhoon_affected_counties"

    __table_args__ = (
        Index("ix_typhoon_county", "typhoon_id", "county_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    typhoon_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("typhoon_events.id"), nullable=False
    )
    county_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("counties.id"), nullable=False
    )
    impact_level: Mapped[str] = mapped_column(
        String, nullable=False, default="direct"
    )  # direct / indirect / peripheral

    typhoon = relationship("TyphoonEvent", back_populates="affected_counties")
