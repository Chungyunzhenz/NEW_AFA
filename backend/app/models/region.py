from typing import List, Optional
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class County(Base):
    __tablename__ = "counties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    county_code: Mapped[str] = mapped_column(String(5), unique=True, nullable=False)
    county_name_zh: Mapped[str] = mapped_column(String, nullable=False)
    county_name_en: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    markets: Mapped[List["Market"]] = relationship("Market", back_populates="county")
    production_data: Mapped[List["ProductionData"]] = relationship(
        "ProductionData", back_populates="county"
    )
    weather_data: Mapped[List["WeatherData"]] = relationship(
        "WeatherData", back_populates="county"
    )

    def __repr__(self) -> str:
        return f"<County(id={self.id}, code={self.county_code}, name={self.county_name_zh})>"


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market_code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    market_name: Mapped[str] = mapped_column(String, nullable=False)
    county_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("counties.id"), nullable=True
    )

    county: Mapped[Optional["County"]] = relationship("County", back_populates="markets")
    trading_data: Mapped[List["TradingData"]] = relationship(
        "TradingData", back_populates="market"
    )

    def __repr__(self) -> str:
        return f"<Market(id={self.id}, code={self.market_code}, name={self.market_name})>"
