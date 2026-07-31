"""Data drift detection: Population Stability Index (PSI) and Kolmogorov-Smirnov test.

Compares an older "reference" window of readings against the most recent
"current" window, per sensor, to flag distributional drift that could
silently degrade the active model's predictions over time. This is the
lightweight, actually-runnable substitute for a full Evidently/Airflow drift
pipeline (see docs/08_mlops.md for the trade-off).
"""

from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from app.models import EquipmentReading, db
from app.utils.logger import get_logger

logger = get_logger(__name__)

_MONITORED_COLUMNS = ["operating_hours", "engine_temp", "hydraulic_pressure", "vibration"]
_PSI_BINS = 10
_PSI_MODERATE_THRESHOLD = 0.1
_PSI_HIGH_THRESHOLD = 0.25


class DriftService:
    """Detects data drift between an older reference window and recent readings."""

    @staticmethod
    def _load_readings_df() -> pd.DataFrame:
        rows = (
            db.session.query(
                EquipmentReading.timestamp,
                EquipmentReading.operating_hours,
                EquipmentReading.engine_temp,
                EquipmentReading.hydraulic_pressure,
                EquipmentReading.vibration,
            )
            .order_by(EquipmentReading.timestamp)
            .all()
        )
        return pd.DataFrame(
            rows,
            columns=["timestamp", "operating_hours", "engine_temp", "hydraulic_pressure", "vibration"],
        )

    @staticmethod
    def _psi(reference: np.ndarray, current: np.ndarray, bins: int = _PSI_BINS) -> float:
        breakpoints = np.quantile(reference, np.linspace(0, 1, bins + 1))
        breakpoints[0] -= 1e-6
        breakpoints[-1] += 1e-6

        ref_counts, _ = np.histogram(reference, bins=breakpoints)
        cur_counts, _ = np.histogram(current, bins=breakpoints)

        ref_pct = np.clip(ref_counts / max(len(reference), 1), 1e-6, None)
        cur_pct = np.clip(cur_counts / max(len(current), 1), 1e-6, None)

        return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))

    def detect_drift(self, split_ratio: float = 0.7) -> dict[str, Any]:
        """Split readings chronologically at `split_ratio` and compare the two halves."""

        df = self._load_readings_df()
        if len(df) < 20:
            return {"status": "insufficient_data", "features": []}

        split_index = int(len(df) * split_ratio)
        reference, current = df.iloc[:split_index], df.iloc[split_index:]

        results = []
        for col in _MONITORED_COLUMNS:
            psi = self._psi(reference[col].to_numpy(), current[col].to_numpy())
            ks_stat, ks_pvalue = ks_2samp(reference[col], current[col])

            if psi >= _PSI_HIGH_THRESHOLD:
                severity = "high"
            elif psi >= _PSI_MODERATE_THRESHOLD:
                severity = "moderate"
            else:
                severity = "none"

            results.append(
                {
                    "feature": col,
                    "psi": round(psi, 4),
                    "ks_statistic": round(float(ks_stat), 4),
                    "ks_pvalue": round(float(ks_pvalue), 4),
                    "drift_detected": bool(ks_pvalue < 0.05 or psi >= _PSI_MODERATE_THRESHOLD),
                    "severity": severity,
                }
            )

        any_drift = any(r["drift_detected"] for r in results)
        status = "drift_detected" if any_drift else "stable"

        logger.info("Drift check: status=%s reference=%d current=%d", status, len(reference), len(current))
        return {
            "status": status,
            "reference_size": len(reference),
            "current_size": len(current),
            "features": results,
        }
