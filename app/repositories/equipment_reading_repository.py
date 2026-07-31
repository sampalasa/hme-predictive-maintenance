"""Repository for the EquipmentReading model."""

from app.models import EquipmentReading, db
from app.repositories.base_repository import BaseRepository


class EquipmentReadingRepository(BaseRepository[EquipmentReading]):
    """Data-access operations specific to EquipmentReading."""

    def __init__(self) -> None:
        super().__init__(EquipmentReading)

    def get_by_equipment(self, equipment_id: int) -> list[EquipmentReading]:
        return (
            db.session.query(EquipmentReading)
            .filter_by(equipment_id=equipment_id)
            .order_by(EquipmentReading.timestamp)
            .all()
        )
