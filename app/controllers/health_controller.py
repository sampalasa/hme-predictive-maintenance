"""Health-check endpoint used to verify the application is running."""

from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health_check():
    """Return 200 OK with a minimal status payload."""

    return jsonify(status="ok", service="hme-predictive-maintenance"), 200
