import duckdb
import pandas as pd
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

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

class DuckDBManager:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_table()

    def _ensure_table(self):
        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.execute(OHLCV_SCHEMA)
            logger.debug(f"Table ensured at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise

    def insert_dataframe(self, df: pd.DataFrame) -> int:
        if df is None or df.empty:
            return 0

        required_cols = ["datetime", "open", "high", "low", "close", "volume", "symbol"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ohlcv_temp AS SELECT * FROM ohlcv WHERE 1=0
                """)

                conn.register("temp_df", df[required_cols])

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

        required_cols = ["datetime", "open", "high", "low", "close", "volume", "symbol"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Missing required column: {col}")

        try:
            with duckdb.connect(str(self.db_path)) as conn:
                conn.register("temp_df", df[required_cols])

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
            with duckdb.connect(str(self.db_path)) as conn:
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
            with duckdb.connect(str(self.db_path)) as conn:
                result = conn.execute("SELECT DISTINCT symbol FROM ohlcv ORDER BY symbol").fetchall()
                return [row[0] for row in result]
        except Exception as e:
            logger.error(f"Failed to get symbols: {e}")
            return []

    def get_date_range(self, symbol: Optional[str] = None) -> dict:
        try:
            with duckdb.connect(str(self.db_path)) as conn:
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
            with duckdb.connect(str(self.db_path)) as conn:
                result = conn.execute(
                    f"SELECT MAX(datetime) FROM ohlcv WHERE symbol = '{symbol}'"
                ).fetchone()
                if result and result[0]:
                    return pd.Timestamp(result[0])
                return None
        except Exception as e:
            logger.error(f"Failed to get latest date for {symbol}: {e}")
            return None
