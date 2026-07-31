"""SQLAlchemy models package.

``db`` is the single :class:`flask_sqlalchemy.SQLAlchemy` instance shared by
the whole application. It is defined here (before importing the individual
model modules) so those modules can safely do ``from app.models import db``
without triggering circular imports.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import order matters only for readability here: SQLAlchemy resolves
# string-based relationships lazily, so all modules just need to be
# imported once so their tables register on `db.metadata`.
from app.models.role import Role  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.equipment import Equipment  # noqa: E402,F401
from app.models.equipment_reading import EquipmentReading  # noqa: E402,F401
from app.models.model_version import ModelVersion  # noqa: E402,F401
from app.models.training_run import TrainingRun  # noqa: E402,F401
from app.models.prediction import Prediction  # noqa: E402,F401
from app.models.maintenance import MaintenanceRecord  # noqa: E402,F401
from app.models.report import Report  # noqa: E402,F401
from app.models.notification import Notification  # noqa: E402,F401
from app.models.audit_log import AuditLog  # noqa: E402,F401
from app.models.setting import Setting  # noqa: E402,F401

__all__ = [
    "db",
    "Role",
    "User",
    "Equipment",
    "EquipmentReading",
    "ModelVersion",
    "TrainingRun",
    "Prediction",
    "MaintenanceRecord",
    "Report",
    "Notification",
    "AuditLog",
    "Setting",
]
