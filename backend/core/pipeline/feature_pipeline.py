import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from services.ai.features import FeatureEngineer
from core.logging import logger


FEATURE_VERSION = "1.0.0"


def _compute_feature_hash(feature_names: List[str]) -> str:
    content = ",".join(sorted(feature_names))
    return hashlib.sha256(content.encode()).hexdigest()[:16]


SELECTED_FEATURES = [
    "returns",
    "log_returns",
    "price_range",
    "hl_ratio",
    "co_ratio",
    "returns_5d",
    "returns_10d",
    "returns_20d",
    "sma_20",
    "sma_50",
    "ema_20",
    "ema_50",
    "sma_20_50_diff",
    "price_to_sma_20",
    "price_to_sma_50",
    "rsi_14",
    "macd",
    "macd_signal",
    "macd_hist",
    "momentum_12",
    "momentum_26",
    "atr_14",
    "stddev_20",
    "bb_position",
    "volume_ratio",
    "vwap",
    "ema_20_above_50",
    "ema_20_slope",
    "pullback_pct",
    "support_distance",
    "trend_strength",
    "breakout_volume",
    "resistance_distance",
    "retest_holds",
    "stage",
    "vs_nifty_return",
    "relative_strength",
    "range_contraction",
    "vcp_signal",
    "reversal_candle",
    "near_support",
    "weekly_trend",
    "daily_weekly_aligned",
    "historical_volatility_20",
    "hv_ratio",
    "donchian_position",
    "atr_percent",
    "volatility_expansion",
    "volume_imbalance",
    "buying_volume_ratio",
    "selling_volume_ratio",
    "relative_volume",
    "momentum_persistency",
    "close_position",
    "body_to_range",
    "intraday_return",
    "gap_size",
    "inside_bar",
    "bullish_signal",
    "bearish_signal",
]


FEATURE_HASH = _compute_feature_hash(SELECTED_FEATURES)


class FeaturePipeline:
    def __init__(self, features: Optional[List[str]] = None):
        self.engineer = FeatureEngineer()
        self.selected_features = features or SELECTED_FEATURES

    @property
    def version_metadata(self) -> Dict[str, object]:
        return {
            "feature_version": FEATURE_VERSION,
            "feature_hash": FEATURE_HASH,
            "num_features": len(self.selected_features),
            "feature_names": self.selected_features.copy(),
        }

    def export_snapshot(
        self,
        features: pd.DataFrame,
        symbol: str,
        timestamp,
        extra_metadata: Optional[Dict[str, object]] = None,
    ) -> Dict[str, object]:
        ts = timestamp
        if not isinstance(ts, str):
            ts = timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)

        snapshot = {
            "symbol": symbol,
            "timestamp": ts,
            "feature_version": FEATURE_VERSION,
            "feature_hash": FEATURE_HASH,
            "num_features": len(self.selected_features),
            "feature_names": self.selected_features.copy(),
            "feature_values": None,
            "metadata": extra_metadata or {},
        }

        if isinstance(features, pd.DataFrame):
            snapshot["feature_values"] = features.to_dict(orient="index") if not features.empty else {}
            snapshot["num_rows"] = len(features)
        elif isinstance(features, dict):
            snapshot["feature_values"] = features

        return snapshot

    def transform(self, ohlcv_df: pd.DataFrame, market_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        if market_df is not None and not market_df.empty:
            self.engineer.set_nifty_data(market_df)

        features = self.engineer.generate_features(ohlcv_df)

        available = [f for f in self.selected_features if f in features.columns]
        unavailable = [f for f in self.selected_features if f not in features.columns]
        if unavailable:
            logger.debug(f"FeaturePipeline: {len(unavailable)} features unavailable")

        result = features[available].copy()
        result = result.replace([np.inf, -np.inf], np.nan)
        return result

    def get_feature_names(self) -> List[str]:
        return self.selected_features
