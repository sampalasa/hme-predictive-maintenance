"""Web dashboard controller: main KPI overview page."""

from flask import Blueprint, jsonify, render_template
from flask_login import login_required

from app.services.dashboard_service import DashboardService

dashboard_bp = Blueprint("dashboard", __name__)

_dashboard_service = DashboardService()


@dashboard_bp.get("/")
@login_required
def index():
    return render_template("dashboard/index.html")


@dashboard_bp.get("/dashboard/api/data")
@login_required
def data():
    return jsonify(_dashboard_service.get_full_dashboard_payload())
