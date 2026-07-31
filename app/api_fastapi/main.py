"""FastAPI application: the public REST API for the HME Predictive Maintenance System.

This replaces the earlier Flask ``/api/v1`` blueprints. No business logic is
duplicated here — every endpoint delegates to the same service layer used by
the Flask web app (``PredictionService``, ``EquipmentService``, ...), each
call wrapped in a Flask application context so Flask-SQLAlchemy's session
works transparently from this separate ASGI process.

Run with: python run_api.py   (Swagger UI at http://127.0.0.1:8000/docs)
"""

from contextlib import contextmanager
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import RedirectResponse, Response
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError

from app import create_app
from app.api_fastapi.schemas import (
    EquipmentCreateRequest,
    EquipmentOverviewItem,
    FleetPredictionResponse,
    LoginRequest,
    LoginResponse,
    PredictionRequest,
    PredictionResponse,
)
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService
from app.services.equipment_service import EquipmentService
from app.services.ml.prediction_service import PredictionService

flask_app = create_app()

app = FastAPI(
    title="HME Predictive Maintenance API",
    description=(
        "API REST publique pour la prédiction de pannes des équipements miniers "
        "(Heavy Mobile Equipment). Authentification par JWT bearer token."
    ),
    version="2.0.0",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v2/auth/login")


@contextmanager
def flask_context() -> Iterator[None]:
    """Push the shared Flask app context so services can use db.session."""

    with flask_app.app_context():
        yield


def get_current_user_payload(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        return AuthService.decode_token(token)
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Redirect the bare root URL to the interactive Swagger docs."""

    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    """Silence the browser's automatic favicon request (no icon to serve)."""

    return Response(status_code=204)


@app.get("/health", tags=["System"])
def health() -> dict:
    return {"status": "ok", "service": "hme-predictive-maintenance-api", "version": "2.0.0"}


@app.post("/api/v2/auth/login", response_model=LoginResponse, tags=["Authentication"])
def login(payload: LoginRequest) -> LoginResponse:
    with flask_context():
        user = UserRepository().get_by_username(payload.username)
        if (
            user is None
            or not user.is_active
            or not AuthService.verify_password(payload.password, user.password_hash)
        ):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token = AuthService.generate_token(user)
        return LoginResponse(access_token=token, role=user.role.name)


@app.post("/api/v2/predict", response_model=PredictionResponse, tags=["Predictions"])
def predict(
    payload: PredictionRequest, _: dict = Depends(get_current_user_payload)
) -> PredictionResponse:
    with flask_context():
        try:
            result = PredictionService().predict_single(payload.model_dump())
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail="No active model registered") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return PredictionResponse(**result)


@app.post("/api/v2/predict/fleet", response_model=FleetPredictionResponse, tags=["Predictions"])
def predict_fleet(_: dict = Depends(get_current_user_payload)) -> FleetPredictionResponse:
    """Score every equipment's latest reading and rank the fleet by failure risk."""

    with flask_context():
        try:
            results = PredictionService().predict_fleet()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail="No active model registered") from exc
        return FleetPredictionResponse(scored_count=len(results), results=results)


@app.get("/api/v2/equipment", response_model=list[EquipmentOverviewItem], tags=["Equipment"])
def list_equipment(_: dict = Depends(get_current_user_payload)) -> list[dict]:
    with flask_context():
        return EquipmentService().list_equipment_overview()


@app.post("/api/v2/equipment", status_code=201, tags=["Equipment"])
def create_equipment(
    payload: EquipmentCreateRequest, _: dict = Depends(get_current_user_payload)
) -> dict:
    with flask_context():
        service = EquipmentService()
        if service.equipment_repo.get_by_code(payload.equipment_code) is not None:
            raise HTTPException(status_code=409, detail="Equipment already exists")
        equipment = service.create_equipment(
            payload.equipment_code, payload.equipment_type, payload.site
        )
        return {"id": equipment.id, "equipment_code": equipment.equipment_code}


@app.get("/api/v2/equipment/{equipment_code}", response_model=EquipmentOverviewItem, tags=["Equipment"])
def get_equipment(equipment_code: str, _: dict = Depends(get_current_user_payload)) -> dict:
    with flask_context():
        overview = EquipmentService().list_equipment_overview()
        for item in overview:
            if item["equipment_code"] == equipment_code:
                return item
        raise HTTPException(status_code=404, detail="Equipment not found")


@app.delete("/api/v2/equipment/{equipment_code}", status_code=204, tags=["Equipment"])
def delete_equipment(equipment_code: str, _: dict = Depends(get_current_user_payload)) -> None:
    with flask_context():
        service = EquipmentService()
        equipment = service.equipment_repo.get_by_code(equipment_code)
        if equipment is None:
            raise HTTPException(status_code=404, detail="Equipment not found")
        service.delete_equipment(equipment)
