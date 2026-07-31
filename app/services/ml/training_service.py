"""AutoML training service.

Orchestrates the full model-comparison pipeline: data preparation, stratified
split, SMOTE resampling, baseline comparison across seven model families, and
composite-score ranking. Optuna tuning of the top candidates is handled by
``optuna_tuner`` and orchestrated by ``app/ml/training/train_pipeline.py``,
which is the executable entry point for the whole pipeline.
"""

from typing import Any

import pandas as pd
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    f1_score,
    log_loss,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from app.config.settings import Config
from app.services.data.data_cleaning_service import DataCleaningService
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.feature_engineering_service import FeatureEngineeringService
from app.services.ml.model_factory import MODEL_NAMES, build_model
from app.utils.logger import get_logger

logger = get_logger(__name__)


class TrainingService:
    """Prepares data and runs the baseline AutoML model comparison."""

    def __init__(self, random_state: int | None = None) -> None:
        self.random_state = random_state if random_state is not None else Config.RANDOM_STATE

    def prepare_dataset(self) -> tuple[pd.DataFrame, list[str]]:
        """Load, clean and feature-engineer the HME_Downtime dataset."""

        df = DataLoaderService().load()
        df = DataCleaningService().clean(df)
        df, feature_names = FeatureEngineeringService().engineer_features(df)
        return df, feature_names

    def split_and_resample(
        self, df: pd.DataFrame, feature_names: list[str], test_size: float = 0.2
    ):
        """Stratified train/test split, then SMOTE on the training fold only."""

        X = df[feature_names]
        y = df[Config.TARGET_COLUMN]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, stratify=y, random_state=self.random_state
        )

        smote = SMOTE(random_state=self.random_state)
        X_train_res, y_train_res = smote.fit_resample(X_train, y_train)

        logger.info(
            "Split: train=%d (after SMOTE=%d), test=%d, positive_rate_test=%.3f",
            len(X_train), len(X_train_res), len(X_test), y_test.mean(),
        )
        return X_train_res, X_test, y_train_res, y_test

    @staticmethod
    def evaluate(model: Any, X_test: pd.DataFrame, y_test: pd.Series) -> dict[str, float]:
        """Compute the full metrics suite required by the AutoML selection."""

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        return {
            "accuracy": float(accuracy_score(y_test, y_pred)),
            "precision": float(precision_score(y_test, y_pred, zero_division=0)),
            "recall": float(recall_score(y_test, y_pred, zero_division=0)),
            "f1": float(f1_score(y_test, y_pred, zero_division=0)),
            "roc_auc": float(roc_auc_score(y_test, y_proba)),
            "balanced_accuracy": float(balanced_accuracy_score(y_test, y_pred)),
            "mcc": float(matthews_corrcoef(y_test, y_pred)),
            "log_loss": float(log_loss(y_test, y_proba)),
        }

    @staticmethod
    def composite_score(metrics: dict[str, float]) -> float:
        """Weighted score used to rank models: balances F1 and ROC AUC."""

        return 0.5 * metrics["f1"] + 0.5 * metrics["roc_auc"]

    def run_baseline_comparison(
        self, X_train: pd.DataFrame, y_train: pd.Series, X_test: pd.DataFrame, y_test: pd.Series
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Train every candidate model with default hyperparameters and rank them."""

        leaderboard: list[dict[str, Any]] = []
        fitted_models: dict[str, Any] = {}

        for name in MODEL_NAMES:
            logger.info("Training baseline model: %s", name)
            model = build_model(name, random_state=self.random_state)
            model.fit(X_train, y_train)

            metrics = self.evaluate(model, X_test, y_test)
            metrics["model"] = name
            metrics["composite_score"] = self.composite_score(metrics)

            leaderboard.append(metrics)
            fitted_models[name] = model

        leaderboard.sort(key=lambda m: m["composite_score"], reverse=True)
        return leaderboard, fitted_models
