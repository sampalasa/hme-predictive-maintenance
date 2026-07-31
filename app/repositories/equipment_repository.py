"""Repository for the Equipment model."""

from app.models import Equipment, db
from app.repositories.base_repository import BaseRepository


class EquipmentRepository(BaseRepository[Equipment]):
    """Data-access operations specific to Equipment."""

    def __init__(self) -> None:
        super().__init__(Equipment)

    def get_by_code(self, equipment_code: str) -> Equipment | None:
        return db.session.query(Equipment).filter_by(equipment_code=equipment_code).first()

    def get_or_create(self, equipment_code: str, equipment_type: str) -> Equipment:
        equipment = self.get_by_code(equipment_code)
        if equipment is not None:
            return equipment

        equipment = Equipment(equipment_code=equipment_code, equipment_type=equipment_type)
        db.session.add(equipment)
        db.session.flush()
        return equipment
