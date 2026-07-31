"""Integration tests for session-based web authentication."""

import re

from app.models import Role, User, db
from app.services.auth_service import AuthService


def _create_user(username: str, password: str, role_name: str = "Admin") -> None:
    role = db.session.query(Role).filter_by(name=role_name).first()
    if role is None:
        role = Role(name=role_name)
        db.session.add(role)
        db.session.flush()

    db.session.add(
        User(
            username=username,
            email=f"{username}@hme-system.local",
            password_hash=AuthService.hash_password(password),
            role_id=role.id,
        )
    )
    db.session.commit()


def _extract_csrf_token(html_bytes: bytes) -> str:
    match = re.search(rb'name="csrf_token" type="hidden" value="([^"]+)"', html_bytes)
    assert match is not None, "CSRF token not found in login page"
    return match.group(1).decode()


def test_dashboard_redirects_anonymous_user_to_login(client):
    response = client.get("/", follow_redirects=True)

    assert response.status_code == 200
    assert response.request.path == "/login"


def test_login_with_valid_credentials_redirects_to_dashboard(app_context, client):
    _create_user("demo_user", "Demo@123")

    login_page = client.get("/login")
    csrf_token = _extract_csrf_token(login_page.data)

    response = client.post(
        "/login",
        data={"username": "demo_user", "password": "Demo@123", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert response.request.path == "/"


def test_login_with_invalid_password_shows_error(app_context, client):
    _create_user("demo_user2", "Demo@123")

    login_page = client.get("/login")
    csrf_token = _extract_csrf_token(login_page.data)

    response = client.post(
        "/login",
        data={"username": "demo_user2", "password": "WrongPassword", "csrf_token": csrf_token},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert response.request.path == "/login"
    assert b"Identifiants invalides" in response.data
