"""Equipment model.

Represents a single physical heavy mobile equipment unit (excavator,
loader, drill, grader, truck, dozer, ...) identified by its EquipmentID
in the source dataset.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import db


class Equipment(db.Model):
    """A physical HME unit tracked by the system."""

    __tablename__ = "equipments"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    equipment_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(30), default="Operational", nullable=False)
    site: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    readings: Mapped[List["EquipmentReading"]] = relationship(
        "EquipmentReading", back_populates="equipment", cascade="all, delete-orphan"
    )
    predictions: Mapped[List["Prediction"]] = relationship(
        "Prediction", back_populates="equipment", cascade="all, delete-orphan"
    )
    maintenance_records: Mapped[List["MaintenanceRecord"]] = relationship(
        "MaintenanceRecord", back_populates="equipment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Equipment {self.equipment_code} ({self.equipment_type})>"
