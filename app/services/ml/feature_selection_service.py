"""Feature selection: compares multiple techniques on the engineered feature set.

Methods implemented: Mutual Information, Recursive Feature Elimination (RFE),
Permutation Importance, SHAP importance, Variance Threshold, and Boruta.
Each returns a ranking (or retained/rejected split) so the results can be
compared side by side to decide which engineered features actually matter.
"""

from typing import Any

from boruta import BorutaPy
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_selection import RFE, VarianceThreshold, mutual_info_classif
from sklearn.inspection import permutation_importance

from app.config.settings import Config
from app.services.data.data_cleaning_service import DataCleaningService
from app.services.data.data_loader_service import DataLoaderService
from app.services.data.feature_engineering_service import FeatureEngineeringService
from app.services.ml.explainability_service import ExplainabilityService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class FeatureSelectionService:
    """Runs several feature selection / importance techniques and compares them."""

    def __init__(self, sample_size: int = 2000, random_state: int | None = None) -> None:
        self.sample_size = sample_size
        self.random_state = random_state if random_state is not None else Config.RANDOM_STATE
        self.feature_engineering = FeatureEngineeringService()
        self._cache: tuple | None = None

    def _prepare_data(self):
        if self._cache is not None:
            return self._cache

        df = DataLoaderService().load()
        df = DataCleaningService().clean(df)
        df, feature_names = self.feature_engineering.engineer_features(df)

        sample = df.sample(min(self.sample_size, len(df)), random_state=self.random_state)
        X = sample[feature_names]
        y = sample[Config.TARGET_COLUMN]

        self._cache = (X, y, feature_names)
        return self._cache

    def mutual_information(self) -> list[dict[str, Any]]:
        X, y, feature_names = self._prepare_data()
        mi = mutual_info_classif(X, y, random_state=self.random_state)
        return self._to_ranking(feature_names, mi)

    def rfe_ranking(self, n_features_to_select: int = 15) -> list[dict[str, Any]]:
        X, y, feature_names = self._prepare_data()
        estimator = RandomForestClassifier(n_estimators=100, random_state=self.random_state, n_jobs=-1)
        rfe = RFE(estimator, n_features_to_select=n_features_to_select)
        rfe.fit(X, y)
        scores = 1.0 / rfe.ranking_  # rank 1 (selected) -> highest score
        return self._to_ranking(feature_names, scores)

    def permutation_importance_ranking(self) -> list[dict[str, Any]]:
        X, y, feature_names = self._prepare_data()
        model = RandomForestClassifier(n_estimators=200, random_state=self.random_state, n_jobs=-1)
        model.fit(X, y)
        result = permutation_importance(
            model, X, y, n_repeats=5, random_state=self.random_state, n_jobs=-1
        )
        return self._to_ranking(feature_names, result.importances_mean)

    @staticmethod
    def shap_importance() -> list[dict[str, Any]]:
        explanation = ExplainabilityService().get_global_explanation()
        return explanation["feature_importance"]

    def variance_threshold(self, threshold: float = 0.01) -> dict[str, Any]:
        X, y, feature_names = self._prepare_data()
        std = X.std().replace(0, 1)
        X_normalized = ((X - X.mean()) / std).fillna(0.0)

        selector = VarianceThreshold(threshold=threshold)
        selector.fit(X_normalized)

        retained = [f for f, keep in zip(feature_names, selector.get_support()) if keep]
        removed = [f for f in feature_names if f not in retained]
        return {"retained": retained, "removed": removed, "threshold": threshold}

    def boruta_selection(self, max_iter: int = 15) -> dict[str, Any]:
        X, y, feature_names = self._prepare_data()
        # n_jobs=1 (not -1): Boruta re-fits the forest on every iteration, and
        # repeatedly spinning up a multiprocessing pool per fit is what was
        # exhausting memory/handles on Windows during testing.
        rf = RandomForestClassifier(
            n_estimators=100, random_state=self.random_state, n_jobs=1, max_depth=7
        )
        boruta = BorutaPy(
            rf, n_estimators=100, random_state=self.random_state, max_iter=max_iter, verbose=0
        )
        boruta.fit(X.values, y.values)

        confirmed = [f for f, keep in zip(feature_names, boruta.support_) if keep]
        tentative = [f for f, keep in zip(feature_names, boruta.support_weak_) if keep]
        rejected = [f for f in feature_names if f not in confirmed and f not in tentative]
        return {"confirmed": confirmed, "tentative": tentative, "rejected": rejected}

    @staticmethod
    def _to_ranking(feature_names: list[str], scores) -> list[dict[str, Any]]:
        ranking = sorted(zip(feature_names, scores), key=lambda item: item[1], reverse=True)
        return [{"feature": f, "score": round(float(s), 5)} for f, s in ranking]

    def compare_all_methods(self, top_n: int = 15) -> dict[str, Any]:
        """Run every technique and return a side-by-side comparison."""

        try:
            shap_ranking = self.shap_importance()[:top_n]
        except FileNotFoundError:
            shap_ranking = []

        return {
            "mutual_information": self.mutual_information()[:top_n],
            "rfe": self.rfe_ranking()[:top_n],
            "permutation_importance": self.permutation_importance_ranking()[:top_n],
            "shap": shap_ranking,
            "variance_threshold": self.variance_threshold(),
            "boruta": self.boruta_selection(),
        }
