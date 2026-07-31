"""Administration panel: user management, audit log, settings, model history."""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.models import AuditLog, ModelVersion, Role, Setting, TrainingRun, User, db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.ml.drift_service import DriftService
from app.utils.constants import ALL_ROLES, ROLE_ADMIN
from app.utils.decorators import roles_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

_user_repo = UserRepository()


def _log_action(action: str, entity_type: str, entity_id: int | None, details: str = "") -> None:
    db.session.add(
        AuditLog(
            user_id=current_user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )
    db.session.commit()


@admin_bp.get("")
@login_required
@roles_required(ROLE_ADMIN)
def index():
    users = _user_repo.get_all()
    model_versions = (
        db.session.query(ModelVersion).order_by(ModelVersion.trained_at.desc()).limit(10).all()
    )
    return render_template("admin/index.html", users=users, roles=ALL_ROLES, model_versions=model_versions)


@admin_bp.post("/users/new")
@login_required
@roles_required(ROLE_ADMIN)
def create_user():
    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    role_name = request.form.get("role", "Technicien")
    full_name = request.form.get("full_name", "").strip() or None

    if not username or not email or not password:
        flash("Nom d'utilisateur, email et mot de passe sont obligatoires.", "danger")
        return redirect(url_for("admin.index"))

    if _user_repo.get_by_username(username) is not None:
        flash(f"L'utilisateur {username} existe déjà.", "danger")
        return redirect(url_for("admin.index"))

    role = db.session.query(Role).filter_by(name=role_name).first()
    user = User(
        username=username,
        email=email,
        password_hash=AuthService.hash_password(password),
        full_name=full_name,
        role_id=role.id,
    )
    db.session.add(user)
    db.session.commit()

    _log_action("create_user", "User", user.id, f"role={role_name}")
    flash(f"Utilisateur {username} créé.", "success")
    return redirect(url_for("admin.index"))


@admin_bp.post("/users/<int:user_id>/toggle-active")
@login_required
@roles_required(ROLE_ADMIN)
def toggle_user_active(user_id: int):
    user = db.session.get(User, user_id)
    if user is None:
        flash("Utilisateur introuvable.", "danger")
        return redirect(url_for("admin.index"))

    user.is_active = not user.is_active
    db.session.commit()

    _log_action("toggle_user_active", "User", user.id, f"is_active={user.is_active}")
    flash(f"Utilisateur {user.username} {'activé' if user.is_active else 'désactivé'}.", "info")
    return redirect(url_for("admin.index"))


@admin_bp.get("/logs")
@login_required
@roles_required(ROLE_ADMIN)
def logs():
    audit_logs = db.session.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return render_template("admin/logs.html", audit_logs=audit_logs)


@admin_bp.get("/settings")
@login_required
@roles_required(ROLE_ADMIN)
def settings():
    all_settings = db.session.query(Setting).order_by(Setting.key).all()
    return render_template("admin/settings.html", settings=all_settings)


@admin_bp.post("/settings")
@login_required
@roles_required(ROLE_ADMIN)
def update_setting():
    key = request.form.get("key", "").strip()
    value = request.form.get("value", "").strip()
    if not key:
        flash("La clé est obligatoire.", "danger")
        return redirect(url_for("admin.settings"))

    setting = db.session.query(Setting).filter_by(key=key).first()
    if setting is None:
        setting = Setting(key=key, value=value)
        db.session.add(setting)
    else:
        setting.value = value
    db.session.commit()

    _log_action("update_setting", "Setting", setting.id, f"{key}={value}")
    flash("Paramètre enregistré.", "success")
    return redirect(url_for("admin.settings"))


@admin_bp.get("/training-history")
@login_required
@roles_required(ROLE_ADMIN)
def training_history():
    runs = db.session.query(TrainingRun).order_by(TrainingRun.started_at.desc()).limit(20).all()
    return render_template("admin/training_history.html", runs=runs)


@admin_bp.get("/drift")
@login_required
@roles_required(ROLE_ADMIN)
def drift():
    report = DriftService().detect_drift()
    return render_template("admin/drift.html", report=report)
