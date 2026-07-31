"""SHAP-based explainability for the active model.

Provides two views: a global ranking of the features that matter most across
the whole fleet, and a local, per-equipment explanation answering
"why does this machine look like it will fail?" in plain language.
"""

import json
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import shap

from app.models import Equipment, EquipmentReading, db
from app.repositories.model_version_repository import ModelVersionRepository
from app.services.data.feature_engineering_service import FeatureEngineeringService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ExplainabilityService:
    """Computes SHAP global feature importance and per-equipment local explanations."""

    def __init__(self) -> None:
        self.model_version_repo = ModelVersionRepository()
        self.feature_engineering = FeatureEngineeringService()

    def _load_model_and_features(self) -> tuple[Any, list[str], Any]:
        active_version = self.model_version_repo.get_active()
        if active_version is None:
            raise FileNotFoundError("No active model version registered.")

        model = joblib.load(active_version.file_path)
        feature_names = json.loads(Path(active_version.feature_list_path).read_text())["features"]
        return model, feature_names, active_version

    @staticmethod
    def _build_fleet_feature_matrix() -> pd.DataFrame:
        rows = (
            db.session.query(
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
        return pd.DataFrame(
            [
                {
                    "EquipmentID": r.equipment_code,
                    "EquipmentType": r.equipment_type,
                    "Timestamp": r.timestamp,
                    "OperatingHours": r.operating_hours,
                    "EngineTemp": r.engine_temp,
                    "HydraulicPressure": r.hydraulic_pressure,
                    "Vibration": r.vibration,
                    "FailureMode": r.failure_mode,
                    "FailureWithin7Days": r.failure_within_7_days,
                }
                for r in rows
            ]
        )

    @staticmethod
    def _shap_values_for_positive_class(explainer: "shap.TreeExplainer", X: pd.DataFrame) -> np.ndarray:
        raw = explainer.shap_values(X)
        if isinstance(raw, list):
            return raw[1]
        if isinstance(raw, np.ndarray) and raw.ndim == 3:
            return raw[:, :, 1]
        return raw

    def get_global_explanation(self, sample_size: int = 500) -> dict[str, Any]:
        """Mean |SHAP value| per feature over a fleet-wide sample (top 20)."""

        model, feature_names, _ = self._load_model_and_features()
        df = self._build_fleet_feature_matrix()
        enriched_df, _ = self.feature_engineering.engineer_features(df)

        sample = enriched_df.sample(min(sample_size, len(enriched_df)), random_state=42)
        X = sample.reindex(columns=feature_names, fill_value=0.0)

        explainer = shap.TreeExplainer(model)
        values = self._shap_values_for_positive_class(explainer, X)

        mean_abs_shap = np.abs(values).mean(axis=0)
        ranking = sorted(zip(feature_names, mean_abs_shap), key=lambda x: x[1], reverse=True)[:20]

        return {
            "sample_size": len(sample),
            "feature_importance": [
                {"feature": f, "importance": round(float(v), 5)} for f, v in ranking
            ],
        }

    def get_equipment_explanation(self, equipment_code: str) -> dict[str, Any] | None:
        """Local SHAP explanation + plain-language narrative for one equipment."""

        model, feature_names, _ = self._load_model_and_features()
        df = self._build_fleet_feature_matrix()
        if equipment_code not in df["EquipmentID"].values:
            return None

        enriched_df, _ = self.feature_engineering.engineer_features(df)
        equipment_rows = enriched_df[enriched_df["EquipmentID"] == equipment_code].sort_values("Timestamp")
        if equipment_rows.empty:
            return None

        latest_row = equipment_rows.iloc[[-1]]
        X = latest_row.reindex(columns=feature_names, fill_value=0.0)
        probability = float(model.predict_proba(X)[0, 1])

        explainer = shap.TreeExplainer(model)
        values = self._shap_values_for_positive_class(explainer, X)[0]

        base_value = explainer.expected_value
        if isinstance(base_value, (list, np.ndarray)):
            base_value = base_value[1] if len(np.atleast_1d(base_value)) > 1 else np.atleast_1d(base_value)[0]

        contributions = sorted(
            zip(feature_names, values, X.iloc[0].values), key=lambda item: abs(item[1]), reverse=True
        )[:10]

        top_positive = [c for c in contributions if c[1] > 0][:5]
        top_negative = [c for c in contributions if c[1] < 0][:5]

        return {
            "equipment_code": equipment_code,
            "probability": round(probability, 4),
            "base_value": round(float(base_value), 4),
            "contributions": [
                {"feature": f, "shap_value": round(float(v), 5), "feature_value": round(float(fv), 3)}
                for f, v, fv in contributions
            ],
            "narrative": self._build_narrative(equipment_code, probability, top_positive, top_negative),
        }

    @staticmethod
    def _build_narrative(
        equipment_code: str,
        probability: float,
        top_positive: list[tuple[str, float, float]],
        top_negative: list[tuple[str, float, float]],
    ) -> str:
        risk_pct = round(probability * 100, 1)
        lines = [
            f"L'équipement {equipment_code} a une probabilité de panne de {risk_pct}% "
            "dans les 7 prochains jours selon le modèle actif."
        ]
        if top_positive:
            factors = ", ".join(f"{f} ({v:+.3f})" for f, v, _ in top_positive[:3])
            lines.append(f"Facteurs qui AUGMENTENT le risque : {factors}.")
        if top_negative:
            factors = ", ".join(f"{f} ({v:+.3f})" for f, v, _ in top_negative[:3])
            lines.append(f"Facteurs qui RÉDUISENT le risque : {factors}.")

        confidence = "élevé" if abs(probability - 0.5) > 0.3 else "modéré"
        lines.append(f"Niveau de confiance du modèle : {confidence}.")

        if probability >= 0.6:
            lines.append(
                "Action recommandée : planifier une inspection préventive sous 7 jours "
                "et surveiller de près les capteurs en tête des facteurs de risque ci-dessus."
            )
        else:
            lines.append("Action recommandée : surveillance de routine, aucune intervention urgente.")

        return " ".join(lines)
