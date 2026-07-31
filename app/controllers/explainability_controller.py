"""Explainable AI (XAI) pages: global SHAP importance and per-equipment explanations."""

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import login_required

from app.services.equipment_service import EquipmentService
from app.services.ml.explainability_service import ExplainabilityService

explainability_bp = Blueprint("explainability", __name__, url_prefix="/explainability")

_explainability_service = ExplainabilityService()
_equipment_service = EquipmentService()


@explainability_bp.get("")
@login_required
def index():
    equipment_list = _equipment_service.equipment_repo.get_all()
    try:
        global_explanation = _explainability_service.get_global_explanation()
    except FileNotFoundError:
        flash("Aucun modèle actif. Lancez d'abord l'entraînement du modèle.", "danger")
        return render_template(
            "explainability/index.html", global_explanation=None, equipment_list=equipment_list
        )

    return render_template(
        "explainability/index.html",
        global_explanation=global_explanation,
        equipment_list=equipment_list,
    )


@explainability_bp.get("/equipment/<equipment_code>")
@login_required
def equipment_explanation(equipment_code: str):
    try:
        explanation = _explainability_service.get_equipment_explanation(equipment_code)
    except FileNotFoundError:
        flash("Aucun modèle actif. Lancez d'abord l'entraînement du modèle.", "danger")
        return redirect(url_for("explainability.index"))

    if explanation is None:
        abort(404)

    return render_template("explainability/equipment.html", explanation=explanation)
