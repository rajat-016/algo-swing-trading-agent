import numpy as np
import pandas as pd
from typing import Dict, Optional, List


BREADTH_ANALYTICS_VERSION = "1.0.0"


def compute_breadth_analytics(
    universe_df: Optional[pd.DataFrame] = None,
    per_stock_df: Optional[pd.DataFrame] = None,
    pct_above_ma50: Optional[float] = None,
    pct_above_ma200: Optional[float] = None,
) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if per_stock_df is not None and "close" in per_stock_df.columns:
        close = per_stock_df["close"].values.astype(np.float64)
        if len(close) >= 50:
            ma50 = pd.Series(close).rolling(50).mean().values
            pct_50 = float(np.mean(close > ma50))
            result["pct_above_ma50"] = round(pct_50, 4)

        if len(close) >= 200:
            ma200 = pd.Series(close).rolling(200).mean().values
            pct_200 = float(np.mean(close > ma200))
            result["pct_above_ma200"] = round(pct_200, 4)

        if len(close) >= 20:
            returns = np.diff(np.log(close))
            if len(returns) > 0:
                adv = (returns > 0).sum()
                dec = (returns < 0).sum()
                total = adv + dec
                result["adv_decl_ratio"] = round(float(adv / total if total > 0 else 0.5), 4)
                result["adv_decl_line"] = round(float((adv - dec) / max(total, 1)), 4)

                cum_breadth = np.cumsum(np.where(returns > 0, 1, np.where(returns < 0, -1, 0)))
                result["cumulative_breadth"] = round(float(cum_breadth[-1] / max(abs(cum_breadth).max(), 1)), 4)

            if len(returns) >= 50:
                short_adv = (returns[-10:] > 0).sum()
                short_dec = (returns[-10:] < 0).sum()
                long_adv = (returns[-50:] > 0).sum()
                long_dec = (returns[-50:] < 0).sum()
                short_ratio = short_adv / max(short_adv + short_dec, 1)
                long_ratio = long_adv / max(long_adv + long_dec, 1)
                result["breadth_thrust"] = round(float(short_ratio - long_ratio), 4)

        if len(close) >= 40:
            returns = np.diff(np.log(close))
            if len(returns) >= 39:
                adv_20 = pd.Series((returns > 0).astype(float)).rolling(20).sum().values
                dec_20 = pd.Series((returns < 0).astype(float)).rolling(20).sum().values
                net_adv_20 = adv_20 - dec_20
                ema_fast = pd.Series(net_adv_20).ewm(span=10, adjust=False).mean().values
                ema_slow = pd.Series(net_adv_20).ewm(span=40, adjust=False).mean().values
                if len(ema_fast) > 0 and len(ema_slow) > 0:
                    mcclellan = ema_fast[-1] - ema_slow[-1]
                    result["mcclellan_oscillator"] = round(float(mcclellan / max(abs(net_adv_20).max(), 1)), 4)

        if len(close) >= 20:
            highs = pd.Series(close).rolling(20).max().values
            lows = pd.Series(close).rolling(20).min().values
            if len(highs) > 0:
                position = (close[-1] - lows[-1]) / (highs[-1] - lows[-1]) if highs[-1] != lows[-1] else 0.5
                result["breadth_position"] = round(float(position), 4)

        if pct_above_ma50 is not None:
            result["pct_above_ma50"] = round(float(pct_above_ma50), 4)
        if pct_above_ma200 is not None:
            result["pct_above_ma200"] = round(float(pct_above_ma200), 4)

    return result


def compute_breadth_from_universe(universe_returns: np.ndarray) -> Dict[str, float]:
    result: Dict[str, float] = {}
    if universe_returns is None or len(universe_returns) == 0:
        return result

    positive = (universe_returns > 0).sum()
    negative = (universe_returns < 0).sum()
    total = positive + negative

    if total > 0:
        result["universe_adv_decl_ratio"] = round(float(positive / total), 4)
        result["universe_breadth"] = round(float((positive - negative) / total), 4)

    if total > 0:
        result["universe_positive_pct"] = round(float(positive / total * 100), 2)
        result["universe_negative_pct"] = round(float(negative / total * 100), 2)

    return result
