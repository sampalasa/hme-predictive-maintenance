"""Builds the intelligent derived-feature set used to train and predict with.

Given the cleaned raw HME_Downtime dataframe (EquipmentID, EquipmentType,
Timestamp, OperatingHours, EngineTemp, HydraulicPressure, Vibration,
FailureMode, FailureWithin7Days), this service produces 30+ engineered
features grouped into five families:

1. Temporal / per-equipment dynamics (rolling stats, lags, deltas, trend).
2. Risk scores (temperature, pressure, vibration, composite health/failure).
3. Usage & lifecycle (age, load, efficiency, remaining life).
4. Interactions & ratios between raw sensors.
5. Encodings (categorical → numeric) and cyclical time features.

The final feature list (``get_feature_names``) is what both the training
pipeline and the prediction service must use, so it is persisted alongside
the trained model to guarantee train/serve consistency.
"""

import numpy as np
import pandas as pd

from app.utils.constants import (
    ENGINE_TEMP_CRITICAL_C,
    ENGINE_TEMP_WARNING_C,
    HYDRAULIC_PRESSURE_CRITICAL_BAR,
    HYDRAULIC_PRESSURE_WARNING_BAR,
    ROLLING_WINDOW_LONG,
    ROLLING_WINDOW_SHORT,
    VIBRATION_CRITICAL_MM_S,
    VIBRATION_WARNING_MM_S,
)
from app.utils.logger import get_logger

logger = get_logger(__name__)

_EPSILON = 1e-6

# Columns that must never be used as model inputs (identifiers, raw
# timestamp, and the label itself).
_NON_FEATURE_COLUMNS = {
    "EquipmentID",
    "EquipmentType",
    "Timestamp",
    "FailureMode",
    "FailureWithin7Days",
}


class FeatureEngineeringService:
    """Generates the intelligent derived-feature set for the ML pipeline."""

    def engineer_features(self, df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """Return (enriched_dataframe, ordered_feature_column_names)."""

        df = df.sort_values(["EquipmentID", "Timestamp"]).reset_index(drop=True)

        df = self._add_temporal_features(df)
        df = self._add_risk_scores(df)
        df = self._add_usage_and_lifecycle_features(df)
        df = self._add_interaction_features(df)
        df = self._add_encodings(df)

        feature_names = [c for c in df.columns if c not in _NON_FEATURE_COLUMNS]
        logger.info("Feature engineering produced %d features", len(feature_names))
        return df, feature_names

    # ------------------------------------------------------------------
    # 1. Temporal / per-equipment dynamics
    # ------------------------------------------------------------------
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        grouped = df.groupby("EquipmentID")

        for col in ("EngineTemp", "HydraulicPressure", "Vibration"):
            roll_short = grouped[col].transform(
                lambda s: s.rolling(ROLLING_WINDOW_SHORT, min_periods=1).mean()
            )
            roll_long = grouped[col].transform(
                lambda s: s.rolling(ROLLING_WINDOW_LONG, min_periods=1).mean()
            )
            roll_std = grouped[col].transform(
                lambda s: s.rolling(ROLLING_WINDOW_SHORT, min_periods=1).std()
            )
            lag1 = grouped[col].shift(1)

            df[f"{col}_RollMean{ROLLING_WINDOW_SHORT}"] = roll_short
            df[f"{col}_RollMean{ROLLING_WINDOW_LONG}"] = roll_long
            df[f"{col}_RollStd{ROLLING_WINDOW_SHORT}"] = roll_std.fillna(0.0)
            df[f"{col}_Lag1"] = lag1.fillna(df[col])
            df[f"{col}_Delta"] = (df[col] - df[f"{col}_Lag1"]).fillna(0.0)

            # Lightweight trend approximation: average change per step over
            # the long window (full linear regression per row would be too
            # slow for a 10k-row dataset refreshed on every training run).
            trend = grouped[col].transform(
                lambda s: (s - s.shift(ROLLING_WINDOW_LONG - 1)) / (ROLLING_WINDOW_LONG - 1)
            )
            df[f"{col}_TrendSlope"] = trend.fillna(0.0)

        df["DaysSinceLastReading"] = (
            grouped["Timestamp"].diff().dt.total_seconds() / 86400.0
        ).fillna(0.0)

        return df

    # ------------------------------------------------------------------
    # 2. Risk scores
    # ------------------------------------------------------------------
    def _add_risk_scores(self, df: pd.DataFrame) -> pd.DataFrame:
        df["TemperatureRiskScore"] = self._risk_score(
            df["EngineTemp"], ENGINE_TEMP_WARNING_C, ENGINE_TEMP_CRITICAL_C
        )
        df["PressureRiskScore"] = self._risk_score(
            df["HydraulicPressure"], HYDRAULIC_PRESSURE_WARNING_BAR, HYDRAULIC_PRESSURE_CRITICAL_BAR
        )
        df["VibrationRiskScore"] = self._risk_score(
            df["Vibration"], VIBRATION_WARNING_MM_S, VIBRATION_CRITICAL_MM_S
        )

        df["HydraulicStressScore"] = (df["HydraulicPressure"] * df["Vibration"]) / 100.0
        df["EngineHealthScore"] = 100.0 - (
            (df["EngineTemp"] / ENGINE_TEMP_CRITICAL_C).clip(upper=1.5) * 100.0
        )

        df["HealthScore"] = (
            0.4 * df["EngineHealthScore"]
            + 0.3 * (100.0 - df["PressureRiskScore"] * 50.0)
            + 0.3 * (100.0 - df["VibrationRiskScore"] * 50.0)
        ).clip(lower=0.0, upper=100.0)

        df["FailureRiskIndex"] = (
            df["TemperatureRiskScore"] + df["PressureRiskScore"] + df["VibrationRiskScore"]
        ) / 3.0

        return df

    @staticmethod
    def _risk_score(series: pd.Series, warning: float, critical: float) -> pd.Series:
        """0 = normal, 1 = warning, 2 = critical."""

        return np.select(
            [series >= critical, series >= warning],
            [2, 1],
            default=0,
        )

    # ------------------------------------------------------------------
    # 3. Usage & lifecycle
    # ------------------------------------------------------------------
    def _add_usage_and_lifecycle_features(self, df: pd.DataFrame) -> pd.DataFrame:
        type_group = df.groupby("EquipmentType")["OperatingHours"]

        df["EquipmentAgeScore"] = type_group.transform(lambda s: s.rank(pct=True))
        df["UsageScore"] = df["OperatingHours"] / (type_group.transform("max") + _EPSILON)

        df["OperatingEfficiency"] = 1.0 / (
            1.0
            + df["Vibration"] / 10.0
            + (df["EngineTemp"] - ENGINE_TEMP_WARNING_C).clip(lower=0) / 50.0
        )
        df["OperatingLoad"] = (df["HydraulicPressure"] * df["OperatingHours"]) / 1_000_000.0

        # Typical operating hours at failure, per equipment type, learned
        # from historical failures — used to estimate remaining useful life.
        failure_hours_by_type = (
            df.loc[df["FailureWithin7Days"] == 1].groupby("EquipmentType")["OperatingHours"].median()
        )
        typical_failure_hours = df["EquipmentType"].map(failure_hours_by_type)
        typical_failure_hours = typical_failure_hours.fillna(df["OperatingHours"].median())
        df["PredictedRemainingLife"] = (typical_failure_hours - df["OperatingHours"]).clip(lower=0.0)

        df["CriticalityScore"] = (
            0.5 * df["FailureRiskIndex"] * 50.0 + 0.5 * df["EquipmentAgeScore"] * 100.0
        ).clip(lower=0.0, upper=100.0)

        df["MaintenancePriority"] = pd.cut(
            df["CriticalityScore"], bins=[-1, 25, 50, 75, 101], labels=[0, 1, 2, 3]
        ).astype(int)
        df["EquipmentConditionScore"] = pd.cut(
            df["HealthScore"], bins=[-1, 25, 50, 75, 101], labels=[3, 2, 1, 0]
        ).astype(int)

        return df

    # ------------------------------------------------------------------
    # 4. Interactions & ratios
    # ------------------------------------------------------------------
    def _add_interaction_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df["EngineTemp_x_Vibration"] = df["EngineTemp"] * df["Vibration"]
        df["HydraulicPressure_x_OperatingHours"] = (
            df["HydraulicPressure"] * df["OperatingHours"] / 1000.0
        )
        df["Vibration_per_OperatingHour"] = df["Vibration"] / (df["OperatingHours"] + _EPSILON)

        for col in ("EngineTemp", "HydraulicPressure", "Vibration"):
            grouped = df.groupby("EquipmentType")[col]
            mean = grouped.transform("mean")
            std = grouped.transform("std").replace(0, _EPSILON)
            df[f"{col}_ZScoreByType"] = (df[col] - mean) / std

        return df

    # ------------------------------------------------------------------
    # 5. Encodings & cyclical time features
    # ------------------------------------------------------------------
    def _add_encodings(self, df: pd.DataFrame) -> pd.DataFrame:
        equipment_type_dummies = pd.get_dummies(
            df["EquipmentType"], prefix="EquipmentType", dtype=int
        )
        df = pd.concat([df, equipment_type_dummies], axis=1)

        failure_mode_freq = df["FailureMode"].map(df["FailureMode"].value_counts(normalize=True))
        df["FailureMode_FreqEncoding"] = failure_mode_freq

        month = df["Timestamp"].dt.month
        day_of_week = df["Timestamp"].dt.dayofweek
        hour = df["Timestamp"].dt.hour

        df["Month_Sin"] = np.sin(2 * np.pi * month / 12)
        df["Month_Cos"] = np.cos(2 * np.pi * month / 12)
        df["DayOfWeek_Sin"] = np.sin(2 * np.pi * day_of_week / 7)
        df["DayOfWeek_Cos"] = np.cos(2 * np.pi * day_of_week / 7)
        df["Hour_Sin"] = np.sin(2 * np.pi * hour / 24)
        df["Hour_Cos"] = np.cos(2 * np.pi * hour / 24)

        return df
