"""Hyperparameter optimization with Optuna for the top AutoML candidates.

Each model family gets its own search space (max_depth, learning_rate,
n_estimators, subsample, gamma, min_child_weight, etc.) tuned to maximize
the mean F1 score over a stratified k-fold cross-validation on the
(SMOTE-resampled) training set.
"""

from typing import Any

import numpy as np
import optuna
from sklearn.model_selection import StratifiedKFold, cross_val_score

from app.services.ml.model_factory import build_model
from app.utils.logger import get_logger

logger = get_logger(__name__)

optuna.logging.set_verbosity(optuna.logging.WARNING)


def _suggest_params(trial: optuna.Trial, model_name: str) -> dict[str, Any]:
    if model_name in ("RandomForest", "ExtraTrees"):
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 20),
            "min_samples_split": trial.suggest_int("min_samples_split", 2, 10),
            "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 8),
            "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
        }

    if model_name == "GradientBoosting":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 400, step=50),
            "max_depth": trial.suggest_int("max_depth", 2, 8),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        }

    if model_name == "HistGradientBoosting":
        return {
            "max_iter": trial.suggest_int("max_iter", 100, 400, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "l2_regularization": trial.suggest_float("l2_regularization", 0.0, 1.0),
        }

    if model_name == "XGBoost":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        }

    if model_name == "LightGBM":
        return {
            "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
            "max_depth": trial.suggest_int("max_depth", 3, 15),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "num_leaves": trial.suggest_int("num_leaves", 15, 127),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        }

    if model_name == "CatBoost":
        return {
            "iterations": trial.suggest_int("iterations", 100, 500, step=50),
            "depth": trial.suggest_int("depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1.0, 10.0),
        }

    raise ValueError(f"No Optuna search space defined for model: {model_name}")


def tune_model(
    model_name: str,
    X_train: np.ndarray,
    y_train: np.ndarray,
    n_trials: int,
    random_state: int,
    n_splits: int = 3,
) -> tuple[dict[str, Any], float]:
    """Run an Optuna study for one model family. Returns (best_params, best_f1)."""

    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)

    def objective(trial: optuna.Trial) -> float:
        params = _suggest_params(trial, model_name)
        model = build_model(model_name, random_state=random_state, params=params)
        scores = cross_val_score(model, X_train, y_train, cv=cv, scoring="f1", n_jobs=1)
        return float(scores.mean())

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)

    logger.info("Optuna tuning for %s: best F1=%.4f params=%s", model_name, study.best_value, study.best_params)
    return study.best_params, study.best_value
