"""Repository for the Prediction model."""

from app.models import Prediction, db
from app.repositories.base_repository import BaseRepository


class PredictionRepository(BaseRepository[Prediction]):
    """Data-access operations specific to Prediction."""

    def __init__(self) -> None:
        super().__init__(Prediction)

    def get_latest_for_equipment(self, equipment_id: int) -> Prediction | None:
        return (
            db.session.query(Prediction)
            .filter_by(equipment_id=equipment_id)
            .order_by(Prediction.created_at.desc())
            .first()
        )
