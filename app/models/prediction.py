"""Prediction model: stores a single failure-risk prediction outcome."""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Float, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import db


class Prediction(db.Model):
    """The result of running the active model against one equipment's features."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)

    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipments.id"), nullable=False, index=True)
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="predictions")

    model_version_id: Mapped[int] = mapped_column(ForeignKey("model_versions.id"), nullable=False)

    probability: Mapped[float] = mapped_column(Float, nullable=False)
    predicted_label: Mapped[int] = mapped_column(nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)

    input_features_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<Prediction equipment_id={self.equipment_id} risk={self.risk_level}>"
