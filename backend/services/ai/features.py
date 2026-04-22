import numpy as np
import pandas as pd
from typing import List, Optional


class FeatureEngineer:
    def __init__(self):
        pass

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "close" not in df.columns:
            return df

        result = df.copy()

        result = self._add_price_features(result)
        result = self._add_moving_averages(result)
        result = self._add_momentum_indicators(result)
        result = self._add_volatility_indicators(result)
        result = self._add_volume_features(result)

        return result

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()

        result["returns"] = result["close"].pct_change()
        result["log_returns"] = np.log(result["close"] / result["close"].shift(1))
        result["price_change"] = result["close"] - result["open"]
        result["price_range"] = result["high"] - result["low"]
        result["hl_ratio"] = result["high"] / result["low"]
        result["co_ratio"] = result["close"] / result["open"]

        result["typical_price"] = (result["high"] + result["low"] + result["close"]) / 3
        result["weighted_price"] = (result["high"] + result["low"] + 2 * result["close"]) / 4

        for period in [5, 10, 20]:
            result[f"returns_{period}d"] = result["close"].pct_change(period)

        return result

    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        for window in [5, 10, 20, 50, 100, 200, 12, 26]:
            result[f"sma_{window}"] = result["close"].rolling(window=window).mean()
            result[f"ema_{window}"] = result["close"].ewm(span=window, adjust=False).mean()

        result["sma_5_20_diff"] = result["sma_5"] - result["sma_20"]
        result["sma_20_50_diff"] = result["sma_20"] - result["sma_50"]
        result["sma_50_200_diff"] = result["sma_50"] - result["sma_200"]

        for window in [5, 20, 50]:
            result[f"price_to_sma_{window}"] = result["close"] / result[f"sma_{window}"]

        return result

    def _add_momentum_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        delta = result["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        for period in [7, 14, 21]:
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss
            result[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        result["macd"] = result["ema_12"] - result["ema_26"]
        result["macd_signal"] = result["macd"].ewm(span=9, adjust=False).mean()
        result["macd_hist"] = result["macd"] - result["macd_signal"]

        for period in [12, 26]:
            result[f"momentum_{period}"] = result["close"] / result["close"].shift(period)

        result["roc"] = ((result["close"] - result["close"].shift(10)) / result["close"].shift(10)) * 100

        return result

    def _add_volatility_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        high_low = result["high"] - result["low"]
        high_close = abs(result["high"] - result["close"].shift())
        low_close = abs(result["low"] - result["close"].shift())

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        for period in [7, 14, 21]:
            result[f"atr_{period}"] = true_range.rolling(window=period).mean()

        for period in [5, 20, 50]:
            result[f"stddev_{period}"] = result["close"].rolling(window=period).std()

        result["bb_upper"] = result["sma_20"] + (result["stddev_20"] * 2)
        result["bb_lower"] = result["sma_20"] - (result["stddev_20"] * 2)
        result["bb_position"] = (result["close"] - result["bb_lower"]) / (result["bb_upper"] - result["bb_lower"])

        return result

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "volume" not in df.columns:
            return df

        result = df.copy()

        for window in [5, 20]:
            result[f"volume_sma_{window}"] = result["volume"].rolling(window=window).mean()
        result["volume_ratio"] = result["volume"] / result["volume_sma_20"]

        result["obv"] = (np.sign(result["close"].diff()) * result["volume"]).cumsum()

        result["vwap"] = (
            (result["typical_price"] * result["volume"]).rolling(window=20).sum()
            / result["volume"].rolling(window=20).sum()
        )

        result["volume_price_correlation"] = (
            result["close"].rolling(window=20).corr(result["volume"])
        )

        return result

    def get_feature_names(self) -> List[str]:
        return [
            "returns",
            "log_returns",
            "price_change",
            "price_range",
            "hl_ratio",
            "co_ratio",
            "returns_5d",
            "returns_10d",
            "returns_20d",
            "sma_5",
            "sma_10",
            "sma_20",
            "sma_50",
            "sma_100",
            "sma_200",
            "sma_5_20_diff",
            "sma_20_50_diff",
            "sma_50_200_diff",
            "price_to_sma_5",
            "price_to_sma_20",
            "price_to_sma_50",
            "rsi_7",
            "rsi_14",
            "rsi_21",
            "macd",
            "macd_signal",
            "macd_hist",
            "momentum_12",
            "momentum_26",
            "roc",
            "atr_7",
            "atr_14",
            "atr_21",
            "stddev_5",
            "stddev_20",
            "stddev_50",
            "bb_upper",
            "bb_lower",
            "bb_position",
            "volume_sma_5",
            "volume_sma_20",
            "volume_ratio",
            "obv",
            "vwap",
            "volume_price_correlation",
        ]
