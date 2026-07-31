"""MaintenanceRecord model: history of maintenance interventions per equipment."""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import db


class MaintenanceRecord(db.Model):
    """A maintenance intervention (preventive or corrective) on an equipment."""

    __tablename__ = "maintenance_records"

    id: Mapped[int] = mapped_column(primary_key=True)

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), nullable=False, index=True)
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="maintenance_records")

    maintenance_type: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[str | None] = mapped_column(String(150), nullable=True)

    downtime_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="Completed", nullable=False)

    performed_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<MaintenanceRecord equipment_id={self.equipment_id} type={self.maintenance_type}>"
