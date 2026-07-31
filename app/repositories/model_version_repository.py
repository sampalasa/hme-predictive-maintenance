"""Repository for the ModelVersion model."""

from app.models import ModelVersion, db
from app.repositories.base_repository import BaseRepository


class ModelVersionRepository(BaseRepository[ModelVersion]):
    """Data-access operations specific to ModelVersion."""

    def __init__(self) -> None:
        super().__init__(ModelVersion)

    def get_active(self) -> ModelVersion | None:
        return db.session.query(ModelVersion).filter_by(is_active=True).first()

    def deactivate_all(self) -> None:
        db.session.query(ModelVersion).update({ModelVersion.is_active: False})
        db.session.commit()
