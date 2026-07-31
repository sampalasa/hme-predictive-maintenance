"""Blueprint registration.

The public REST API lives in the separate FastAPI service
(app/api_fastapi, served by run_api.py) — Flask only serves the web UI here.
"""

from flask import Flask


def register_blueprints(app: Flask) -> None:
    """Register all application blueprints on the given Flask app."""

    from app.controllers.admin_controller import admin_bp
    from app.controllers.auth_controller import auth_bp
    from app.controllers.dashboard_controller import dashboard_bp
    from app.controllers.eda_controller import eda_bp
    from app.controllers.equipment_controller import equipment_bp
    from app.controllers.evaluation_controller import evaluation_bp
    from app.controllers.explainability_controller import explainability_bp
    from app.controllers.feature_selection_controller import feature_selection_bp
    from app.controllers.health_controller import health_bp
    from app.controllers.maintenance_controller import maintenance_bp
    from app.controllers.prediction_web_controller import prediction_web_bp
    from app.controllers.reports_controller import reports_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(eda_bp)
    app.register_blueprint(equipment_bp)
    app.register_blueprint(evaluation_bp)
    app.register_blueprint(maintenance_bp)
    app.register_blueprint(prediction_web_bp)
    app.register_blueprint(explainability_bp)
    app.register_blueprint(feature_selection_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(admin_bp)
