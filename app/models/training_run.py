"""TrainingRun model: audit trail of AutoML training executions."""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import db


class TrainingRun(db.Model):
    """One execution of the AutoML training pipeline."""

    __tablename__ = "training_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_version_id: Mapped[int | None] = mapped_column(ForeignKey("model_versions.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(30), default="running", nullable=False)
    leaderboard_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    def __repr__(self) -> str:
        return f"<TrainingRun {self.id} status={self.status}>"
