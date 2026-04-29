import sys
import os
from pathlib import Path

BACKEND_PATH = str(Path(__file__).parent.parent.parent / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

from services.ai.features import FeatureEngineer
import pandas as pd
from typing import List
import logging

logger = logging.getLogger(__name__)


class FeaturePipeline:
    def __init__(self):
        self.engineer = FeatureEngineer()

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "close" not in df.columns:
            return df

        result = self.engineer.generate_features(df.copy())
        self.validate_no_future_data(result)
        return result

    def validate_no_future_data(self, df: pd.DataFrame) -> bool:
        feature_cols = self.engineer.get_feature_names()
        for col in feature_cols:
            if col not in df.columns:
                continue
            if df[col].isna().all():
                logger.warning(f"Feature {col} is all NaN - may indicate look-ahead issue")
        return True

    def get_feature_names(self) -> List[str]:
        return self.engineer.get_feature_names()
