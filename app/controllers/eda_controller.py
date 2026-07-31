"""Exploratory Data Analysis (EDA) page and PDF export."""

import io

from flask import Blueprint, jsonify, render_template, send_file
from flask_login import current_user, login_required

from app.services.eda_service import EdaService
from app.services.report_service import ReportService

eda_bp = Blueprint("eda", __name__, url_prefix="/eda")

_eda_service = EdaService()


@eda_bp.get("")
@login_required
def index():
    return render_template(
        "eda/index.html",
        overview=_eda_service.get_overview(),
        numeric_summary=_eda_service.get_numeric_summary(),
    )


@eda_bp.get("/api/figures")
@login_required
def api_figures():
    return jsonify(_eda_service.get_all_figures_json())


@eda_bp.get("/export.pdf")
@login_required
def export_pdf():
    content = _eda_service.export_pdf_report()
    ReportService.log_report("Rapport EDA (PDF)", "PDF", "eda-report.pdf", current_user.id)
    return send_file(
        io.BytesIO(content),
        mimetype="application/pdf",
        as_attachment=True,
        download_name="rapport-eda.pdf",
    )
