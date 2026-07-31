"""Pydantic request/response schemas for the FastAPI service."""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str


class PredictionRequest(BaseModel):
    EquipmentID: str = Field(examples=["EQ-057"])
    EquipmentType: str = Field(examples=["Excavator"])
    Timestamp: str = Field(examples=["2026-07-30T08:00:00"])
    OperatingHours: int = Field(examples=[13500])
    EngineTemp: float = Field(examples=[95.0])
    HydraulicPressure: float = Field(examples=[280.0])
    Vibration: float = Field(examples=[4.5])
    FailureMode: str = Field(examples=["Hydraulic"])


class PredictionResponse(BaseModel):
    equipment_id: str
    probability: float
    predicted_label: int
    risk_level: str
    model_version: str


class FleetPredictionItem(BaseModel):
    equipment_code: str
    equipment_type: str
    probability: float
    predicted_label: int
    risk_level: str
    last_reading_at: str


class FleetPredictionResponse(BaseModel):
    scored_count: int
    results: list[FleetPredictionItem]


class EquipmentOverviewItem(BaseModel):
    id: int
    equipment_code: str
    equipment_type: str
    status: str
    site: str | None = None
    reading_count: int
    last_operating_hours: int | None = None
    last_reading_at: str | None = None
    risk_level: str | None = None
    probability: float | None = None


class EquipmentCreateRequest(BaseModel):
    equipment_code: str
    equipment_type: str
    site: str | None = None
