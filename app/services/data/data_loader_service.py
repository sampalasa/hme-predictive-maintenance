"""Loads the raw HME_Downtime dataset from the source Excel workbook.

Column detection is name-based (not positional) so the loader keeps working
if the workbook's column order changes, and fails loudly and early if an
expected column is missing or renamed.
"""

from pathlib import Path

import pandas as pd

from app.config.settings import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DataLoaderService:
    """Reads and validates the HME_Downtime sheet from the dataset workbook."""

    def __init__(
        self,
        dataset_path: Path | None = None,
        sheet_name: str | None = None,
        expected_columns: list[str] | None = None,
    ) -> None:
        self.dataset_path = Path(dataset_path or Config.DATASET_PATH)
        self.sheet_name = sheet_name or Config.DATASET_SHEET_NAME
        self.expected_columns = expected_columns or Config.EXPECTED_COLUMNS

    def load(self) -> pd.DataFrame:
        """Load the raw dataset and validate its schema.

        Raises:
            FileNotFoundError: if the workbook does not exist.
            ValueError: if any expected column is missing from the sheet.
        """

        if not self.dataset_path.exists():
            raise FileNotFoundError(f"Dataset not found at: {self.dataset_path}")

        logger.info("Loading dataset from %s (sheet=%s)", self.dataset_path, self.sheet_name)
        df = pd.read_excel(self.dataset_path, sheet_name=self.sheet_name)

        self._validate_schema(df)
        self._coerce_dtypes(df)

        logger.info("Loaded %d rows, %d columns", len(df), len(df.columns))
        return df

    def _validate_schema(self, df: pd.DataFrame) -> None:
        missing = [col for col in self.expected_columns if col not in df.columns]
        if missing:
            raise ValueError(
                f"Dataset is missing expected column(s): {missing}. "
                f"Found columns: {list(df.columns)}"
            )

    @staticmethod
    def _coerce_dtypes(df: pd.DataFrame) -> None:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"])
        df["EquipmentID"] = df["EquipmentID"].astype(str)
        df["EquipmentType"] = df["EquipmentType"].astype(str)
        df["FailureMode"] = df["FailureMode"].astype(str)
