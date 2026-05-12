import os
import duckdb
import pandas as pd
from typing import Optional, List
from pathlib import Path
from loguru import logger


OHLCV_SCHEMA = """
CREATE TABLE IF NOT EXISTS ohlcv (
    datetime TIMESTAMP,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume DOUBLE,
    symbol VARCHAR
);
"""

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

PREDICTION_LOG_ANALYTICS_SCHEMA = """
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

SHAP_EXPLANATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS shap_explanations (
    id INTEGER PRIMARY KEY,
    prediction_id VARCHAR,
    symbol VARCHAR NOT NULL,
    prediction_time TIMESTAMP,
    predicted_class VARCHAR,
    confidence DOUBLE,
    base_value DOUBLE,
    predicted_score DOUBLE,
    top_features TEXT,
    feature_attribution TEXT,
    shap_values_json TEXT,
    explainer_type VARCHAR,
    latency_seconds DOUBLE,
    model_version VARCHAR,
    feature_version VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

PORTFOLIO_INSIGHTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS portfolio_insights (
    id INTEGER PRIMARY KEY,
    snapshot_time TIMESTAMP,
    total_value DOUBLE,
    num_positions INTEGER,
    num_sectors INTEGER,
    top_holding_pct DOUBLE,
    top_3_holdings_pct DOUBLE,
    herfindahl_index DOUBLE,
    sector_exposures TEXT,
    capital_concentrations TEXT,
    correlation_pairs TEXT,
    correlation_clusters TEXT,
    portfolio_daily_vol_pct DOUBLE,
    portfolio_annualized_vol_pct DOUBLE,
    weighted_vol_pct DOUBLE,
    net_exposure_pct DOUBLE,
    directional_bias VARCHAR,
    risk_score DOUBLE,
    overall_risk_level VARCHAR,
    alerts TEXT,
    regime_label VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ANALYTICAL_SCHEMAS = [
    TRADE_MEMORY_SCHEMA_V1,
    MARKET_MEMORY_SCHEMA,
    REGIME_HISTORY_SCHEMA,
    PREDICTION_LOG_ANALYTICS_SCHEMA,
    REFLECTION_LOG_SCHEMA,
    SHAP_EXPLANATIONS_SCHEMA,
    PORTFOLIO_INSIGHTS_SCHEMA,
]

OHLCV_REQUIRED_COLS = ["datetime", "open", "high", "low", "close", "volume", "symbol"]


class AnalyticsDB:
    def __init__(self, db_path: Optional[str] = None):
        self._db_path = db_path
        self._conn: Optional["duckdb.DuckDBPyConnection"] = None
        self._ready = False

    def _resolve_path(self) -> str:
        if self._db_path:
            return str(self._db_path)
        try:
            from ai.config.settings import ai_settings
            return ai_settings.duckdb_absolute_path
        except ImportError:
            from core.config import get_settings
            return get_settings().duckdb_path

    def _get_conn(self):
        if self._conn is None:
            path = self._resolve_path()
            parent = os.path.dirname(path)
            if parent:
                os.makedirs(parent, exist_ok=True)
            self._conn = duckdb.connect(path)
            self._create_schemas()
            self._ready = True
        return self._conn

    async def initialize(self):
        try:
            self._get_conn()
            path = self._resolve_path()
            logger.info(f"AnalyticsDB initialized at {path}")
        except ImportError:
            logger.warning("duckdb not installed; analytical storage unavailable")
            self._ready = False
        except Exception as e:
            logger.error(f"AnalyticsDB initialization failed: {e}")
            self._ready = False

    def _create_schemas(self):
        conn = self._get_conn()
        conn.execute(OHLCV_SCHEMA)
        for schema in ANALYTICAL_SCHEMAS:
            conn.execute(schema)
        self._migrate_if_needed()

    def _migrate_if_needed(self):
        conn = self._get_conn()
        try:
            cols = [row[1] for row in conn.execute(
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
                conn.execute(f"ALTER TABLE trade_memory ADD COLUMN {col} {col_types[col]}")
                logger.info(f"Migrated trade_memory: added column {col}")
        except Exception as e:
            logger.warning(f"Migration check failed: {e}")

    def ensure_table(self, schema_sql: str):
        conn = self._get_conn()
        conn.execute(schema_sql)

    def execute(self, query: str, params: Optional[list] = None):
        conn = self._get_conn()
        if params:
            return conn.execute(query, params)
        return conn.execute(query)

    def query_df(self, query: str, params: Optional[list] = None) -> pd.DataFrame:
        conn = self._get_conn()
        if params:
            return conn.execute(query, params).fetchdf()
        return conn.execute(query).fetchdf()

    def fetch_all(self, query: str, params: Optional[list] = None) -> list:
        conn = self._get_conn()
        if params:
            return conn.execute(query, params).fetchall()
        return conn.execute(query).fetchall()

    def fetch_one(self, query: str, params: Optional[list] = None):
        conn = self._get_conn()
        if params:
            return conn.execute(query, params).fetchone()
        return conn.execute(query).fetchone()

    # ---- OHLCV operations (from backtesting DuckDBManager) ----

    def insert_dataframe(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0

        for col in OHLCV_REQUIRED_COLS:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        try:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlcv_temp AS SELECT * FROM ohlcv WHERE 1=0
            """)
            conn.register("temp_df", df[OHLCV_REQUIRED_COLS])
            conn.execute("""
                INSERT INTO ohlcv
                SELECT DISTINCT * FROM temp_df
            """)
            conn.execute("DROP TABLE IF EXISTS ohlcv_temp")
            conn.unregister("temp_df")

            count = len(df)
            logger.info(f"Inserted {count} records into DuckDB")
            return count

        except Exception as e:
            logger.error(f"Failed to insert data: {e}")
            raise

    def insert_dataframe_upsert(self, df: pd.DataFrame) -> dict:
        if df is None or df.empty:
            return {"inserted": 0, "skipped": 0}

        for col in OHLCV_REQUIRED_COLS:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        try:
            conn = self._get_conn()
            conn.register("temp_df", df[OHLCV_REQUIRED_COLS])

            existing_count = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT t.* FROM temp_df t
                    INNER JOIN ohlcv o
                        ON t.datetime = o.datetime
                        AND t.symbol = o.symbol
                )
            """).fetchone()[0]

            new_count = conn.execute("""
                SELECT COUNT(*) FROM (
                    SELECT t.* FROM temp_df t
                    LEFT JOIN ohlcv o
                        ON t.datetime = o.datetime
                        AND t.symbol = o.symbol
                    WHERE o.datetime IS NULL
                )
            """).fetchone()[0]

            if new_count > 0:
                conn.execute("""
                    INSERT INTO ohlcv
                    SELECT DISTINCT t.* FROM temp_df t
                    LEFT JOIN ohlcv o
                        ON t.datetime = o.datetime
                        AND t.symbol = o.symbol
                    WHERE o.datetime IS NULL
                """)

            conn.unregister("temp_df")

            result = {"inserted": int(new_count), "skipped": int(existing_count)}
            logger.info(f"Upsert complete: {result['inserted']} new, {result['skipped']} skipped")
            return result

        except Exception as e:
            logger.error(f"Failed to upsert data: {e}")
            raise

    def load_data(
        self,
        start_date: str,
        end_date: str,
        symbols: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        try:
            conn = self._get_conn()
            query = f"""
                SELECT * FROM ohlcv
                WHERE datetime >= '{start_date}' AND datetime <= '{end_date}'
            """
            if symbols:
                symbol_list = "', '".join(symbols)
                query += f" AND symbol IN ('{symbol_list}')"

            query += " ORDER BY symbol, datetime"

            df = conn.execute(query).fetchdf()
            df["datetime"] = pd.to_datetime(df["datetime"])
            logger.info(f"Loaded {len(df)} rows from DuckDB")
            return df

        except Exception as e:
            logger.error(f"Failed to load data: {e}")
            raise

    def get_symbols(self) -> List[str]:
        try:
            conn = self._get_conn()
            result = conn.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol").fetchall()
            return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            return []

    def get_date_range(self, symbol: Optional[str] = None) -> dict:
        try:
            conn = self._get_conn()
            query = "SELECT MIN(datetime) as min_date, MAX(datetime) as max_date, COUNT(*) as count FROM ohlcv"
            if symbol:
                query += f" WHERE symbol = '{symbol}'"

            result = conn.execute(query).fetchone()
            return {
                "min_date": result[0],
                "max_date": result[1],
                "count": result[2],
            }
        except Exception as e:
            logger.error(f"Failed to get date range: {e}")
            return {}

    def get_latest_date(self, symbol: str) -> Optional[pd.Timestamp]:
        try:
            conn = self._get_conn()
            result = conn.execute(
                f"SELECT MAX(datetime) FROM ohlcv WHERE symbol = '{symbol}'"
            ).fetchone()
            if result and result[0]:
                return pd.Timestamp(result[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get latest date for {symbol}: {e}")
            return None

    # ---- Trade memory operations (from backend DuckDBAnalytics) ----

    def insert_trade_memory(self, trade: dict):
        conn = self._get_conn()
        conn.execute(
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

    # ---- SHAP Explanations ----

    def store_shap_explanation(self, explanation: dict):
        conn = self._get_conn()
        import json as _json
        conn.execute(
            """
            INSERT INTO shap_explanations
            (prediction_id, symbol, prediction_time, predicted_class, confidence,
             base_value, predicted_score, top_features, feature_attribution,
             shap_values_json, explainer_type, latency_seconds, model_version, feature_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                explanation.get("prediction_id"),
                explanation.get("symbol", ""),
                explanation.get("prediction_time"),
                explanation.get("predicted_class"),
                explanation.get("confidence"),
                explanation.get("base_value"),
                explanation.get("predicted_score"),
                _json.dumps(explanation.get("top_features", {})),
                _json.dumps(explanation.get("feature_attribution", {})),
                _json.dumps(explanation.get("shap_values_json", {})),
                explanation.get("explainer_type"),
                explanation.get("latency_seconds"),
                explanation.get("model_version"),
                explanation.get("feature_version"),
            ],
        )

    def get_recent_explanations(self, limit: int = 20) -> list:
        return self.fetch_all(
            "SELECT * FROM shap_explanations ORDER BY created_at DESC LIMIT ?",
            params=[limit],
        )

    # ---- Lifecycle ----

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False
            logger.info("AnalyticsDB closed")
