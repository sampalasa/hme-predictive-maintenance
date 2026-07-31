"""Application configuration classes.

Values are sourced from environment variables (via a .env file loaded with
python-dotenv) so the same codebase can run in development, testing and
production without code changes.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


class Config:
    """Base configuration shared by all environments."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-not-for-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{(BASE_DIR / 'instance' / 'hme.db').as_posix()}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    RATELIMIT_STORAGE_URI = "memory://"

    DATASET_PATH = BASE_DIR / os.environ.get(
        "DATASET_PATH",
        "Datasets/Synthetic_Datasets_10_Master_Projects_10000Rows.xlsx",
    )
    DATASET_SHEET_NAME = os.environ.get("DATASET_SHEET_NAME", "1_HME_Downtime")

    ML_ARTIFACTS_DIR = BASE_DIR / os.environ.get("ML_ARTIFACTS_DIR", "app/ml/artifacts")
    OPTUNA_N_TRIALS = int(os.environ.get("OPTUNA_N_TRIALS", "30"))
    RANDOM_STATE = int(os.environ.get("RANDOM_STATE", "42"))

    LOGS_DIR = BASE_DIR / "logs"

    # Columns expected in the raw HME_Downtime dataset. Used by the data
    # loader to validate the source file before any processing happens.
    EXPECTED_COLUMNS = [
        "EquipmentID",
        "EquipmentType",
        "Timestamp",
        "OperatingHours",
        "EngineTemp",
        "HydraulicPressure",
        "Vibration",
        "FailureMode",
        "FailureWithin7Days",
    ]

    TARGET_COLUMN = "FailureWithin7Days"


class DevelopmentConfig(Config):
    """Local development configuration: verbose errors, auto-reload."""

    DEBUG = True


class TestingConfig(Config):
    """Configuration used by the automated test suite (isolated in-memory DB)."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration: debug disabled, secrets must be set via env."""

    DEBUG = False


_CONFIG_MAP = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(env_name: str | None = None) -> type[Config]:
    """Resolve a Config class from an environment name (defaults to FLASK_ENV)."""

    env_name = env_name or os.environ.get("FLASK_ENV", "development")
    return _CONFIG_MAP.get(env_name, DevelopmentConfig)
