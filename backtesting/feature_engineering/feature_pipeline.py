import sys
import os
from pathlib import Path
from typing import List, Optional

BACKEND_PATH = str(Path(__file__).parent.parent.parent / "backend")
if BACKEND_PATH not in sys.path:
    sys.path.insert(0, BACKEND_PATH)

from services.ai.features import FeatureEngineer
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class FeaturePipeline:
    def __init__(self):
        self.engineer = FeatureEngineer()
        # Import live system's 60 curated features for alignment
        self.selected_features: Optional[List[str]] = self._load_live_selected_features()
        
    def _load_live_selected_features(self) -> Optional[List[str]]:
        try:
            from core.pipeline.feature_pipeline import SELECTED_FEATURES
            logger.info(f"Aligned with live system: {len(SELECTED_FEATURES)} selected features")
            return SELECTED_FEATURES
        except ImportError:
            logger.warning("Could not import live SELECTED_FEATURES, using all available features")
            return None

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "close" not in df.columns:
            return df

        result = self.engineer.generate_features(df.copy())
        self.validate_no_future_data(result)
        
        # Preserve critical OHLCV columns needed by labeler and simulator
        critical_cols = ["open", "high", "low", "close", "volume", "datetime", "symbol"]
        preserved = [col for col in critical_cols if col in result.columns]
        
        # Filter to live-aligned features if available
        if self.selected_features is not None:
            available = [f for f in self.selected_features if f in result.columns]
            unavailable = [f for f in self.selected_features if f not in result.columns]
            if unavailable:
                logger.debug(f"Unavailable selected features: {len(unavailable)}")
            result = result[preserved + available].copy()
        
        return result

    def validate_no_future_data(self, df: pd.DataFrame) -> bool:
        feature_cols = self.get_feature_names()
        for col in feature_cols:
            if col not in df.columns:
                continue
            if df[col].isna().all():
                logger.warning(f"Feature {col} is all NaN - may indicate look-ahead issue")
        return True

    def get_feature_names(self) -> List[str]:
        if self.selected_features is not None:
            return [f for f in self.selected_features if f in self.engineer.get_feature_names()]
        return self.engineer.get_feature_names()
