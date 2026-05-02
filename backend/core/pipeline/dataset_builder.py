import pandas as pd
import numpy as np
from typing import Optional, Tuple
from core.pipeline.feature_pipeline import FeaturePipeline
from core.pipeline.label_pipeline import LabelPipeline
from core.logging import logger


class DatasetBuilder:
    def __init__(
        self,
        feature_pipeline: Optional[FeaturePipeline] = None,
        label_pipeline: Optional[LabelPipeline] = None,
        lookahead: int = 5,
        threshold: float = 0.10,
        stop_loss: float = 0.03,
    ):
        self.feature_pipeline = feature_pipeline or FeaturePipeline()
        self.label_pipeline = label_pipeline or LabelPipeline(
            lookahead=lookahead, threshold=threshold, stop_loss=stop_loss
        )

    def build(
        self,
        ohlcv_df: pd.DataFrame,
        market_df: Optional[pd.DataFrame] = None,
    ) -> Tuple[pd.DataFrame, pd.Series]:
        features = self.feature_pipeline.transform(ohlcv_df, market_df)

        labels = self.label_pipeline.transform(ohlcv_df)

        valid_idx = features.index.intersection(labels.index)
        features = features.loc[valid_idx]
        labels = labels.loc[valid_idx]

        features = features.dropna(how="all")
        labels = labels.loc[features.index]

        nan_feature_counts = features.isna().sum()
        bad_features = nan_feature_counts[nan_feature_counts > len(features) * 0.5].index.tolist()
        if bad_features:
            features = features.drop(columns=bad_features)
            logger.info(f"DatasetBuilder: dropped {len(bad_features)} features with >50% NaN")

        features = features.fillna(features.median())

        logger.info(f"DatasetBuilder: {len(features)} samples, {len(features.columns)} features")
        return features, labels
