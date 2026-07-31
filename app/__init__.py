"""Application factory for the HME Predictive Maintenance System."""

from flask import Flask, Response

from app.config import get_config
from app.extensions import csrf, limiter, login_manager
from app.models import User, db
from app.routes import register_blueprints
from app.utils.logger import get_logger

logger = get_logger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """Build and configure the Flask application instance."""

    app = Flask(__name__, static_folder="../static", template_folder="../templates")
    app.config.from_object(get_config(config_name))

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    @app.context_processor
    def inject_notifications() -> dict:
        from flask_login import current_user

        from app.services.notification_service import NotificationService

        if not current_user.is_authenticated:
            return {}

        notification_service = NotificationService()
        return {
            "unread_notifications_count": notification_service.count_unread(),
            "recent_notifications": notification_service.get_recent(limit=8),
        }

    @app.route("/favicon.ico")
    def favicon() -> Response:
        """The tab icon is served via <link rel="icon"> in base.html (data URI);
        this route just silences the browser's automatic /favicon.ico probe."""

        return Response(status=204)

    with app.app_context():
        db.create_all()

    register_blueprints(app)

    logger.info("Application created (config=%s)", config_name or "development")
    return app
