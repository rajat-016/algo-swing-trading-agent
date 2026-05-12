import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

import numpy as np
import pandas as pd
from loguru import logger

from intelligence.market_regime.features.volatility_clustering import (
    compute_volatility_clustering,
    VOLATILITY_CLUSTER_VERSION,
)
from intelligence.market_regime.features.trend_persistence import (
    compute_trend_persistence,
    TREND_PERSISTENCE_VERSION,
)
from intelligence.market_regime.features.breadth_analytics import (
    compute_breadth_analytics,
    BREADTH_ANALYTICS_VERSION,
)
from intelligence.market_regime.features.sector_strength import (
    compute_sector_strength,
    SECTOR_STRENGTH_VERSION,
)
from intelligence.market_regime.features.market_stress import (
    compute_market_stress,
    MARKET_STRESS_VERSION,
)
from intelligence.market_regime.features.feature_drift_logger import FeatureDriftLogger


REGIME_FEATURE_VERSION = "1.0.0"

REGIME_FEATURE_GROUPS = [
    "volatility_clustering",
    "trend_persistence",
    "breadth_analytics",
    "sector_strength",
    "market_stress",
]

REGIME_FEATURE_SNAPSHOT_TABLE = """
CREATE TABLE IF NOT EXISTS regime_feature_snapshots (
    id INTEGER PRIMARY KEY,
    regime VARCHAR NOT NULL,
    confidence DOUBLE,
    group_name VARCHAR NOT NULL,
    feature_version VARCHAR NOT NULL,
    feature_hash VARCHAR NOT NULL,
    feature_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REGIME_FEATURE_SNAPSHOT_INDEX = """
CREATE INDEX IF NOT EXISTS idx_regime_feature_snapshot_time
ON regime_feature_snapshots(regime, created_at DESC);
"""


def _compute_regime_feature_hash(feature_data: Dict[str, Any]) -> str:
    content = ",".join(sorted(feature_data.keys()))
    return hashlib.sha256(content.encode()).hexdigest()[:16]


class RegimeFeaturePipeline:
    def __init__(self, drift_logger: Optional[FeatureDriftLogger] = None, db=None):
        self.drift_logger = drift_logger or FeatureDriftLogger(db)
        self._db = db
        self._ready = False

    def initialize(self, db=None):
        if db is not None:
            self._db = db
            self.drift_logger.initialize(db)

        if self._db is None:
            logger.warning("No database for RegimeFeaturePipeline")
            self._ready = False
            return

        try:
            self._db.execute(REGIME_FEATURE_SNAPSHOT_TABLE)
            try:
                self._db.execute(REGIME_FEATURE_SNAPSHOT_INDEX)
            except Exception:
                pass
            self._ready = True
            logger.info("RegimeFeaturePipeline initialized")
        except Exception as e:
            logger.warning(f"Failed to init RegimeFeaturePipeline: {e}")
            self._ready = False

    def compute_all(
        self,
        ohlcv_df: Optional[pd.DataFrame] = None,
        vix_level: Optional[float] = None,
        vix_change: Optional[float] = None,
        put_call_ratio: Optional[float] = None,
        nifty_return: Optional[float] = None,
        sector_returns: Optional[Dict[str, float]] = None,
        pct_above_ma50: Optional[float] = None,
        pct_above_ma200: Optional[float] = None,
        per_stock_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Dict[str, float]]:
        results: Dict[str, Dict[str, float]] = {}

        # 1. Volatility Clustering
        vol_features = compute_volatility_clustering(ohlcv_df) if ohlcv_df is not None else {}
        results["volatility_clustering"] = vol_features

        # 2. Trend Persistence
        trend_features = compute_trend_persistence(ohlcv_df) if ohlcv_df is not None else {}
        results["trend_persistence"] = trend_features

        # 3. Breadth Analytics
        breadth_features = compute_breadth_analytics(
            per_stock_df=per_stock_df,
            pct_above_ma50=pct_above_ma50,
            pct_above_ma200=pct_above_ma200,
        )
        results["breadth_analytics"] = breadth_features

        # 4. Sector Strength
        sector_features = compute_sector_strength(
            per_stock_df=per_stock_df,
            nifty_return=nifty_return,
            sector_returns=sector_returns,
        )
        results["sector_strength"] = sector_features

        # 5. Market Stress
        stress_features = compute_market_stress(
            df=ohlcv_df,
            vix_level=vix_level,
            vix_change=vix_change,
            put_call_ratio=put_call_ratio,
        )
        results["market_stress"] = stress_features

        for group_name, features in results.items():
            if features:
                logger.debug(f"RegimeFeaturePipeline: {group_name}: {len(features)} features computed")
            else:
                logger.debug(f"RegimeFeaturePipeline: {group_name}: no features (insufficient data)")

        return results

    def compute_and_log(
        self,
        ohlcv_df: Optional[pd.DataFrame] = None,
        vix_level: Optional[float] = None,
        vix_change: Optional[float] = None,
        put_call_ratio: Optional[float] = None,
        nifty_return: Optional[float] = None,
        sector_returns: Optional[Dict[str, float]] = None,
        pct_above_ma50: Optional[float] = None,
        pct_above_ma200: Optional[float] = None,
        per_stock_df: Optional[pd.DataFrame] = None,
    ) -> Dict[str, Dict[str, float]]:
        results = self.compute_all(
            ohlcv_df=ohlcv_df,
            vix_level=vix_level,
            vix_change=vix_change,
            put_call_ratio=put_call_ratio,
            nifty_return=nifty_return,
            sector_returns=sector_returns,
            pct_above_ma50=pct_above_ma50,
            pct_above_ma200=pct_above_ma200,
            per_stock_df=per_stock_df,
        )

        for group_name, features in results.items():
            if features:
                drift_results = self.drift_logger.check_group_drift(group_name, features)
                if drift_results:
                    self.drift_logger.log_drift_results(drift_results)

        return results

    def export_snapshot(
        self,
        regime: str,
        confidence: float,
        feature_data: Dict[str, Dict[str, float]],
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        flattened: Dict[str, float] = {}
        for group_name, features in feature_data.items():
            for fname, value in features.items():
                flattened[f"{group_name}__{fname}"] = value

        feature_hash = _compute_regime_feature_hash(flattened)

        snapshot = {
            "regime": regime,
            "confidence": confidence,
            "feature_version": REGIME_FEATURE_VERSION,
            "feature_hash": feature_hash,
            "num_features": len(flattened),
            "feature_groups": list(feature_data.keys()),
            "feature_data": feature_data,
            "timestamp": ts,
        }
        return snapshot

    def persist_snapshot(
        self,
        regime: str,
        confidence: float,
        feature_data: Dict[str, Dict[str, float]],
        timestamp: Optional[str] = None,
    ) -> bool:
        if not self._ready or self._db is None:
            logger.warning("Cannot persist regime feature snapshot: DB not ready")
            return False

        snapshot = self.export_snapshot(regime, confidence, feature_data, timestamp)

        try:
            for group_name, features in feature_data.items():
                if not features:
                    continue
                feature_hash = _compute_regime_feature_hash(features)
                self._db.execute(
                    """
                    INSERT INTO regime_feature_snapshots
                    (regime, confidence, group_name, feature_version, feature_hash, feature_data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        regime,
                        confidence,
                        group_name,
                        REGIME_FEATURE_VERSION,
                        feature_hash,
                        json.dumps(features),
                        snapshot["timestamp"],
                    ],
                )
            return True
        except Exception as e:
            logger.error(f"Failed to persist regime feature snapshot: {e}")
            return False

    def get_snapshot_history(
        self,
        group_name: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        if not self._ready or self._db is None:
            return []

        try:
            if group_name:
                rows = self._db.fetch_all(
                    """
                    SELECT * FROM regime_feature_snapshots
                    WHERE group_name = ?
                    ORDER BY created_at DESC LIMIT ?
                    """,
                    [group_name, limit],
                )
            else:
                rows = self._db.fetch_all(
                    "SELECT * FROM regime_feature_snapshots ORDER BY created_at DESC LIMIT ?",
                    [limit],
                )
            return [
                {
                    "id": r[0],
                    "regime": r[1],
                    "confidence": r[2],
                    "group_name": r[3],
                    "feature_version": r[4],
                    "feature_hash": r[5],
                    "feature_data": json.loads(r[6]) if isinstance(r[6], str) else r[6],
                    "created_at": r[7],
                }
                for r in rows
            ]
        except Exception as e:
            logger.warning(f"Failed to query regime feature snapshots: {e}")
            return []

    @property
    def is_ready(self) -> bool:
        return self._ready
