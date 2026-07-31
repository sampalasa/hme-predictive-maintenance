"""Integration tests for the AutoML training + model registry flow.

Uses a small synthetic dataframe (not the full 10k-row dataset) so the suite
stays fast: baseline comparison and one Optuna trial per model are enough to
exercise the whole path end-to-end.
"""

from app.models import ModelVersion, TrainingRun, db
from app.services.data.feature_engineering_service import FeatureEngineeringService
from app.services.ml.model_registry_service import ModelRegistryService
from app.services.ml.training_service import TrainingService


def test_baseline_comparison_returns_ranked_leaderboard(sample_raw_dataframe):
    df, feature_names = FeatureEngineeringService().engineer_features(sample_raw_dataframe)

    training_service = TrainingService(random_state=42)
    X_train, X_test, y_train, y_test = training_service.split_and_resample(
        df, feature_names, test_size=0.2
    )

    leaderboard, fitted_models = training_service.run_baseline_comparison(
        X_train, y_train, X_test, y_test
    )

    assert len(leaderboard) == 7
    assert set(fitted_models.keys()) == {m["model"] for m in leaderboard}

    scores = [m["composite_score"] for m in leaderboard]
    assert scores == sorted(scores, reverse=True)

    for metrics in leaderboard:
        for key in ("accuracy", "precision", "recall", "f1", "roc_auc", "balanced_accuracy", "mcc", "log_loss"):
            assert key in metrics


def test_model_registry_persists_model_version_and_training_run(app_context, sample_raw_dataframe, tmp_path):
    db.create_all()

    df, feature_names = FeatureEngineeringService().engineer_features(sample_raw_dataframe)
    training_service = TrainingService(random_state=42)
    X_train, X_test, y_train, y_test = training_service.split_and_resample(df, feature_names)

    leaderboard, fitted_models = training_service.run_baseline_comparison(
        X_train, y_train, X_test, y_test
    )
    best_entry = leaderboard[0]
    best_model = fitted_models[best_entry["model"]]

    registry = ModelRegistryService(artifacts_dir=tmp_path)
    metrics = {k: v for k, v in best_entry.items() if k != "model"}
    model_version = registry.register_best_model(
        model=best_model,
        model_name=best_entry["model"],
        metrics=metrics,
        hyperparameters={},
        feature_names=feature_names,
        leaderboard=leaderboard,
    )

    assert model_version.is_active is True
    assert db.session.get(ModelVersion, model_version.id) is not None
    assert db.session.query(TrainingRun).filter_by(model_version_id=model_version.id).count() == 1
