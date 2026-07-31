"""Aggregates KPIs and chart-ready series for the operations dashboard.

All figures are computed live from the database (Equipment, EquipmentReading,
MaintenanceRecord, Prediction) — nothing here is hardcoded, so the dashboard
always reflects the current state of the seeded dataset.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func

from app.models import Equipment, EquipmentReading, MaintenanceRecord, Prediction, db
from app.utils.constants import (
    ENGINE_TEMP_CRITICAL_C,
    HYDRAULIC_PRESSURE_CRITICAL_BAR,
    VIBRATION_CRITICAL_MM_S,
)


class DashboardService:
    """Computes the KPIs and chart series shown on the main dashboard."""

    def get_summary_kpis(self) -> dict[str, Any]:
        total_equipment = db.session.query(func.count(Equipment.id)).scalar() or 0
        total_failures = (
            db.session.query(func.count(EquipmentReading.id))
            .filter(EquipmentReading.failure_within_7_days == 1)
            .scalar()
            or 0
        )

        period_start, period_end = db.session.query(
            func.min(EquipmentReading.timestamp), func.max(EquipmentReading.timestamp)
        ).first()
        period_hours = (
            max((period_end - period_start).total_seconds() / 3600.0, 1.0)
            if period_start and period_end
            else 1.0
        )

        fleet_exposure_hours = total_equipment * period_hours
        mtbf_hours = fleet_exposure_hours / total_failures if total_failures else 0.0

        mttr_hours = float(db.session.query(func.avg(MaintenanceRecord.downtime_hours)).scalar() or 0.0)
        total_downtime_hours = float(
            db.session.query(func.sum(MaintenanceRecord.downtime_hours)).scalar() or 0.0
        )
        availability_pct = (
            max(0.0, (fleet_exposure_hours - total_downtime_hours) / fleet_exposure_hours) * 100.0
            if fleet_exposure_hours
            else 0.0
        )

        today = datetime.now(timezone.utc).date()
        predictions_today = (
            db.session.query(func.count(Prediction.id))
            .filter(func.date(Prediction.created_at) == today)
            .scalar()
            or 0
        )

        return {
            "total_equipment": total_equipment,
            "total_failures": total_failures,
            "availability_pct": round(availability_pct, 2),
            "mtbf_hours": round(mtbf_hours, 1),
            "mttr_hours": round(mttr_hours, 1),
            "predictions_today": predictions_today,
            "critical_equipment": self._count_critical_equipment(),
        }

    @staticmethod
    def _count_critical_equipment() -> int:
        """Rule-based (non-ML) count of equipment whose latest reading breaches critical thresholds."""

        latest_reading_ids = db.session.query(func.max(EquipmentReading.id)).group_by(
            EquipmentReading.equipment_id
        )

        critical_count = (
            db.session.query(func.count(EquipmentReading.id))
            .filter(EquipmentReading.id.in_(latest_reading_ids))
            .filter(
                (EquipmentReading.engine_temp >= ENGINE_TEMP_CRITICAL_C)
                | (EquipmentReading.hydraulic_pressure >= HYDRAULIC_PRESSURE_CRITICAL_BAR)
                | (EquipmentReading.vibration >= VIBRATION_CRITICAL_MM_S)
            )
            .scalar()
        )
        return critical_count or 0

    @staticmethod
    def get_failures_by_type() -> list[dict[str, Any]]:
        rows = (
            db.session.query(Equipment.equipment_type, func.count(EquipmentReading.id))
            .join(EquipmentReading, EquipmentReading.equipment_id == Equipment.id)
            .filter(EquipmentReading.failure_within_7_days == 1)
            .group_by(Equipment.equipment_type)
            .order_by(func.count(EquipmentReading.id).desc())
            .all()
        )
        return [{"label": row[0], "count": row[1]} for row in rows]

    @staticmethod
    def get_top_critical_equipment(limit: int = 10) -> list[dict[str, Any]]:
        rows = (
            db.session.query(
                Equipment.equipment_code,
                Equipment.equipment_type,
                func.count(EquipmentReading.id).label("failures"),
            )
            .join(EquipmentReading, EquipmentReading.equipment_id == Equipment.id)
            .filter(EquipmentReading.failure_within_7_days == 1)
            .group_by(Equipment.id)
            .order_by(func.count(EquipmentReading.id).desc())
            .limit(limit)
            .all()
        )
        return [
            {"equipment_code": row[0], "equipment_type": row[1], "failures": row[2]} for row in rows
        ]

    @staticmethod
    def get_monthly_evolution() -> list[dict[str, Any]]:
        month_expr = func.strftime("%Y-%m", EquipmentReading.timestamp)
        rows = (
            db.session.query(month_expr.label("month"), func.count(EquipmentReading.id))
            .filter(EquipmentReading.failure_within_7_days == 1)
            .group_by("month")
            .order_by("month")
            .all()
        )
        return [{"month": row[0], "count": row[1]} for row in rows]

    @staticmethod
    def get_recent_predictions(limit: int = 8) -> list[dict[str, Any]]:
        rows = (
            db.session.query(Prediction, Equipment.equipment_code)
            .join(Equipment, Equipment.id == Prediction.equipment_id)
            .order_by(Prediction.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "equipment_code": code,
                "probability": round(prediction.probability, 3),
                "risk_level": prediction.risk_level,
                "created_at": prediction.created_at.isoformat(),
            }
            for prediction, code in rows
        ]

    @staticmethod
    def get_recent_maintenance(limit: int = 8) -> list[dict[str, Any]]:
        rows = (
            db.session.query(MaintenanceRecord, Equipment.equipment_code)
            .join(Equipment, Equipment.id == MaintenanceRecord.equipment_id)
            .order_by(MaintenanceRecord.performed_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "equipment_code": code,
                "maintenance_type": record.maintenance_type,
                "downtime_hours": record.downtime_hours,
                "performed_at": record.performed_at.isoformat(),
                "performed_by": record.performed_by,
            }
            for record, code in rows
        ]

    def get_full_dashboard_payload(self) -> dict[str, Any]:
        return {
            "kpis": self.get_summary_kpis(),
            "failures_by_type": self.get_failures_by_type(),
            "top_critical_equipment": self.get_top_critical_equipment(),
            "monthly_evolution": self.get_monthly_evolution(),
            "recent_predictions": self.get_recent_predictions(),
            "recent_maintenance": self.get_recent_maintenance(),
        }
