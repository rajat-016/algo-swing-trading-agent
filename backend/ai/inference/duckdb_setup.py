import os
from loguru import logger
from typing import Optional
from ai.config.settings import ai_settings


TRADE_MEMORY_SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_memory (
    trade_id VARCHAR PRIMARY KEY,
    symbol VARCHAR NOT NULL,
    entry_price DOUBLE,
    exit_price DOUBLE,
    direction VARCHAR,
    confidence DOUBLE,
    regime VARCHAR,
    pnl DOUBLE,
    pnl_pct DOUBLE,
    entry_time TIMESTAMP,
    exit_time TIMESTAMP,
    reason_summary TEXT,
    features_snapshot TEXT,
    outcome VARCHAR,
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
            TRADE_MEMORY_SCHEMA,
            MARKET_MEMORY_SCHEMA,
            PREDICTION_LOG_SCHEMA,
            REFLECTION_LOG_SCHEMA,
        ]:
            self._conn.execute(schema)

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
            (trade_id, symbol, entry_price, exit_price, direction, confidence,
             regime, pnl, pnl_pct, entry_time, exit_time, reason_summary,
             features_snapshot, outcome)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade["trade_id"],
                trade["symbol"],
                trade.get("entry_price"),
                trade.get("exit_price"),
                trade.get("direction"),
                trade.get("confidence"),
                trade.get("regime"),
                trade.get("pnl"),
                trade.get("pnl_pct"),
                trade.get("entry_time"),
                trade.get("exit_time"),
                trade.get("reason_summary"),
                trade.get("features_snapshot"),
                trade.get("outcome"),
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
