"""Shared pytest fixtures."""

import pandas as pd
import pytest

from app import create_app
from app.models import db


@pytest.fixture()
def app():
    flask_app = create_app("testing")
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_context(app):
    with app.app_context():
        yield
        db.session.remove()


@pytest.fixture()
def sample_raw_dataframe() -> pd.DataFrame:
    """A tiny synthetic dataframe matching the HME_Downtime schema."""

    equipment_types = ["Excavator", "Loader"]
    rows = []
    for eq_idx, eq_type in enumerate(equipment_types):
        equipment_id = f"EQ-{eq_idx:03d}"
        for i in range(20):
            rows.append(
                {
                    "EquipmentID": equipment_id,
                    "EquipmentType": eq_type,
                    "Timestamp": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i),
                    "OperatingHours": 1000 + i * 50,
                    "EngineTemp": 80.0 + i,
                    "HydraulicPressure": 250.0 + i * 2,
                    "Vibration": 3.0 + i * 0.1,
                    "FailureMode": "Hydraulic",
                    "FailureWithin7Days": 1 if i % 4 == 0 else 0,
                }
            )
    return pd.DataFrame(rows)
