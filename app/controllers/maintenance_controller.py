"""Maintenance record creation, attached to an equipment's detail page."""

from flask import Blueprint, abort, flash, redirect, request, url_for
from flask_login import login_required

from app.models import MaintenanceRecord, db
from app.repositories.equipment_repository import EquipmentRepository
from app.utils.constants import ROLE_ADMIN, ROLE_ENGINEER, ROLE_TECHNICIAN
from app.utils.decorators import roles_required

maintenance_bp = Blueprint("maintenance", __name__, url_prefix="/equipment")

_equipment_repo = EquipmentRepository()


@maintenance_bp.post("/<equipment_code>/maintenance")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER, ROLE_TECHNICIAN)
def create_maintenance(equipment_code: str):
    equipment = _equipment_repo.get_by_code(equipment_code)
    if equipment is None:
        abort(404)

    maintenance_type = request.form.get("maintenance_type", "Corrective")
    description = request.form.get("description", "").strip() or None
    downtime_hours = float(request.form.get("downtime_hours") or 0)
    cost = float(request.form.get("cost") or 0)

    db.session.add(
        MaintenanceRecord(
            equipment_id=equipment.id,
            maintenance_type=maintenance_type,
            description=description,
            performed_by=request.form.get("performed_by", "").strip() or None,
            downtime_hours=downtime_hours,
            cost=cost,
            status="Completed",
        )
    )
    db.session.commit()

    flash(f"Maintenance enregistrée pour {equipment_code}.", "success")
    return redirect(url_for("equipment.detail", equipment_code=equipment_code))
