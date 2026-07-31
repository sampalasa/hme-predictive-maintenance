"""Executable AutoML training pipeline.

Run with:
    python -m app.ml.training.train_pipeline

Steps: load + clean + feature-engineer the HME_Downtime dataset, split and
SMOTE-resample, compare 7 model families with default hyperparameters,
tune the top 3 candidates with Optuna, select the best model by a composite
F1/ROC-AUC score, and register it as the active model version.
"""

from sklearn.feature_selection import mutual_info_classif

from app import create_app
from app.config.settings import Config
from app.services.ml.model_factory import build_model
from app.services.ml.model_registry_service import ModelRegistryService
from app.services.ml.optuna_tuner import tune_model
from app.services.ml.training_service import TrainingService
from app.utils.logger import get_logger

logger = get_logger(__name__)

TOP_K_FOR_TUNING = 3

_RAW_SENSOR_COLUMNS = ["OperatingHours", "EngineTemp", "HydraulicPressure", "Vibration"]


def _diagnose_signal_quality(df, target_col: str) -> str:
    """Warn early if the raw sensors carry no statistical signal about the target.

    A model landing at chance level (ROC AUC ~0.5) can mean either a pipeline
    bug or a dataset with no learnable relationship. Checking mutual
    information up front tells the two apart and leaves a paper trail on the
    registered model (TrainingRun.notes) for anyone reviewing results later.
    """

    mi_scores = mutual_info_classif(
        df[_RAW_SENSOR_COLUMNS], df[target_col], random_state=Config.RANDOM_STATE
    )
    mi_report = ", ".join(f"{col}={value:.4f}" for col, value in zip(_RAW_SENSOR_COLUMNS, mi_scores))
    note = f"Raw sensor mutual information with target: {mi_report}."

    if max(mi_scores) < 0.01:
        note += (
            " WARNING: near-zero mutual information — the source dataset "
            "(Datasets/Synthetic_Datasets_10_Master_Projects_10000Rows.xlsx, sheet "
            f"{Config.DATASET_SHEET_NAME}) shows no statistically exploitable relationship "
            "between raw sensors and FailureWithin7Days. Chance-level model performance "
            "(ROC AUC ~0.5) is expected and reflects a dataset limitation, not a pipeline defect."
        )
        logger.warning(note)

    return note


def _print_leaderboard(title: str, leaderboard: list[dict]) -> None:
    print(f"\n=== {title} ===")
    header = (
        f"{'Model':<24}{'Acc':>8}{'Prec':>8}{'Rec':>8}{'F1':>8}{'ROC_AUC':>10}"
        f"{'BalAcc':>9}{'MCC':>8}{'LogLoss':>10}{'Composite':>11}"
    )
    print(header)
    for m in leaderboard:
        print(
            f"{m['model']:<24}{m['accuracy']:>8.3f}{m['precision']:>8.3f}{m['recall']:>8.3f}"
            f"{m['f1']:>8.3f}{m['roc_auc']:>10.3f}{m['balanced_accuracy']:>9.3f}"
            f"{m['mcc']:>8.3f}{m['log_loss']:>10.3f}{m['composite_score']:>11.4f}"
        )


def run(n_trials: int | None = None) -> dict:
    """Run the full AutoML pipeline end-to-end and return the winning entry."""

    n_trials = n_trials if n_trials is not None else Config.OPTUNA_N_TRIALS

    training_service = TrainingService()

    logger.info("Preparing dataset (load -> clean -> feature engineering)")
    df, feature_names = training_service.prepare_dataset()

    signal_note = _diagnose_signal_quality(df, Config.TARGET_COLUMN)

    X_train, X_test, y_train, y_test = training_service.split_and_resample(df, feature_names)

    logger.info("Running baseline comparison across model families")
    baseline_leaderboard, fitted_models = training_service.run_baseline_comparison(
        X_train, y_train, X_test, y_test
    )
    _print_leaderboard("Baseline leaderboard (default hyperparameters)", baseline_leaderboard)

    tuned_leaderboard: list[dict] = []
    tuned_models: dict[str, tuple] = {}

    for entry in baseline_leaderboard[:TOP_K_FOR_TUNING]:
        name = entry["model"]
        logger.info("Optuna tuning: %s (%d trials)", name, n_trials)

        best_params, best_cv_f1 = tune_model(
            name, X_train, y_train, n_trials=n_trials, random_state=training_service.random_state
        )
        model = build_model(name, random_state=training_service.random_state, params=best_params)
        model.fit(X_train, y_train)

        metrics = training_service.evaluate(model, X_test, y_test)
        tuned_name = f"{name} (tuned)"
        metrics["model"] = tuned_name
        metrics["composite_score"] = training_service.composite_score(metrics)
        metrics["hyperparameters"] = best_params

        tuned_leaderboard.append(metrics)
        tuned_models[tuned_name] = (model, name, best_params)

    tuned_leaderboard.sort(key=lambda m: m["composite_score"], reverse=True)
    if tuned_leaderboard:
        _print_leaderboard("Tuned leaderboard (Optuna-optimized top candidates)", tuned_leaderboard)

    full_leaderboard = baseline_leaderboard + tuned_leaderboard
    full_leaderboard.sort(key=lambda m: m["composite_score"], reverse=True)
    best_entry = full_leaderboard[0]

    if best_entry["model"] in tuned_models:
        best_model, base_name, best_hyperparams = tuned_models[best_entry["model"]]
    else:
        best_model = fitted_models[best_entry["model"]]
        base_name = best_entry["model"]
        best_hyperparams = {}

    print(
        f"\n>>> Best model selected: {best_entry['model']} "
        f"(composite score={best_entry['composite_score']:.4f}, "
        f"F1={best_entry['f1']:.4f}, ROC AUC={best_entry['roc_auc']:.4f})"
    )

    best_metrics = {k: v for k, v in best_entry.items() if k not in ("model", "hyperparameters")}

    app = create_app()
    with app.app_context():
        registry = ModelRegistryService()
        model_version = registry.register_best_model(
            model=best_model,
            model_name=base_name,
            metrics=best_metrics,
            hyperparameters=best_hyperparams,
            feature_names=feature_names,
            leaderboard=full_leaderboard,
            notes=signal_note,
        )
        model_version_id = model_version.id

    return {"best_entry": best_entry, "model_version_id": model_version_id}


if __name__ == "__main__":
    run()
