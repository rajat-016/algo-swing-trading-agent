import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


class YahooFetcher:
    def __init__(self):
        self._session = yf.download

    def fetch_symbol_data(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
        interval: str = "1h",
    ) -> Optional[pd.DataFrame]:
        try:
            logger.info(f"Fetching {symbol} from {start_date} to {end_date} [{interval}]")

            df = yf.download(
                symbol,
                start=start_date,
                end=end_date,
                interval=interval,
                auto_adjust=False,
                progress=False,
            )

            if df is None or df.empty:
                logger.warning(f"No data returned for {symbol}")
                return None

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            df = df.reset_index()

            if "Date" in df.columns:
                df.rename(columns={"Date": "datetime"}, inplace=True)
            elif "Datetime" in df.columns:
                df.rename(columns={"Datetime": "datetime"}, inplace=True)

            required_cols = ["open", "high", "low", "close", "volume"]
            for col in required_cols:
                if col not in df.columns:
                    alt = col.capitalize()
                    if alt in df.columns:
                        df.rename(columns={alt: col}, inplace=True)

            df["datetime"] = pd.to_datetime(df["datetime"])
            df["symbol"] = symbol

            for col in ["open", "high", "low", "close"]:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

            df = df.dropna(subset=["close"])
            df = df[df["volume"] > 0]

            df = df.drop_duplicates(subset=["datetime"])
            df = df.sort_values("datetime").reset_index(drop=True)

            logger.info(f"Fetched {len(df)} rows for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to fetch {symbol}: {e}")
            return None

    def fetch_multiple_symbols(
        self,
        symbols: List[str],
        start_date: str,
        end_date: str,
        interval: str = "1h",
    ) -> List[pd.DataFrame]:
        all_data = []
        for symbol in symbols:
            df = self.fetch_symbol_data(symbol, start_date, end_date, interval)
            if df is not None and not df.empty:
                all_data.append(df)
        logger.info(f"Fetched data for {len(all_data)}/{len(symbols)} symbols")
        return all_data
