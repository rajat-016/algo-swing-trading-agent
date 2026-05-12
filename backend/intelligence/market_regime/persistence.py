from datetime import datetime, timezone
from typing import Optional, List, Dict
from loguru import logger

from intelligence.market_regime.config import RegimeConfig
from intelligence.market_regime.regimes import RegimeOutput, RegimeType
from intelligence.market_regime.transition_detector import TransitionDetectorOutput


REGIME_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS market_regime_history (
    id INTEGER PRIMARY KEY,
    regime VARCHAR NOT NULL,
    confidence DOUBLE,
    risk_level VARCHAR,
    stability VARCHAR,
    atr_pct DOUBLE,
    bb_width DOUBLE,
    vix_level DOUBLE,
    ema_diff_pct DOUBLE,
    adx DOUBLE,
    macd_histogram DOUBLE,
    volume_ratio DOUBLE,
    signal_breakdown TEXT,
    suggested_behavior TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REGIME_HISTORY_INDEX = """
CREATE INDEX IF NOT EXISTS idx_regime_history_created_at
ON market_regime_history(created_at DESC);
"""

TRANSITION_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS regime_transition_log (
    id INTEGER PRIMARY KEY,
    current_regime VARCHAR NOT NULL,
    transition_probability DOUBLE,
    regime_persistence_bars INTEGER,
    avg_regime_duration DOUBLE,
    volatility_spike_score DOUBLE,
    vol_spike_detected BOOLEAN,
    confidence_degradation DOUBLE,
    confidence_degraded BOOLEAN,
    transition_alert VARCHAR,
    markov_next_regime VARCHAR,
    markov_next_probability DOUBLE,
    is_unstable BOOLEAN,
    is_transitioning BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TRANSITION_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transition_log_created
ON regime_transition_log(created_at DESC);
"""


class RegimePersistence:
    def __init__(self, config: RegimeConfig, db=None):
        self.config = config
        self._db = db
        self._ready = False

    def initialize(self, db=None):
        if db is not None:
            self._db = db
        if self._db is None:
            logger.warning("No database connection provided for RegimePersistence")
            self._ready = False
            return

        try:
            self._db.execute(REGIME_HISTORY_TABLE)
            try:
                self._db.execute(REGIME_HISTORY_INDEX)
            except Exception:
                pass
            try:
                self._db.execute(TRANSITION_LOG_TABLE)
            except Exception:
                pass
            try:
                self._db.execute(TRANSITION_LOG_INDEX)
            except Exception:
                pass
            self._ready = True
            logger.info("Regime persistence initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize regime persistence: {e}")
            self._ready = False

    def store_regime(self, regime_output: RegimeOutput):
        if not self._ready or self._db is None:
            return False

        try:
            ts = regime_output.timestamp or datetime.now(timezone.utc).isoformat()
            signal_breakdown_str = str(regime_output.signal_breakdown) if regime_output.signal_breakdown else None
            suggested_str = str(regime_output.suggested_behavior) if regime_output.suggested_behavior else None

            self._db.execute(
                """
                INSERT INTO market_regime_history
                (regime, confidence, risk_level, stability,
                 atr_pct, bb_width, vix_level,
                 ema_diff_pct, adx, macd_histogram, volume_ratio,
                 signal_breakdown, suggested_behavior, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    regime_output.regime.value if isinstance(regime_output.regime, RegimeType) else regime_output.regime,
                    regime_output.confidence,
                    regime_output.risk_level,
                    regime_output.stability,
                    regime_output.volatility_context.atr_pct if regime_output.volatility_context else None,
                    regime_output.volatility_context.bb_width if regime_output.volatility_context else None,
                    regime_output.volatility_context.vix_level if regime_output.volatility_context else None,
                    regime_output.trend_context.ema_diff_pct if regime_output.trend_context else None,
                    regime_output.trend_context.adx if regime_output.trend_context else None,
                    regime_output.trend_context.macd_histogram if regime_output.trend_context else None,
                    regime_output.volume_context.volume_ratio if regime_output.volume_context else None,
                    signal_breakdown_str,
                    suggested_str,
                    ts,
                ],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store regime: {e}")
            return False

    def get_recent_regimes(self, limit: int = 100) -> List[dict]:
        if not self._ready or self._db is None:
            return []

        try:
            rows = self._db.fetch_all(
                "SELECT * FROM market_regime_history ORDER BY created_at DESC LIMIT ?",
                [limit],
            )
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to query regimes: {e}")
            return []

    def get_regime_by_date(self, date: str) -> Optional[dict]:
        if not self._ready or self._db is None:
            return None

        try:
            row = self._db.fetch_one(
                "SELECT * FROM market_regime_history WHERE DATE(created_at) = ? ORDER BY created_at DESC LIMIT 1",
                [date],
            )
            return self._row_to_dict(row) if row else None
        except Exception as e:
            logger.warning(f"Failed to query regime by date: {e}")
            return None

    def get_regime_distribution(self, days: int = 30) -> Dict[str, int]:
        if not self._ready or self._db is None:
            return {}

        import pandas as pd
        try:
            df = self._db.query_df(
                """
                SELECT regime, COUNT(*) as count
                FROM market_regime_history
                WHERE created_at >= NOW() - INTERVAL ? DAY
                GROUP BY regime
                ORDER BY count DESC
                """,
                [days],
            )
            return dict(zip(df["regime"].tolist(), df["count"].tolist()))
        except Exception as e:
            logger.warning(f"Failed to get regime distribution: {e}")
            return {}

    def get_transition_count(self, days: int = 30) -> int:
        if not self._ready or self._db is None:
            return 0

        try:
            rows = self._db.fetch_all(
                """
                SELECT regime FROM market_regime_history
                WHERE created_at >= NOW() - INTERVAL ? DAY
                ORDER BY created_at ASC
                """,
                [days],
            )
            if len(rows) < 2:
                return 0
            regimes = [r[0] for r in rows]
            changes = sum(1 for i in range(1, len(regimes)) if regimes[i] != regimes[i - 1])
            return changes
        except Exception as e:
            logger.warning(f"Failed to count transitions: {e}")
            return 0

    def store_transition_log(
        self,
        transition_output: "TransitionDetectorOutput",
        current_regime: str,
    ) -> bool:
        if not self._ready or self._db is None:
            return False

        try:
            self._db.execute(
                """
                INSERT INTO regime_transition_log
                (current_regime, transition_probability, regime_persistence_bars,
                 avg_regime_duration, volatility_spike_score, vol_spike_detected,
                 confidence_degradation, confidence_degraded, transition_alert,
                 markov_next_regime, markov_next_probability, is_unstable,
                 is_transitioning, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    current_regime,
                    transition_output.current_transition_probability,
                    transition_output.regime_persistence_bars,
                    transition_output.avg_regime_duration,
                    transition_output.volatility_spike_score,
                    transition_output.vol_spike_detected,
                    transition_output.confidence_degradation,
                    transition_output.confidence_degraded,
                    transition_output.transition_alert,
                    transition_output.most_likely_next_regime,
                    transition_output.most_likely_next_probability,
                    transition_output.is_unstable,
                    transition_output.is_transitioning,
                    datetime.now(timezone.utc).isoformat(),
                ],
            )
            return True
        except Exception as e:
            logger.error(f"Failed to store transition log: {e}")
            return False

    def get_transition_logs(self, limit: int = 50) -> List[dict]:
        if not self._ready or self._db is None:
            return []

        try:
            rows = self._db.fetch_all(
                "SELECT * FROM regime_transition_log ORDER BY created_at DESC LIMIT ?",
                [limit],
            )
            col_names = [
                "id", "current_regime", "transition_probability",
                "regime_persistence_bars", "avg_regime_duration",
                "volatility_spike_score", "vol_spike_detected",
                "confidence_degradation", "confidence_degraded",
                "transition_alert", "markov_next_regime",
                "markov_next_probability", "is_unstable",
                "is_transitioning", "created_at",
            ]
            # Remove confidence_current, confidence_previous from col_names since they're not in the query
            return [dict(zip(col_names, r)) for r in rows]
        except Exception as e:
            logger.warning(f"Failed to query transition logs: {e}")
            return []

    def _row_to_dict(self, row) -> dict:
        col_names = [
            "id", "regime", "confidence", "risk_level", "stability",
            "atr_pct", "bb_width", "vix_level",
            "ema_diff_pct", "adx", "macd_histogram", "volume_ratio",
            "signal_breakdown", "suggested_behavior", "created_at",
        ]
        return {col: val for col, val in zip(col_names, row)} if row else {}

    @property
    def is_ready(self) -> bool:
        return self._ready
