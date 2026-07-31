"""Runs the currently active model against a single equipment reading.

Because several engineered features are computed per equipment (rolling
means, lags, trend slopes), a lone new reading is combined with that
equipment's historical readings (if any exist in the database) before
feature engineering runs, then only the resulting last row is used for
inference. This keeps train/serve feature computation identical.
"""

import json
from pathlib import Path
from typing import Any

import joblib
import pandas as pd

from app.models import Equipment, EquipmentReading, ModelVersion, Prediction, db
from app.repositories.equipment_reading_repository import EquipmentReadingRepository
from app.repositories.equipment_repository import EquipmentRepository
from app.repositories.model_version_repository import ModelVersionRepository
from app.repositories.prediction_repository import PredictionRepository
from app.services.data.feature_engineering_service import FeatureEngineeringService
from app.utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_INPUT_FIELDS = [
    "EquipmentID",
    "EquipmentType",
    "Timestamp",
    "OperatingHours",
    "EngineTemp",
    "HydraulicPressure",
    "Vibration",
    "FailureMode",
]


class PredictionService:
    """Loads the active model version and predicts failure risk for one reading."""

    def __init__(self) -> None:
        self.model_version_repo = ModelVersionRepository()
        self.equipment_repo = EquipmentRepository()
        self.reading_repo = EquipmentReadingRepository()
        self.prediction_repo = PredictionRepository()
        self.feature_engineering = FeatureEngineeringService()

    def _load_active_model(self) -> tuple[Any, list[str], ModelVersion]:
        active_version = self.model_version_repo.get_active()
        if active_version is None:
            raise FileNotFoundError("No active model version registered.")

        model = joblib.load(active_version.file_path)
        feature_names = json.loads(Path(active_version.feature_list_path).read_text())["features"]
        return model, feature_names, active_version

    def predict_single(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_payload(payload)

        model, feature_names, active_version = self._load_active_model()

        input_df = self._build_input_frame(payload)
        enriched_df, _ = self.feature_engineering.engineer_features(input_df)
        latest_row = enriched_df.iloc[[-1]]

        X = latest_row.reindex(columns=feature_names, fill_value=0.0)
        probability = float(model.predict_proba(X)[0, 1])
        predicted_label = int(probability >= 0.5)
        risk_level = self._risk_level(probability)

        self._persist_prediction(payload, active_version.id, probability, predicted_label, risk_level)

        return {
            "equipment_id": payload["EquipmentID"],
            "probability": round(probability, 4),
            "predicted_label": predicted_label,
            "risk_level": risk_level,
            "model_version": f"{active_version.name} v{active_version.version_number}",
        }

    def predict_fleet(self) -> list[dict[str, Any]]:
        """Score every equipment's most recent reading and rank them by failure risk.

        Feature engineering runs once over the whole fleet's reading history
        (not equipment-by-equipment) so that population-level features
        (per-type z-scores, age percentiles, ...) match how the model was
        trained, then only the latest row per equipment is scored.
        """

        model, feature_names, active_version = self._load_active_model()

        rows = (
            db.session.query(
                Equipment.id.label("equipment_pk"),
                Equipment.equipment_code,
                Equipment.equipment_type,
                EquipmentReading.timestamp,
                EquipmentReading.operating_hours,
                EquipmentReading.engine_temp,
                EquipmentReading.hydraulic_pressure,
                EquipmentReading.vibration,
                EquipmentReading.failure_mode,
                EquipmentReading.failure_within_7_days,
            )
            .join(EquipmentReading, EquipmentReading.equipment_id == Equipment.id)
            .all()
        )
        if not rows:
            return []

        df = pd.DataFrame(
            [
                {
                    "EquipmentPk": row.equipment_pk,
                    "EquipmentID": row.equipment_code,
                    "EquipmentType": row.equipment_type,
                    "Timestamp": row.timestamp,
                    "OperatingHours": row.operating_hours,
                    "EngineTemp": row.engine_temp,
                    "HydraulicPressure": row.hydraulic_pressure,
                    "Vibration": row.vibration,
                    "FailureMode": row.failure_mode,
                    "FailureWithin7Days": row.failure_within_7_days,
                }
                for row in rows
            ]
        )

        enriched_df, _ = self.feature_engineering.engineer_features(df)
        latest_per_equipment = enriched_df.sort_values("Timestamp").groupby("EquipmentID").tail(1)

        X = latest_per_equipment.reindex(columns=feature_names, fill_value=0.0)
        probabilities = model.predict_proba(X)[:, 1]

        results: list[dict[str, Any]] = []
        predictions_to_persist: list[Prediction] = []

        for (_, row), probability in zip(latest_per_equipment.iterrows(), probabilities):
            probability = float(probability)
            predicted_label = int(probability >= 0.5)
            risk_level = self._risk_level(probability)

            results.append(
                {
                    "equipment_code": row["EquipmentID"],
                    "equipment_type": row["EquipmentType"],
                    "probability": round(probability, 4),
                    "predicted_label": predicted_label,
                    "risk_level": risk_level,
                    "last_reading_at": row["Timestamp"].isoformat(),
                }
            )
            predictions_to_persist.append(
                Prediction(
                    equipment_id=int(row["EquipmentPk"]),
                    model_version_id=active_version.id,
                    probability=probability,
                    predicted_label=predicted_label,
                    risk_level=risk_level,
                    input_features_json=json.dumps({"source": "fleet_batch_prediction"}),
                )
            )

        db.session.add_all(predictions_to_persist)
        db.session.commit()

        results.sort(key=lambda r: r["probability"], reverse=True)
        logger.info("Fleet-wide prediction: scored %d equipment(s)", len(results))
        return results

    @staticmethod
    def _validate_payload(payload: dict[str, Any]) -> None:
        missing = [f for f in _REQUIRED_INPUT_FIELDS if f not in payload]
        if missing:
            raise ValueError(f"Missing required field(s): {missing}")

    def _build_input_frame(self, payload: dict[str, Any]) -> pd.DataFrame:
        new_row = {
            "EquipmentID": str(payload["EquipmentID"]),
            "EquipmentType": str(payload["EquipmentType"]),
            "Timestamp": pd.to_datetime(payload["Timestamp"]),
            "OperatingHours": int(payload["OperatingHours"]),
            "EngineTemp": float(payload["EngineTemp"]),
            "HydraulicPressure": float(payload["HydraulicPressure"]),
            "Vibration": float(payload["Vibration"]),
            "FailureMode": str(payload["FailureMode"]),
            "FailureWithin7Days": 0,
        }

        equipment = self.equipment_repo.get_by_code(new_row["EquipmentID"])
        history_rows: list[dict[str, Any]] = []
        if equipment is not None:
            for reading in self.reading_repo.get_by_equipment(equipment.id):
                history_rows.append(
                    {
                        "EquipmentID": new_row["EquipmentID"],
                        "EquipmentType": equipment.equipment_type,
                        "Timestamp": reading.timestamp,
                        "OperatingHours": reading.operating_hours,
                        "EngineTemp": reading.engine_temp,
                        "HydraulicPressure": reading.hydraulic_pressure,
                        "Vibration": reading.vibration,
                        "FailureMode": reading.failure_mode,
                        "FailureWithin7Days": reading.failure_within_7_days,
                    }
                )

        all_rows = history_rows + [new_row]
        df = pd.DataFrame(all_rows)
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        return df

    @staticmethod
    def _risk_level(probability: float) -> str:
        if probability >= 0.85:
            return "Critical"
        if probability >= 0.6:
            return "High"
        if probability >= 0.3:
            return "Medium"
        return "Low"

    def _persist_prediction(
        self,
        payload: dict[str, Any],
        model_version_id: int,
        probability: float,
        predicted_label: int,
        risk_level: str,
    ) -> None:
        equipment = self.equipment_repo.get_or_create(
            equipment_code=str(payload["EquipmentID"]), equipment_type=str(payload["EquipmentType"])
        )

        prediction = Prediction(
            equipment_id=equipment.id,
            model_version_id=model_version_id,
            probability=probability,
            predicted_label=predicted_label,
            risk_level=risk_level,
            input_features_json=json.dumps(payload, default=str),
        )
        db.session.add(prediction)
        db.session.commit()
