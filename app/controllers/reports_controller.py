"""Report export pages: CSV, Excel and PDF downloads."""

import io
from pathlib import Path

from flask import Blueprint, abort, render_template, send_file, send_from_directory
from flask_login import current_user, login_required

from app.services.report_service import ReportService

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")

_report_service = ReportService()

_DOCS_EXPORTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "exports"
_DOC_NAMES = [
    "01_data_collection",
    "02_data_cleaning",
    "03_eda",
    "04_feature_engineering",
    "05_model_training",
    "06_model_evaluation",
    "07_explainability",
    "08_mlops",
]


@reports_bp.get("")
@login_required
def index():
    return render_template("reports/index.html", doc_names=_DOC_NAMES)


@reports_bp.get("/documentation/<path:filename>")
@login_required
def download_documentation(filename: str):
    if not (_DOCS_EXPORTS_DIR / filename).is_file():
        abort(404)
    return send_from_directory(_DOCS_EXPORTS_DIR, filename, as_attachment=True)


@reports_bp.get("/equipment.csv")
@login_required
def download_equipment_csv():
    content = _report_service.equipment_overview_csv()
    _report_service.log_report("Rapport équipements (CSV)", "CSV", "equipment.csv", current_user.id)
    return send_file(
        io.BytesIO(content), mimetype="text/csv", as_attachment=True, download_name="equipements.csv"
    )


@reports_bp.get("/predictions.xlsx")
@login_required
def download_predictions_excel():
    content = _report_service.predictions_excel()
    _report_service.log_report("Rapport prédictions (Excel)", "Excel", "predictions.xlsx", current_user.id)
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="predictions.xlsx",
    )


@reports_bp.get("/maintenance.csv")
@login_required
def download_maintenance_csv():
    content = _report_service.maintenance_csv()
    _report_service.log_report("Rapport maintenance (CSV)", "CSV", "maintenance.csv", current_user.id)
    return send_file(
        io.BytesIO(content), mimetype="text/csv", as_attachment=True, download_name="maintenance.csv"
    )


@reports_bp.get("/fleet-summary.pdf")
@login_required
def download_fleet_summary_pdf():
    content = _report_service.fleet_summary_pdf()
    _report_service.log_report("Rapport de synthèse flotte (PDF)", "PDF", "fleet-summary.pdf", current_user.id)
    return send_file(
        io.BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="rapport-synthese-flotte.pdf",
    )
