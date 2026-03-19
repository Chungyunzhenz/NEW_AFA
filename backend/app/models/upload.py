from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from ..database import Base


class ColumnMappingPreset(Base):
    __tablename__ = "column_mapping_presets"

    __table_args__ = (
        UniqueConstraint("name", "data_type", name="uq_preset_name_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)  # trading / production / weather
    mapping_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ColumnMappingPreset(id={self.id}, name={self.name!r}, type={self.data_type})>"
