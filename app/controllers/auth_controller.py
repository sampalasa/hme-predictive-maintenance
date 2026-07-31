"""Web authentication controller: session-based login/logout (Flask-Login)."""

from datetime import datetime, timezone

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user

from app.extensions import limiter
from app.models import db
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.utils.forms import LoginForm
from app.utils.logger import get_logger

logger = get_logger(__name__)

auth_bp = Blueprint("auth", __name__)

_user_repo = UserRepository()


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = _user_repo.get_by_username(form.username.data.strip())

        if (
            user is None
            or not user.is_active
            or not AuthService.verify_password(form.password.data, user.password_hash)
        ):
            flash("Identifiants invalides.", "danger")
            logger.warning("Failed login attempt for username=%s", form.username.data)
            return render_template("auth/login.html", form=form)

        login_user(user, remember=form.remember_me.data)
        user.last_login_at = datetime.now(timezone.utc)
        db.session.commit()

        logger.info("User %s logged in", user.username)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("dashboard.index"))

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Vous avez été déconnecté.", "info")
    return redirect(url_for("auth.login"))
