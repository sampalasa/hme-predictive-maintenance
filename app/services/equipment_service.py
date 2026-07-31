"""Business logic for equipment listing, detail view and lifecycle."""

from typing import Any

from sqlalchemy import func

from app.models import Equipment, MaintenanceRecord, Prediction, db
from app.repositories.equipment_reading_repository import EquipmentReadingRepository
from app.repositories.equipment_repository import EquipmentRepository


class EquipmentService:
    """Aggregates equipment data (readings, latest prediction, maintenance)."""

    def __init__(self) -> None:
        self.equipment_repo = EquipmentRepository()
        self.reading_repo = EquipmentReadingRepository()

    def list_equipment_overview(self) -> list[dict[str, Any]]:
        """One row per equipment with its latest reading and latest prediction."""

        equipment_list = self.equipment_repo.get_all()
        overview = []

        for equipment in equipment_list:
            readings = self.reading_repo.get_by_equipment(equipment.id)
            last_reading = readings[-1] if readings else None

            latest_prediction = (
                db.session.query(Prediction)
                .filter_by(equipment_id=equipment.id)
                .order_by(Prediction.created_at.desc())
                .first()
            )

            overview.append(
                {
                    "id": equipment.id,
                    "equipment_code": equipment.equipment_code,
                    "equipment_type": equipment.equipment_type,
                    "status": equipment.status,
                    "site": equipment.site,
                    "reading_count": len(readings),
                    "last_operating_hours": last_reading.operating_hours if last_reading else None,
                    "last_reading_at": last_reading.timestamp.isoformat() if last_reading else None,
                    "risk_level": latest_prediction.risk_level if latest_prediction else None,
                    "probability": round(latest_prediction.probability, 4)
                    if latest_prediction
                    else None,
                }
            )

        return overview

    def get_equipment_detail(self, equipment_code: str) -> dict[str, Any] | None:
        equipment = self.equipment_repo.get_by_code(equipment_code)
        if equipment is None:
            return None

        readings = self.reading_repo.get_by_equipment(equipment.id)
        maintenance_records = (
            db.session.query(MaintenanceRecord)
            .filter_by(equipment_id=equipment.id)
            .order_by(MaintenanceRecord.performed_at.desc())
            .all()
        )
        predictions = (
            db.session.query(Prediction)
            .filter_by(equipment_id=equipment.id)
            .order_by(Prediction.created_at.desc())
            .limit(20)
            .all()
        )

        return {
            "equipment": equipment,
            "readings": readings,
            "maintenance_records": maintenance_records,
            "predictions": predictions,
        }

    def get_latest_predictions_ranked(self) -> list[dict[str, Any]]:
        """Most recent Prediction per equipment, ranked by failure probability (desc)."""

        latest_per_equipment = (
            db.session.query(
                Prediction.equipment_id, func.max(Prediction.created_at).label("max_created_at")
            )
            .group_by(Prediction.equipment_id)
            .subquery()
        )

        rows = (
            db.session.query(Prediction, Equipment.equipment_code, Equipment.equipment_type)
            .join(
                latest_per_equipment,
                (Prediction.equipment_id == latest_per_equipment.c.equipment_id)
                & (Prediction.created_at == latest_per_equipment.c.max_created_at),
            )
            .join(Equipment, Equipment.id == Prediction.equipment_id)
            .order_by(Prediction.probability.desc())
            .all()
        )

        return [
            {
                "equipment_code": code,
                "equipment_type": equipment_type,
                "probability": round(prediction.probability, 4),
                "risk_level": prediction.risk_level,
                "predicted_at": prediction.created_at.isoformat(),
            }
            for prediction, code, equipment_type in rows
        ]

    def create_equipment(self, equipment_code: str, equipment_type: str, site: str | None = None) -> Equipment:
        equipment = Equipment(equipment_code=equipment_code, equipment_type=equipment_type, site=site)
        db.session.add(equipment)
        db.session.commit()
        return equipment

    def update_equipment(
        self, equipment: Equipment, equipment_type: str, status: str, site: str | None
    ) -> Equipment:
        equipment.equipment_type = equipment_type
        equipment.status = status
        equipment.site = site
        db.session.commit()
        return equipment

    def delete_equipment(self, equipment: Equipment) -> None:
        db.session.delete(equipment)
        db.session.commit()
