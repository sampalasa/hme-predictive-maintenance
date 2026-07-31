"""Model evaluation page: metrics, confusion matrix, ROC/PR/calibration/lift curves."""

from flask import Blueprint, flash, render_template
from flask_login import login_required

from app.services.ml.model_evaluation_service import ModelEvaluationService

evaluation_bp = Blueprint("evaluation", __name__, url_prefix="/evaluation")


@evaluation_bp.get("")
@login_required
def index():
    try:
        report = ModelEvaluationService().get_full_report()
    except FileNotFoundError:
        flash("Aucun modèle actif. Lancez d'abord l'entraînement du modèle.", "danger")
        return render_template("evaluation/index.html", report=None)

    return render_template("evaluation/index.html", report=report)
