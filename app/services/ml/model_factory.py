"""Instantiates each candidate classifier compared by the AutoML pipeline."""

from typing import Any

from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.ensemble import (
    ExtraTreesClassifier,
    GradientBoostingClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
)
from xgboost import XGBClassifier

MODEL_NAMES: list[str] = [
    "RandomForest",
    "ExtraTrees",
    "GradientBoosting",
    "HistGradientBoosting",
    "XGBoost",
    "LightGBM",
    "CatBoost",
]


def build_model(name: str, random_state: int, params: dict[str, Any] | None = None):
    """Instantiate a classifier by name with the given hyperparameters."""

    params = params or {}

    if name == "RandomForest":
        return RandomForestClassifier(random_state=random_state, n_jobs=-1, **params)
    if name == "ExtraTrees":
        return ExtraTreesClassifier(random_state=random_state, n_jobs=-1, **params)
    if name == "GradientBoosting":
        return GradientBoostingClassifier(random_state=random_state, **params)
    if name == "HistGradientBoosting":
        return HistGradientBoostingClassifier(random_state=random_state, **params)
    if name == "XGBoost":
        return XGBClassifier(
            random_state=random_state, n_jobs=-1, eval_metric="logloss", **params
        )
    if name == "LightGBM":
        return LGBMClassifier(random_state=random_state, n_jobs=-1, verbosity=-1, **params)
    if name == "CatBoost":
        return CatBoostClassifier(random_state=random_state, verbose=False, **params)

    raise ValueError(f"Unknown model name: {name}")
