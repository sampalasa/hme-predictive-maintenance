"""Integration tests for the FastAPI public REST API (app/api_fastapi)."""

from fastapi.testclient import TestClient

from app.api_fastapi.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_predict_requires_authentication():
    response = client.post(
        "/api/v2/predict",
        json={
            "EquipmentID": "EQ-057",
            "EquipmentType": "Excavator",
            "Timestamp": "2026-07-30T08:00:00",
            "OperatingHours": 13500,
            "EngineTemp": 95.0,
            "HydraulicPressure": 280.0,
            "Vibration": 4.5,
            "FailureMode": "Hydraulic",
        },
    )
    assert response.status_code == 401


def test_login_with_invalid_credentials_returns_401():
    response = client.post(
        "/api/v2/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401
