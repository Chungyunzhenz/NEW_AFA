from typing import Optional
from sqlalchemy import (
    Integer,
    Float,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class ProductionData(Base):
    __tablename__ = "production_data"

    __table_args__ = (
        UniqueConstraint(
            "year", "month", "crop_id", "county_id", name="uq_production_year_month_crop_county"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    crop_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("crops.id"), nullable=True
    )
    county_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("counties.id"), nullable=True
    )
    planted_area_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    harvest_area_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    production_tonnes: Mapped[float] = mapped_column(Float, nullable=False)
    yield_per_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    crop: Mapped[Optional["Crop"]] = relationship("Crop", back_populates="production_data")
    county: Mapped[Optional["County"]] = relationship(
        "County", back_populates="production_data"
    )

    def __repr__(self) -> str:
        return (
            f"<ProductionData(id={self.id}, year={self.year}, month={self.month}, "
            f"production={self.production_tonnes})>"
        )
