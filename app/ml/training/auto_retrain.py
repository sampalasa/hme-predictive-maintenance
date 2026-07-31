"""Drift-triggered automatic retraining.

Run with:
    python -m app.ml.training.auto_retrain

Checks for data drift (PSI/KS-test) between older and recent equipment
readings. If drift is detected, re-runs the full AutoML training pipeline
and registers the new model as active. Intended to be scheduled with the
OS's own scheduler (cron / Windows Task Scheduler) — see docs/08_mlops.md for
why this replaces a full Airflow DAG in this project.
"""

from app import create_app
from app.ml.training.train_pipeline import run as run_training_pipeline
from app.services.ml.drift_service import DriftService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run() -> dict:
    app = create_app()
    with app.app_context():
        drift_report = DriftService().detect_drift()
        logger.info("Drift check result: %s", drift_report["status"])

        if drift_report["status"] != "drift_detected":
            logger.info("No significant drift detected — skipping retraining.")
            return {"retrained": False, "drift_report": drift_report}

        drifted_features = [f["feature"] for f in drift_report["features"] if f["drift_detected"]]
        logger.warning("Drift detected on: %s — triggering retraining.", drifted_features)

    training_result = run_training_pipeline()
    logger.info(
        "Retraining complete. New active model: %s", training_result["best_entry"]["model"]
    )
    return {"retrained": True, "drift_report": drift_report, "training_result": training_result}


if __name__ == "__main__":
    run()
