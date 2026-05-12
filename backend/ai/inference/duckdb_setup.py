import os
from loguru import logger
from typing import Optional
from ai.config.settings import ai_settings


TRADE_MEMORY_SCHEMA_V1 = """
CREATE TABLE IF NOT EXISTS trade_memory (
    trade_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    timestamp TIMESTAMP,
    market_regime VARCHAR,
    feature_snapshot TEXT,
    prediction VARCHAR,
    confidence DOUBLE,
    reasoning TEXT,
    outcome VARCHAR,
    portfolio_state TEXT,
    reflection_notes TEXT,
    schema_version VARCHAR DEFAULT '1.0',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MARKET_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS market_memory (
    id INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    regime VARCHAR,
    regime_confidence DOUBLE,
    volatility DOUBLE,
    vix_level DOUBLE,
    breadth DOUBLE,
    sector_rotation_score DOUBLE,
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REGIME_HISTORY_SCHEMA = """
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

PREDICTION_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS prediction_log_analytics (
    id INTEGER PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    prediction_time TIMESTAMP,
    predicted_class INTEGER,
    predicted_probs VARCHAR,
    actual_outcome VARCHAR,
    confidence DOUBLE,
    features_hash VARCHAR,
    model_version VARCHAR,
    regime_at_prediction VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

REFLECTION_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS reflection_log (
    id INTEGER PRIMARY KEY,
    period_start DATE,
    period_end DATE,
    reflection_type VARCHAR,
    content TEXT,
    metrics_snapshot TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class DuckDBAnalytics:
    def __init__(self):
        self._conn: Optional["duckdb.DuckDBPyConnection"] = None
        self._ready = False

    async def initialize(self):
        try:
            import duckdb

            db_path = ai_settings.duckdb_absolute_path
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

            self._conn = duckdb.connect(db_path)
            self._create_schemas()
            self._migrate_if_needed()
            self._ready = True
            logger.info(f"DuckDB analytics initialized at {db_path}")
        except ImportError:
            logger.warning("duckdb not installed; analytical storage unavailable")
            self._ready = False
        except Exception as e:
            logger.error(f"DuckDB initialization failed: {e}")
            self._ready = False

    def _create_schemas(self):
        for schema in [
            TRADE_MEMORY_SCHEMA_V1,
            MARKET_MEMORY_SCHEMA,
            REGIME_HISTORY_SCHEMA,
            PREDICTION_LOG_SCHEMA,
            REFLECTION_LOG_SCHEMA,
        ]:
            self._conn.execute(schema)

    def _migrate_if_needed(self):
        try:
            cols = [row[1] for row in self._conn.execute(
                "PRAGMA table_info('trade_memory')"
            ).fetchall()]
            col_set = set(cols)
            v1_cols = {"prediction", "portfolio_state", "reflection_notes", "schema_version"}
            v2_cols = {"pnl", "pnl_pct", "exit_price", "exit_reason", "closed_at"}
            all_new = v1_cols | v2_cols
            missing = all_new - col_set
            col_types = {
                "prediction": "VARCHAR",
                "portfolio_state": "TEXT",
                "reflection_notes": "TEXT",
                "schema_version": "VARCHAR DEFAULT '1.0'",
                "pnl": "DOUBLE",
                "pnl_pct": "DOUBLE",
                "exit_price": "DOUBLE",
                "exit_reason": "VARCHAR",
                "closed_at": "TIMESTAMP",
            }
            for col in missing:
                self._conn.execute(f"ALTER TABLE trade_memory ADD COLUMN {col} {col_types[col]}")
                logger.info(f"Migrated trade_memory: added column {col}")
        except Exception as e:
            logger.warning(f"Migration check failed (may be normal for first init): {e}")

    def _require_conn(self):
        if not self._ready or self._conn is None:
            raise RuntimeError("DuckDB not initialized. Call initialize() first.")

    def execute(self, query: str, params: Optional[list] = None):
        self._require_conn()
        if params:
            return self._conn.execute(query, params)
        return self._conn.execute(query)

    def query_df(self, query: str, params: Optional[list] = None):
        self._require_conn()
        if params:
            return self._conn.execute(query, params).fetchdf()
        return self._conn.execute(query).fetchdf()

    def fetch_all(self, query: str, params: Optional[list] = None):
        self._require_conn()
        if params:
            return self._conn.execute(query, params).fetchall()
        return self._conn.execute(query).fetchall()

    def fetch_one(self, query: str, params: Optional[list] = None):
        self._require_conn()
        if params:
            return self._conn.execute(query, params).fetchone()
        return self._conn.execute(query).fetchone()

    def insert_trade_memory(self, trade: dict):
        self._require_conn()
        self._conn.execute(
            """
            INSERT OR REPLACE INTO trade_memory
            (trade_id, symbol, timestamp, market_regime, feature_snapshot,
             prediction, confidence, reasoning, outcome,
             portfolio_state, reflection_notes, schema_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade["trade_id"],
                trade.get("symbol") or trade.get("ticker", ""),
                trade.get("timestamp"),
                trade.get("market_regime"),
                trade.get("feature_snapshot"),
                trade.get("prediction"),
                trade.get("confidence"),
                trade.get("reasoning"),
                trade.get("outcome"),
                trade.get("portfolio_state"),
                trade.get("reflection_notes"),
                trade.get("schema_version", "1.0"),
            ],
        )

    def get_recent_trades(self, limit: int = 100) -> list:
        return self.fetch_all(
            "SELECT * FROM trade_memory ORDER BY created_at DESC LIMIT ?",
            params=[limit],
        )

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False
            logger.info("DuckDB analytics closed")
