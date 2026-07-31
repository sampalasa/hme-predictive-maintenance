"""Advanced evaluation of the active model: curves and extended metrics.

Rebuilds the same train/test split used by the training pipeline (same
random_state) so the test set here matches what the model was actually
scored on when it was selected, then derives confusion matrix, ROC/PR
curves, calibration, lift/gain, and a learning curve.
"""

from typing import Any

import numpy as np
from sklearn.calibration import calibration_curve
from sklearn.metrics import cohen_kappa_score, confusion_matrix, precision_recall_curve, roc_curve
from sklearn.model_selection import learning_curve

from app.repositories.model_version_repository import ModelVersionRepository
from app.services.ml.model_factory import build_model
from app.services.ml.training_service import TrainingService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelEvaluationService:
    """Computes evaluation curves/metrics for the currently active model."""

    def __init__(self) -> None:
        self.model_version_repo = ModelVersionRepository()
        self.training_service = TrainingService()

    def _load_active_model_and_test_split(self):
        active_version = self.model_version_repo.get_active()
        if active_version is None:
            raise FileNotFoundError("No active model version registered.")

        import joblib

        model = joblib.load(active_version.file_path)

        df, feature_names = self.training_service.prepare_dataset()
        X_train, X_test, y_train, y_test = self.training_service.split_and_resample(df, feature_names)
        return model, active_version, X_train, X_test, y_train, y_test

    def get_full_report(self) -> dict[str, Any]:
        model, active_version, X_train, X_test, y_train, y_test = (
            self._load_active_model_and_test_split()
        )

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        metrics = self.training_service.evaluate(model, X_test, y_test)
        metrics["cohen_kappa"] = round(float(cohen_kappa_score(y_test, y_pred)), 4)

        cm = confusion_matrix(y_test, y_pred).tolist()

        fpr, tpr, _ = roc_curve(y_test, y_proba)
        precision, recall, _ = precision_recall_curve(y_test, y_proba)
        prob_true, prob_pred = calibration_curve(y_test, y_proba, n_bins=10)

        lift_gain = self._compute_lift_gain(y_test.to_numpy(), y_proba)
        learning_curve_data = self._compute_learning_curve(
            active_version.algorithm, X_train, y_train
        )

        return {
            "model_name": f"{active_version.name} v{active_version.version_number}",
            "metrics": {k: round(float(v), 4) for k, v in metrics.items()},
            "confusion_matrix": cm,
            "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist()},
            "pr_curve": {"precision": precision.tolist(), "recall": recall.tolist()},
            "calibration_curve": {"prob_true": prob_true.tolist(), "prob_pred": prob_pred.tolist()},
            "lift_gain": lift_gain,
            "learning_curve": learning_curve_data,
        }

    @staticmethod
    def _compute_lift_gain(y_true: np.ndarray, y_proba: np.ndarray, n_bins: int = 10) -> dict[str, Any]:
        order = np.argsort(-y_proba)
        y_sorted = y_true[order]
        total_positives = y_sorted.sum()
        n = len(y_sorted)

        bin_size = max(1, n // n_bins)
        deciles, gains, lifts = [], [], []
        cumulative_positive = 0
        baseline_rate = total_positives / n if n else 0.0

        for i in range(1, n_bins + 1):
            end = min(i * bin_size, n)
            cumulative_positive = y_sorted[:end].sum()
            population_pct = end / n * 100
            gain_pct = (cumulative_positive / total_positives * 100) if total_positives else 0.0
            lift = (cumulative_positive / end) / baseline_rate if baseline_rate and end else 0.0

            deciles.append(round(population_pct, 1))
            gains.append(round(float(gain_pct), 2))
            lifts.append(round(float(lift), 3))

        return {"population_pct": deciles, "gain_pct": gains, "lift": lifts}

    @staticmethod
    def _compute_learning_curve(algorithm: str, X_train, y_train) -> dict[str, Any]:
        """Learning curve using a fresh default-hyperparameter model of the same family.

        Re-using the exact tuned hyperparameters would make this slower without
        changing the qualitative bias/variance story the curve is meant to show,
        so a default-configuration model of the same algorithm is used instead.
        """

        try:
            model = build_model(algorithm, random_state=42)
            train_sizes, train_scores, test_scores = learning_curve(
                model,
                X_train,
                y_train,
                cv=3,
                train_sizes=np.linspace(0.2, 1.0, 5),
                scoring="f1",
                n_jobs=1,
            )
            return {
                "train_sizes": train_sizes.tolist(),
                "train_scores_mean": train_scores.mean(axis=1).tolist(),
                "test_scores_mean": test_scores.mean(axis=1).tolist(),
            }
        except Exception as exc:  # pragma: no cover - defensive, evaluation page must not crash
            logger.warning("Learning curve computation failed: %s", exc)
            return {"train_sizes": [], "train_scores_mean": [], "test_scores_mean": []}
