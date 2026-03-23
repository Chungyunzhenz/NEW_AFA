from typing import Optional
from datetime import date, datetime
from sqlalchemy import (
    String,
    Integer,
    Float,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from ..database import Base


class TradingData(Base):
    __tablename__ = "trading_data"

    __table_args__ = (
        UniqueConstraint(
            "trade_date", "crop_name_raw", "market_id", name="uq_trading_date_crop_market"
        ),
        Index("ix_trading_crop_date", "crop_id", "trade_date"),
        Index("ix_trading_market_date", "market_id", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    crop_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("crops.id"), nullable=True
    )
    crop_name_raw: Mapped[str] = mapped_column(String, nullable=False)
    market_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("markets.id"), nullable=True
    )
    market_code_raw: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_mid: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    price_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    crop: Mapped[Optional["Crop"]] = relationship("Crop", back_populates="trading_data")
    market: Mapped[Optional["Market"]] = relationship(
        "Market", back_populates="trading_data"
    )

    def __repr__(self) -> str:
        return (
            f"<TradingData(id={self.id}, date={self.trade_date}, "
            f"crop={self.crop_name_raw}, avg_price={self.price_avg})>"
        )
