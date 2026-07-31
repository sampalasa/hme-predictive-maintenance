"""Equipment management: list, detail, at-risk ranking, CRUD, fleet prediction."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import limiter
from app.services.equipment_service import EquipmentService
from app.services.ml.prediction_service import PredictionService
from app.services.notification_service import NotificationService
from app.utils.constants import ROLE_ADMIN, ROLE_ENGINEER
from app.utils.decorators import roles_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

equipment_bp = Blueprint("equipment", __name__, url_prefix="/equipment")

_equipment_service = EquipmentService()
_prediction_service = PredictionService()
_notification_service = NotificationService()


@equipment_bp.get("")
@login_required
def list_equipment():
    overview = _equipment_service.list_equipment_overview()
    return render_template("equipment/list.html", equipment_list=overview)


@equipment_bp.get("/at-risk")
@login_required
def at_risk():
    ranked = _equipment_service.get_latest_predictions_ranked()
    return render_template("equipment/at_risk.html", ranked=ranked)


@equipment_bp.post("/predict-fleet")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER)
@limiter.limit("5 per minute")
def predict_fleet():
    try:
        results = _prediction_service.predict_fleet()
    except FileNotFoundError:
        flash("Aucun modèle actif. Lancez d'abord l'entraînement (python -m app.ml.training.train_pipeline).", "danger")
        return redirect(url_for("equipment.at_risk"))

    critical_count = _notification_service.notify_critical_predictions(results)

    flash(
        f"Prédiction lancée sur {len(results)} équipement(s). "
        f"{critical_count} alerte(s) critique(s) générée(s).",
        "success",
    )
    return redirect(url_for("equipment.at_risk"))


@equipment_bp.get("/new")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER)
def new_equipment_form():
    return render_template("equipment/form.html", equipment=None)


@equipment_bp.post("/new")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER)
def create_equipment():
    equipment_code = request.form.get("equipment_code", "").strip()
    equipment_type = request.form.get("equipment_type", "").strip()
    site = request.form.get("site", "").strip() or None

    if not equipment_code or not equipment_type:
        flash("Le code et le type d'équipement sont obligatoires.", "danger")
        return redirect(url_for("equipment.new_equipment_form"))

    if _equipment_service.equipment_repo.get_by_code(equipment_code) is not None:
        flash(f"L'équipement {equipment_code} existe déjà.", "danger")
        return redirect(url_for("equipment.new_equipment_form"))

    _equipment_service.create_equipment(equipment_code, equipment_type, site)
    flash(f"Équipement {equipment_code} créé.", "success")
    return redirect(url_for("equipment.list_equipment"))


@equipment_bp.get("/<equipment_code>")
@login_required
def detail(equipment_code: str):
    detail_data = _equipment_service.get_equipment_detail(equipment_code)
    if detail_data is None:
        abort(404)
    return render_template("equipment/detail.html", **detail_data)


@equipment_bp.get("/<equipment_code>/edit")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER)
def edit_equipment_form(equipment_code: str):
    equipment = _equipment_service.equipment_repo.get_by_code(equipment_code)
    if equipment is None:
        abort(404)
    return render_template("equipment/form.html", equipment=equipment)


@equipment_bp.post("/<equipment_code>/edit")
@login_required
@roles_required(ROLE_ADMIN, ROLE_ENGINEER)
def update_equipment(equipment_code: str):
    equipment = _equipment_service.equipment_repo.get_by_code(equipment_code)
    if equipment is None:
        abort(404)

    equipment_type = request.form.get("equipment_type", "").strip()
    status = request.form.get("status", "Operational").strip()
    site = request.form.get("site", "").strip() or None

    _equipment_service.update_equipment(equipment, equipment_type, status, site)
    flash(f"Équipement {equipment_code} mis à jour.", "success")
    return redirect(url_for("equipment.detail", equipment_code=equipment_code))


@equipment_bp.post("/<equipment_code>/delete")
@login_required
@roles_required(ROLE_ADMIN)
def delete_equipment(equipment_code: str):
    equipment = _equipment_service.equipment_repo.get_by_code(equipment_code)
    if equipment is None:
        abort(404)

    _equipment_service.delete_equipment(equipment)
    flash(f"Équipement {equipment_code} supprimé.", "info")
    return redirect(url_for("equipment.list_equipment"))
