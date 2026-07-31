"""EquipmentReading model: one row per sensor reading from HME_Downtime."""

from datetime import datetime

from sqlalchemy import ForeignKey, String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import db


class EquipmentReading(db.Model):
    """A raw sensor reading imported from the HME_Downtime dataset."""

    __tablename__ = "equipment_readings"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), nullable=False, index=True)
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="readings")

    timestamp: Mapped[datetime] = mapped_column(nullable=False, index=True)
    operating_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    engine_temp: Mapped[float] = mapped_column(Float, nullable=False)
    hydraulic_pressure: Mapped[float] = mapped_column(Float, nullable=False)
    vibration: Mapped[float] = mapped_column(Float, nullable=False)
    failure_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    failure_within_7_days: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    def __repr__(self) -> str:
        return f"<EquipmentReading equipment_id={self.equipment_id} at={self.timestamp}>"
