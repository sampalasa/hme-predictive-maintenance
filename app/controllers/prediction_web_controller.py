"""Web pages for individual and batch (CSV) predictions."""

import io

import pandas as pd
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services.equipment_service import EquipmentService
from app.services.ml.prediction_service import PredictionService
from app.services.notification_service import NotificationService
from app.utils.constants import EQUIPMENT_TYPES
from app.utils.logger import get_logger

logger = get_logger(__name__)

prediction_web_bp = Blueprint("prediction_web", __name__, url_prefix="/predict")

_prediction_service = PredictionService()
_equipment_service = EquipmentService()
_notification_service = NotificationService()

_FAILURE_MODES = ["Engine", "Hydraulic", "Electrical", "Brake", "Transmission"]


@prediction_web_bp.get("")
@login_required
def predict_form():
    equipment_list = _equipment_service.equipment_repo.get_all()
    prefill_code = request.args.get("equipment_id", "")
    return render_template(
        "prediction/form.html",
        equipment_list=equipment_list,
        equipment_types=EQUIPMENT_TYPES,
        failure_modes=_FAILURE_MODES,
        prefill_code=prefill_code,
        result=None,
    )


@prediction_web_bp.post("")
@login_required
def handle_predict():
    equipment_list = _equipment_service.equipment_repo.get_all()

    payload = {
        "EquipmentID": request.form.get("equipment_id", "").strip(),
        "EquipmentType": request.form.get("equipment_type", "").strip(),
        "Timestamp": request.form.get("timestamp") or pd.Timestamp.now().isoformat(),
        "OperatingHours": request.form.get("operating_hours", 0),
        "EngineTemp": request.form.get("engine_temp", 0),
        "HydraulicPressure": request.form.get("hydraulic_pressure", 0),
        "Vibration": request.form.get("vibration", 0),
        "FailureMode": request.form.get("failure_mode", "Engine"),
    }

    try:
        result = _prediction_service.predict_single(payload)
        _notification_service.notify_critical_predictions(
            [
                {
                    "equipment_code": result["equipment_id"],
                    "equipment_type": payload["EquipmentType"],
                    "probability": result["probability"],
                    "risk_level": result["risk_level"],
                }
            ]
        )
    except FileNotFoundError:
        flash("Aucun modèle actif. Lancez d'abord l'entraînement du modèle.", "danger")
        return redirect(url_for("prediction_web.predict_form"))
    except (ValueError, TypeError) as exc:
        flash(f"Données invalides : {exc}", "danger")
        return redirect(url_for("prediction_web.predict_form"))

    return render_template(
        "prediction/form.html",
        equipment_list=equipment_list,
        equipment_types=EQUIPMENT_TYPES,
        failure_modes=_FAILURE_MODES,
        prefill_code=payload["EquipmentID"],
        result=result,
    )


@prediction_web_bp.get("/batch")
@login_required
def batch_form():
    return render_template("prediction/batch.html", results=None)


@prediction_web_bp.post("/batch")
@login_required
def handle_batch():
    uploaded_file = request.files.get("csv_file")
    if not uploaded_file or uploaded_file.filename == "":
        flash("Veuillez sélectionner un fichier CSV.", "danger")
        return redirect(url_for("prediction_web.batch_form"))

    try:
        df = pd.read_csv(io.StringIO(uploaded_file.stream.read().decode("utf-8")))
    except Exception as exc:
        flash(f"Impossible de lire le fichier CSV : {exc}", "danger")
        return redirect(url_for("prediction_web.batch_form"))

    results = []
    errors = 0
    for _, row in df.iterrows():
        try:
            result = _prediction_service.predict_single(row.to_dict())
            results.append(result)
        except Exception as exc:
            errors += 1
            logger.warning("Batch prediction row failed: %s", exc)

    if errors:
        flash(f"{errors} ligne(s) n'ont pas pu être traitées (voir logs).", "warning")

    results.sort(key=lambda r: r["probability"], reverse=True)
    return render_template("prediction/batch.html", results=results)
