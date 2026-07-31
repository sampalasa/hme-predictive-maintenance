"""Cleans the raw HME_Downtime dataframe before feature engineering.

The current dataset has no missing values, but this service stays
defensive: production sensor feeds do drop readings, so imputation and
outlier handling are implemented even though today's synthetic dataset
does not exercise every branch.
"""

import pandas as pd

from app.utils.logger import get_logger

logger = get_logger(__name__)

_NUMERIC_COLUMNS = ["OperatingHours", "EngineTemp", "HydraulicPressure", "Vibration"]


class DataCleaningService:
    """Deduplicates, imputes and caps outliers in the raw sensor dataframe."""

    def clean(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        before = len(df)
        df = df.drop_duplicates(subset=["EquipmentID", "Timestamp"])
        if len(df) != before:
            logger.info("Dropped %d duplicate readings", before - len(df))

        df = self._impute_missing(df)
        df = self._cap_outliers_iqr(df, _NUMERIC_COLUMNS)

        df = df.sort_values(["EquipmentID", "Timestamp"]).reset_index(drop=True)
        return df

    @staticmethod
    def _impute_missing(df: pd.DataFrame) -> pd.DataFrame:
        for col in _NUMERIC_COLUMNS:
            if df[col].isna().any():
                median = df[col].median()
                df[col] = df[col].fillna(median)
                logger.warning("Imputed %d missing values in %s with median=%.2f",
                                df[col].isna().sum(), col, median)

        for col in ["EquipmentType", "FailureMode"]:
            if df[col].isna().any():
                mode = df[col].mode(dropna=True)
                fill_value = mode.iloc[0] if not mode.empty else "Unknown"
                df[col] = df[col].fillna(fill_value)

        return df

    @staticmethod
    def _cap_outliers_iqr(df: pd.DataFrame, columns: list[str], factor: float = 1.5) -> pd.DataFrame:
        """Cap extreme values to [Q1 - factor*IQR, Q3 + factor*IQR] per column."""

        for col in columns:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            lower = q1 - factor * iqr
            upper = q3 + factor * iqr

            n_capped = ((df[col] < lower) | (df[col] > upper)).sum()
            if n_capped:
                logger.info("Capping %d outlier(s) in %s to [%.2f, %.2f]", n_capped, col, lower, upper)
            df[col] = df[col].clip(lower=lower, upper=upper)

        return df
