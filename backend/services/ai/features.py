import numpy as np
import pandas as pd
from typing import List, Optional


class FeatureEngineer:
    def __init__(self):
        self._nifty_data = None
        self._use_cache = True

    def set_nifty_data(self, df: pd.DataFrame):
        """Set NIFTY data for relative strength calculation"""
        if df is not None and not df.empty:
            self._nifty_data = df.copy()

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty or "close" not in df.columns:
            return df

        result = df.copy()

        result = self._add_price_features(result)
        result = self._add_moving_averages(result)
        result = self._add_momentum_indicators(result)
        result = self._add_volatility_indicators(result)
        result = self._add_volume_features(result)
        result = self._add_strategy_features(result)
        result = self._add_candlestick_patterns(result)
        result = self._add_advanced_volatility(result)
        result = self._add_order_flow_features(result)
        result = self._add_market_context_features(result)
        result = self._add_price_action_features(result)

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

    def _add_strategy_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        result = self._add_trend_pullback_features(result)
        result = self._add_breakout_retest_features(result)
        result = self._add_stage_analysis_features(result)
        result = self._add_relative_strength_features(result)
        result = self._add_vcp_features(result)
        result = self._add_support_zone_features(result)
        result = self._add_multi_timeframe_features(result)

        return result

    def _add_trend_pullback_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns or "ema_20" not in df.columns:
            return df

        result = df.copy()

        result["ema_20_above_50"] = (result["ema_20"] > result["ema_50"]).astype(int)
        result["ema_20_slope"] = result["ema_20"].pct_change(5)
        result["pullback_pct"] = (result["ema_20"] - result["close"]) / result["ema_20"]
        result["pullback_to_ema_level"] = ((result["close"] < result["ema_20"]) & (result["close"] > result["ema_50"])).astype(int)

        swing_low = result["low"].rolling(20).min()
        result["support_level"] = swing_low
        result["support_distance"] = (result["close"] - swing_low) / result["close"]

        trend_strength = (result["ema_20"] - result["ema_50"]) / result["ema_50"]
        result["trend_strength"] = trend_strength

        return result

    def _add_breakout_retest_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        result["breakout_volume"] = result["volume"] / result["volume_sma_20"]

        result["resistance"] = result["high"].rolling(20).max()
        result["resistance_distance"] = (result["resistance"] - result["close"]) / result["close"]

        result["at_breakout"] = ((result["close"] > result["resistance"].shift(1)) & (result["close"].shift(1) <= result["resistance"].shift(1))).astype(int)

        result["retest_level"] = result["close"].where(result["close"] < result["resistance"] * 1.02)
        result["retest_holds"] = ((result["close"] > result["close"].shift(1).rolling(3).min()) & (result["close"] < result["resistance"])).astype(int)

        return result

    def _add_stage_analysis_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        if len(result) >= 150:
            result["weekly_ma_30"] = result["close"].ewm(span=150, adjust=False).mean()
            result["weekly_ma_slope"] = result["weekly_ma_30"].pct_change(20)

            above_weekly = (result["close"] > result["weekly_ma_30"]).astype(int)
            rising_weekly = (result["weekly_ma_slope"] > 0).astype(int)

            result["stage"] = 0
            result.loc[~above_weekly.astype(bool), "stage"] = 1
            result.loc[(above_weekly == 1) & (rising_weekly == 1), "stage"] = 2
            result.loc[(above_weekly == 0) & (rising_weekly == 0), "stage"] = 3

            result["stage_2_start"] = ((result["stage"] == 2) & (result["close"].pct_change(10) > 0.05)).astype(int)
        else:
            result["weekly_ma_30"] = result["ema_50"]
            result["weekly_ma_slope"] = result["ema_50"].pct_change(10)
            result["stage"] = 0
            result["stage_2_start"] = 0

        return result

    def _add_relative_strength_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        stock_return = result["close"].pct_change(20)
        result["vs_nifty_return"] = 0.0
        result["nifty_correlation"] = 0.0
        result["outperform_days"] = 15  # neutral default
        result["relative_strength"] = 0

        if self._nifty_data is not None and not self._nifty_data.empty:
            nifty = self._nifty_data.copy()
            nifty_close = nifty["close"]

            nifty_aligned = nifty_close.reindex(result.index, method='nearest')
            nifty_aligned = nifty_aligned.pct_change(20)

            result["vs_nifty_return"] = stock_return - nifty_aligned
            result["nifty_correlation"] = result["close"].rolling(window=20).corr(nifty_aligned)

            stock_above = stock_return > nifty_aligned
            result["outperform_days"] = stock_above.rolling(20).sum()

            result["relative_strength"] = (stock_return > nifty_aligned + 0.02).astype(int)

        return result

    def _add_vcp_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        result["daily_range"] = (result["high"] - result["low"]) / result["close"]
        result["range_ma_10"] = result["daily_range"].rolling(10).mean()

        max_range = result["daily_range"].rolling(40).max()
        result["range_contraction"] = result["daily_range"] / max_range

        result["tightness_score"] = 1 - (result["daily_range"] / result["range_ma_10"])

        tight_range = result["daily_range"] < (result["range_ma_10"] * 0.5)
        result["consolidation_days"] = tight_range.rolling(20).apply(lambda x: x.sum() if x.sum() > 5 else 0)

        result["vcp_signal"] = ((result["range_contraction"] < 0.5) & (result["consolidation_days"] > 3)).astype(int)

        return result

    def _add_support_zone_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        result["weekly_swing_low"] = result["low"].rolling(5).min()
        result["weekly_swing_high"] = result["high"].rolling(5).max()

        result["support_distance"] = (result["close"] - result["weekly_swing_low"]) / result["close"]

        is_hammer = ((result["close"] - result["low"]) > (result["high"] - result["close"]) * 2) & (result["close"] > result["open"])
        is_engulfing = (result["close"] > result["open"].shift(1)) & (result["open"] < result["close"].shift(1))

        result["reversal_candle"] = (is_hammer | is_engulfing).astype(int)

        result["near_support"] = (result["support_distance"] < 0.03).astype(int)

        return result

    def _add_multi_timeframe_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        if len(result) >= 50:
            result["weekly_ema_20"] = result["close"].ewm(span=20, adjust=False).mean()
            result["weekly_ema_50"] = result["close"].ewm(span=50, adjust=False).mean()

            result["weekly_trend"] = 0
            result.loc[result["weekly_ema_20"] > result["weekly_ema_50"], "weekly_trend"] = 1
            result.loc[result["weekly_ema_20"] < result["weekly_ema_50"], "weekly_trend"] = -1
        else:
            result["weekly_ema_20"] = result["ema_20"] if "ema_20" in result.columns else result["close"]
            result["weekly_ema_50"] = result["ema_50"] if "ema_50" in result.columns else result["close"]
            result["weekly_trend"] = 0

        daily_trend = 1 if result["ema_20"].iloc[-1] > result["ema_50"].iloc[-1] else -1 if len(result) >= 20 else 0
        result["daily_weekly_aligned"] = ((result["weekly_trend"] == 1) & (daily_trend == 1)).astype(int)

        return result

    def _add_candlestick_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns or "open" not in df.columns:
            return df

        result = df.copy()

        body = result["close"] - result["open"]
        upper_shadow = result["high"] - result[["close", "open"]].max(axis=1)
        lower_shadow = result[["close", "open"]].min(axis=1) - result["low"]
        full_body = abs(body)
        full_range = result["high"] - result["low"]

        result["doji"] = ((full_body <= full_range * 0.1) & (upper_shadow > full_body) & (lower_shadow > full_body)).astype(int)

        result["hammer"] = (
            (lower_shadow > full_body * 2) &
            (upper_shadow < full_body * 0.5) &
            (body > 0)
        ).astype(int)

        result["inverted_hammer"] = (
            (upper_shadow > full_body * 2) &
            (lower_shadow < full_body * 0.5) &
            (body > 0)
        ).astype(int)

        result["hanging_man"] = (
            (lower_shadow > full_body * 2) &
            (upper_shadow < full_body * 0.5) &
            (body < 0)
        ).astype(int)

        result["shooting_star"] = (
            (upper_shadow > full_body * 2) &
            (lower_shadow < full_body * 0.5) &
            (body < 0)
        ).astype(int)

        result["bullish_engulfing"] = (
            (result["close"].shift(1) < result["open"].shift(1)) &
            (result["close"] > result["open"]) &
            (result["close"] > result["open"].shift(1)) &
            (result["open"] < result["close"].shift(1))
        ).astype(int)

        result["bearish_engulfing"] = (
            (result["close"].shift(1) > result["open"].shift(1)) &
            (result["close"] < result["open"]) &
            (result["close"] < result["open"].shift(1)) &
            (result["open"] > result["close"].shift(1))
        ).astype(int)

        result["morning_star"] = (
            (result["close"].shift(2) < result["open"].shift(2)) &
            (abs(result["close"].shift(1) - result["open"].shift(1)) < abs(result["open"].shift(2) - result["close"].shift(2)) * 0.3) &
            (result["close"] > result["open"]) &
            (result["close"] > (result["open"].shift(2) + result["close"].shift(2)) / 2)
        ).astype(int)

        result["evening_star"] = (
            (result["close"].shift(2) > result["open"].shift(2)) &
            (abs(result["close"].shift(1) - result["open"].shift(1)) < abs(result["open"].shift(2) - result["close"].shift(2)) * 0.3) &
            (result["close"] < result["open"]) &
            (result["close"] < (result["open"].shift(2) + result["close"].shift(2)) / 2)
        ).astype(int)

        result["three_white_soldiers"] = (
            (result["close"] > result["open"]) &
            (result["close"].shift(1) > result["open"].shift(1)) &
            (result["close"].shift(2) > result["open"].shift(2)) &
            (result["close"] > result["close"].shift(1)) &
            (result["close"].shift(1) > result["close"].shift(2)) &
            (result["open"] > result["open"].shift(1)) &
            (result["open"].shift(1) > result["open"].shift(2))
        ).astype(int)

        result["three_black_crows"] = (
            (result["close"] < result["open"]) &
            (result["close"].shift(1) < result["open"].shift(1)) &
            (result["close"].shift(2) < result["open"].shift(2)) &
            (result["close"] < result["close"].shift(1)) &
            (result["close"].shift(1) < result["close"].shift(2)) &
            (result["open"] < result["open"].shift(1)) &
            (result["open"].shift(1) < result["open"].shift(2))
        ).astype(int)

        result["piercing_line"] = (
            (result["close"].shift(1) < result["open"].shift(1)) &
            (result["close"] > result["open"]) &
            (result["close"] > (result["open"].shift(1) + result["close"].shift(1)) / 2) &
            (result["open"] < result["close"].shift(1))
        ).astype(int)

        result["dark_cloud_cover"] = (
            (result["close"].shift(1) > result["open"].shift(1)) &
            (result["close"] < result["open"]) &
            (result["close"] < (result["open"].shift(1) + result["close"].shift(1)) / 2) &
            (result["open"] > result["close"].shift(1))
        ).astype(int)

        result["tweezer_bottom"] = (
            (result["low"] == result["low"].shift(1)) &
            (result["close"] > result["open"])
        ).astype(int)

        result["tweezer_top"] = (
            (result["high"] == result["high"].shift(1)) &
            (result["close"] < result["open"])
        ).astype(int)

        result["bullish_signal"] = (
            result["hammer"] |
            result["inverted_hammer"] |
            result["bullish_engulfing"] |
            result["morning_star"] |
            result["three_white_soldiers"] |
            result["piercing_line"] |
            result["tweezer_bottom"]
        ).astype(int)

        result["bearish_signal"] = (
            result["hanging_man"] |
            result["shooting_star"] |
            result["bearish_engulfing"] |
            result["evening_star"] |
            result["three_black_crows"] |
            result["dark_cloud_cover"] |
            result["tweezer_top"]
        ).astype(int)

        return result

    def _add_advanced_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        log_returns = np.log(result["close"] / result["close"].shift(1))
        result["historical_volatility_10"] = log_returns.rolling(10).std() * np.sqrt(252)
        result["historical_volatility_20"] = log_returns.rolling(20).std() * np.sqrt(252)
        result["historical_volatility_30"] = log_returns.rolling(30).std() * np.sqrt(252)
        result["hv_ratio"] = result["historical_volatility_10"] / result["historical_volatility_20"]

        result["volatility_regime"] = 0
        result.loc[result["historical_volatility_20"] > result["historical_volatility_20"].rolling(50).mean() * 1.5, "volatility_regime"] = 2
        result.loc[result["historical_volatility_20"] < result["historical_volatility_20"].rolling(50).mean() * 0.7, "volatility_regime"] = 1

        if "atr_14" in result.columns:
            result["kelly_lower"] = result["ema_20"] - (result["atr_14"] * 2)
            result["kelly_upper"] = result["ema_20"] + (result["atr_14"] * 2)
            result["kelly_mid"] = result["ema_20"]
            result["kelly_position"] = (result["close"] - result["kelly_lower"]) / (result["kelly_upper"] - result["kelly_lower"])
            result["kelly_squeeze"] = (result["close"] < result["kelly_lower"]).astype(int) | (result["close"] > result["kelly_upper"]).astype(int)

        for period in [20, 40]:
            result[f"donchian_mid_{period}"] = (result["high"].rolling(period).max() + result["low"].rolling(period).min()) / 2
            result[f"donchian_upper_{period}"] = result["high"].rolling(period).max()
            result[f"donchian_lower_{period}"] = result["low"].rolling(period).min()

        result["donchian_position"] = (result["close"] - result["donchian_lower_20"]) / (result["donchian_upper_20"] - result["donchian_lower_20"])

        result["atr_percent"] = result["atr_14"] / result["close"] * 100
        result["atr_ratio_14_21"] = result["atr_14"] / result["atr_21"]

        result["volatility_expansion"] = (result["historical_volatility_10"] > result["historical_volatility_20"] * 1.3).astype(int)
        result["volatility_contraction"] = (result["historical_volatility_10"] < result["historical_volatility_20"] * 0.7).astype(int)

        return result

    def _add_order_flow_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns or "volume" not in df.columns:
            return df

        result = df.copy()

        result["vwap"] = (result["typical_price"] * result["volume"]).cumsum() / result["volume"].cumsum()
        result["vwap_distance"] = (result["close"] - result["vwap"]) / result["close"]
        result["vwap_deviation"] = (result["close"] - result["vwap"]) / result["atr_14"]

        result["volume_weighted_price_change"] = result["returns"] * result["volume"]
        result["volume_price_trend"] = result["volume_weighted_price_change"].rolling(10).sum()

        intrabar_volume = result["volume"] / 5
        result["absorption_volume"] = (
            (result["close"] < result["open"]) &
            (result["volume"] > result["volume"].rolling(20).mean() * 1.5)
        ).astype(int)

        result["selling_volume"] = np.where(result["close"] < result["open"], result["volume"], 0)
        result["buying_volume"] = np.where(result["close"] > result["open"], result["volume"], 0)
        result["selling_volume_ratio"] = (
            result["selling_volume"].rolling(10).sum() /
            result["volume"].rolling(10).sum()
        )
        result["buying_volume_ratio"] = (
            result["buying_volume"].rolling(10).sum() /
            result["volume"].rolling(10).sum()
        )

        result["cumulative_delta"] = result["buying_volume"].cumsum() - result["selling_volume"].cumsum()
        result["delta_ratio"] = result["cumulative_delta"] / result["volume"].cumsum()

        result["volume_imbalance"] = result["buying_volume_ratio"] - result["selling_volume_ratio"]

        result["high_volume_node"] = (
            result["volume"] > result["volume"].rolling(20).mean() * 1.5
        ).astype(int)

        result["low_volume_node"] = (
            result["volume"] < result["volume"].rolling(20).mean() * 0.5
        ).astype(int)

        result["price_action"] = np.where(result["close"] > result["vwap"], 1, -1)

        return result

    def _add_market_context_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns:
            return df

        result = df.copy()

        result["nifty_bias"] = 0
        if self._nifty_data is not None and not self._nifty_data.empty:
            nifty = self._nifty_data.copy()
            nifty_close = nifty["close"].reindex(result.index, method='nearest')

            nifty_ema_20 = nifty_close.ewm(span=20, adjust=False).mean()
            nifty_ema_50 = nifty_close.ewm(span=50, adjust=False).mean()

            result["nifty_bias"] = np.where(nifty_ema_20 > nifty_ema_50, 1, -1)

            result["nifty_momentum"] = nifty_close.pct_change(5)
            result["nifty_volatility"] = nifty_close.pct_change().rolling(10).std()

        result["market_correlation"] = result["close"].rolling(20).corr(result["close"].shift(1)) if len(result) > 20 else 0.0

        result["relative_volume"] = (
            result["volume"] / result["volume"].rolling(20).mean()
        )

        result["price_correlation_5d"] = result["close"].rolling(5).corr(result["close"].shift(5))
        result["price_correlation_10d"] = result["close"].rolling(10).corr(result["close"].shift(10))
        result["price_correlation_20d"] = result["close"].rolling(20).corr(result["close"].shift(20))

        result["momentum_persistency"] = result["returns"].rolling(5).apply(
            lambda x: (x > 0).sum() if len(x) > 0 else 0
        )

        result["trend_persistency"] = (result["ema_20"] > result["ema_20"].shift(5)).rolling(10).apply(
            lambda x: (x == True).sum() if len(x) > 0 else 0
        )

        return result

    def _add_price_action_features(self, df: pd.DataFrame) -> pd.DataFrame:
        if "close" not in df.columns or "low" not in df.columns or "high" not in df.columns:
            return df

        result = df.copy()

        result["pivot"] = (result["high"] + result["low"] + result["close"]) / 3
        result["pivot_r1"] = 2 * result["pivot"] - result["low"]
        result["pivot_s1"] = 2 * result["pivot"] - result["high"]
        result["pivot_r2"] = result["pivot"] + (result["high"] - result["low"])
        result["pivot_s2"] = result["pivot"] - (result["high"] - result["low"])

        fib_levels = [0.236, 0.382, 0.5, 0.618, 0.786]
        for fib in fib_levels:
            range_20 = result["high"].rolling(20).max() - result["low"].rolling(20).min()
            result[f"fib_retrace_{int(fib * 1000)}"] = result["high"].rolling(20).max() - (range_20 * fib)
            result[f"fib_extension_{int(fib * 1000)}"] = result["low"].rolling(20).min() + (range_20 * fib)

        result["at_pivot_r1"] = (abs(result["close"] - result["pivot_r1"]) < result["atr_14"]).astype(int)
        result["at_pivot_s1"] = (abs(result["close"] - result["pivot_s1"]) < result["atr_14"]).astype(int)
        result["at_fib_382"] = (abs(result["close"] - result["fib_retrace_382"]) < result["atr_14"]).astype(int)
        result["at_fib_618"] = (abs(result["close"] - result["fib_retrace_618"]) < result["atr_14"]).astype(int)

        shift_close = result["close"].shift(1).fillna(result["close"])
        result["gap_up"] = np.where(
            result["open"] > shift_close,
            ((result["open"] - shift_close) / shift_close).fillna(0),
            0
        )
        result["gap_down"] = np.where(
            result["open"] < shift_close,
            ((shift_close - result["open"]) / shift_close).fillna(0),
            0
        )
        result["gap_size"] = abs(result["open"] - shift_close) / shift_close
        result["gap_size"] = result["gap_size"].fillna(0)
        result["gap_filled"] = (
            ((result["gap_up"] > 0) & (result["close"] < shift_close)) |
            ((result["gap_down"] > 0) & (result["close"] > shift_close))
        ).astype(int)

        result["inside_bar"] = (
            (result["high"] < result["high"].shift(1)) &
            (result["low"] > result["low"].shift(1))
        ).astype(int)

        result["outside_bar"] = (
            (result["high"] > result["high"].shift(1)) &
            (result["low"] < result["low"].shift(1))
        ).astype(int)

        result["close_position"] = (result["close"] - result["low"]) / (result["high"] - result["low"])

        result["body_to_range"] = abs(result["close"] - result["open"]) / (result["high"] - result["low"])

        result["upper_wick_ratio"] = (result["high"] - result[["close", "open"]].max(axis=1)) / (result["high"] - result["low"])
        result["lower_wick_ratio"] = (result[["close", "open"]].min(axis=1) - result["low"]) / (result["high"] - result["low"])

        result["intraday_return"] = (result["close"] - result["open"]) / result["open"]
        result["overnight_gap"] = (result["open"] - shift_close) / shift_close

        result["range_expansion_20"] = result["price_range"] / result["price_range"].rolling(20).mean()
        result["range_expansion_50"] = result["price_range"] / result["price_range"].rolling(50).mean()

        result["close_vs_high_20"] = (result["close"] - result["high"].rolling(20).max()) / result["close"]
        result["close_vs_low_20"] = (result["close"] - result["low"].rolling(20).min()) / result["close"]

        return result

    def get_feature_names(self) -> List[str]:
        base_features = [
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
        strategy_features = [
            "ema_20_above_50",
            "ema_20_slope",
            "pullback_pct",
            "pullback_to_ema_level",
            "support_level",
            "support_distance",
            "trend_strength",
            "breakout_volume",
            "resistance",
            "resistance_distance",
            "at_breakout",
            "retest_level",
            "retest_holds",
            "weekly_ma_30",
            "weekly_ma_slope",
            "stage",
            "stage_2_start",
            "vs_nifty_return",
            "nifty_correlation",
            "outperform_days",
            "relative_strength",
            "daily_range",
            "range_ma_10",
            "range_contraction",
            "tightness_score",
            "consolidation_days",
            "vcp_signal",
            "weekly_swing_low",
            "weekly_swing_high",
            "reversal_candle",
            "near_support",
            "weekly_ema_20",
            "weekly_ema_50",
            "weekly_trend",
            "daily_weekly_aligned",
        ]
        candlestick_features = [
            "doji",
            "hammer",
            "inverted_hammer",
            "hanging_man",
            "shooting_star",
            "bullish_engulfing",
            "bearish_engulfing",
            "morning_star",
            "evening_star",
            "three_white_soldiers",
            "three_black_crows",
            "piercing_line",
            "dark_cloud_cover",
            "tweezer_bottom",
            "tweezer_top",
            "bullish_signal",
            "bearish_signal",
        ]
        volatility_features = [
            "historical_volatility_10",
            "historical_volatility_20",
            "historical_volatility_30",
            "hv_ratio",
            "volatility_regime",
            "kelly_lower",
            "kelly_upper",
            "kelly_mid",
            "kelly_position",
            "kelly_squeeze",
            "donchian_mid_20",
            "donchian_upper_20",
            "donchian_lower_20",
            "donchian_mid_40",
            "donchian_upper_40",
            "donchian_lower_40",
            "donchian_position",
            "atr_percent",
            "atr_ratio_14_21",
            "volatility_expansion",
            "volatility_contraction",
        ]
        order_flow_features = [
            "vwap_distance",
            "vwap_deviation",
            "volume_weighted_price_change",
            "volume_price_trend",
            "absorption_volume",
            "selling_volume_ratio",
            "buying_volume_ratio",
            "cumulative_delta",
            "delta_ratio",
            "volume_imbalance",
            "high_volume_node",
            "low_volume_node",
            "price_action",
        ]
        market_context_features = [
            "nifty_bias",
            "nifty_momentum",
            "nifty_volatility",
            "market_correlation",
            "relative_volume",
            "price_correlation_5d",
            "price_correlation_10d",
            "price_correlation_20d",
            "momentum_persistency",
            "trend_persistency",
        ]
        price_action_features = [
            "pivot",
            "pivot_r1",
            "pivot_s1",
            "pivot_r2",
            "pivot_s2",
            "fib_retrace_236",
            "fib_retrace_382",
            "fib_retrace_500",
            "fib_retrace_618",
            "fib_retrace_786",
            "fib_extension_236",
            "fib_extension_382",
            "fib_extension_500",
            "fib_extension_618",
            "fib_extension_786",
            "at_pivot_r1",
            "at_pivot_s1",
            "at_fib_382",
            "at_fib_618",
            "gap_up",
            "gap_down",
            "gap_size",
            "gap_filled",
            "inside_bar",
            "outside_bar",
            "close_position",
            "body_to_range",
            "upper_wick_ratio",
            "lower_wick_ratio",
            "intraday_return",
            "overnight_gap",
            "range_expansion_20",
            "range_expansion_50",
            "close_vs_high_20",
            "close_vs_low_20",
        ]
        return base_features + strategy_features + candlestick_features + volatility_features + order_flow_features + market_context_features + price_action_features
