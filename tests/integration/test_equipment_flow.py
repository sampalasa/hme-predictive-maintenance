"""Integration tests for equipment CRUD and CSRF-protected POST forms.

Guards against the CSRF-token-missing regression found during manual QA:
every hand-written HTML form (not a FlaskForm) must carry an explicit
`csrf_token` hidden input, otherwise Flask-WTF's CSRFProtect rejects the
POST with 400 before the view function ever runs.
"""

import re

from app.models import Equipment, Role, User, db
from app.services.auth_service import AuthService


def _login_as_admin(client) -> None:
    role = Role(name="Admin")
    db.session.add(role)
    db.session.flush()
    db.session.add(
        User(
            username="qa_admin",
            email="qa_admin@hme-system.local",
            password_hash=AuthService.hash_password("Qa@12345"),
            role_id=role.id,
        )
    )
    db.session.commit()

    login_page = client.get("/login")
    csrf_token = re.search(rb'name="csrf_token" type="hidden" value="([^"]+)"', login_page.data).group(1).decode()
    client.post(
        "/login",
        data={"username": "qa_admin", "password": "Qa@12345", "csrf_token": csrf_token},
        follow_redirects=True,
    )


def _extract_csrf(html_bytes: bytes) -> str:
    match = re.search(rb'name="csrf_token"[^>]*value="([^"]+)"', html_bytes)
    assert match is not None, "CSRF token input not found on the page"
    return match.group(1).decode()


def test_create_equipment_via_form_succeeds(app_context, client):
    _login_as_admin(client)

    form_page = client.get("/equipment/new")
    csrf_token = _extract_csrf(form_page.data)

    response = client.post(
        "/equipment/new",
        data={
            "equipment_code": "EQ-QA-001",
            "equipment_type": "Loader",
            "site": "Test Site",
            "csrf_token": csrf_token,
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert response.request.path == "/equipment"
    assert db.session.query(Equipment).filter_by(equipment_code="EQ-QA-001").first() is not None


def test_create_equipment_without_csrf_token_is_rejected(app_context, client):
    _login_as_admin(client)

    response = client.post(
        "/equipment/new",
        data={"equipment_code": "EQ-QA-002", "equipment_type": "Loader"},
    )

    assert response.status_code == 400
