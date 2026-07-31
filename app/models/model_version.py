"""ModelVersion model: registry of trained ML model artifacts."""

from datetime import datetime, timezone

from sqlalchemy import String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import db


class ModelVersion(db.Model):
    """A trained and persisted machine learning model artifact."""

    __tablename__ = "model_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(80), nullable=False)
    version_number: Mapped[str] = mapped_column(String(30), nullable=False)

    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    feature_list_path: Mapped[str] = mapped_column(String(500), nullable=False)

    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    hyperparameters_json: Mapped[str] = mapped_column(Text, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trained_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<ModelVersion {self.name} v{self.version_number} active={self.is_active}>"
