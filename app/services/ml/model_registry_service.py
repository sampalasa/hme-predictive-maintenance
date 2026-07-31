"""Persists the winning AutoML model and registers it in the database.

A model is only usable by ``PredictionService`` once it has gone through
this registry: the raw joblib artifact alone is not enough, since the
feature list and metrics need to travel with it for traceability and for
train/serve consistency.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib

from app.config.settings import Config
from app.models import ModelVersion, TrainingRun, db
from app.repositories.model_version_repository import ModelVersionRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelRegistryService:
    """Saves model artifacts to disk and records them in the database."""

    def __init__(self, artifacts_dir: Path | None = None) -> None:
        self.artifacts_dir = Path(artifacts_dir or Config.ML_ARTIFACTS_DIR)
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.model_version_repo = ModelVersionRepository()

    def register_best_model(
        self,
        model: Any,
        model_name: str,
        metrics: dict[str, float],
        hyperparameters: dict[str, Any],
        feature_names: list[str],
        leaderboard: list[dict[str, Any]],
        notes: str | None = None,
    ) -> ModelVersion:
        """Save the model + feature list to disk and mark it as the active version."""

        version_number = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

        model_path = self.artifacts_dir / f"{model_name}_{version_number}.joblib"
        feature_list_path = self.artifacts_dir / f"{model_name}_{version_number}_features.json"

        joblib.dump(model, model_path)
        feature_list_path.write_text(json.dumps({"features": feature_names}, indent=2))

        self.model_version_repo.deactivate_all()

        model_version = ModelVersion(
            name=model_name,
            algorithm=model_name,
            version_number=version_number,
            file_path=str(model_path),
            feature_list_path=str(feature_list_path),
            metrics_json=json.dumps(metrics),
            hyperparameters_json=json.dumps(hyperparameters),
            is_active=True,
        )
        db.session.add(model_version)
        db.session.flush()

        training_run = TrainingRun(
            model_version_id=model_version.id,
            status="completed",
            leaderboard_json=json.dumps(leaderboard),
            notes=notes,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(training_run)
        db.session.commit()

        logger.info("Registered new active model: %s v%s (%s)", model_name, version_number, model_path.name)
        return model_version
