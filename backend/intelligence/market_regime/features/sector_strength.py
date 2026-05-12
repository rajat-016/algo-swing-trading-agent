import numpy as np
import pandas as pd
from typing import Dict, Optional, List


SECTOR_STRENGTH_VERSION = "1.0.0"


def compute_sector_strength(
    per_stock_df: Optional[pd.DataFrame] = None,
    nifty_return: Optional[float] = None,
    sector_returns: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if per_stock_df is not None and "close" in per_stock_df.columns:
        close = per_stock_df["close"].values.astype(np.float64)
        if len(close) >= 20:
            stock_return_20d = (close[-1] / close[-20]) - 1 if close[-20] > 0 else 0
            result["sector_relative_strength"] = round(float(stock_return_20d), 6)

            if nifty_return is not None:
                result["sector_vs_market"] = round(float(stock_return_20d - nifty_return), 6)

            if len(close) >= 60:
                ret_1m = (close[-1] / close[-20]) - 1 if close[-20] > 0 else 0
                ret_2m = (close[-20] / close[-40]) - 1 if close[-40] > 0 else 0
                ret_3m = (close[-40] / close[-60]) - 1 if close[-60] > 0 else 0
                result["sector_momentum_ranking"] = round(float(ret_1m - np.mean([ret_2m, ret_3m])), 6)
                result["sector_acceleration"] = round(float(ret_1m - ret_2m), 6)
        else:
            result["sector_relative_strength"] = 0.0

        if len(close) >= 20:
            nifty_aligned = nifty_return if nifty_return is not None else close[-20] / close[0] - 1 if close[0] > 0 else 0
            if nifty_aligned != 0:
                stock_returns = pd.Series(close).pct_change().dropna()
                nifty_series = pd.Series(
                    [nifty_aligned] * len(stock_returns)
                )
                corr = stock_returns.rolling(20).corr(nifty_series)
                result["sector_correlation"] = round(float(corr.iloc[-1]) if not corr.empty and not np.isnan(corr.iloc[-1]) else 0.0, 4)

    if sector_returns:
        returns = list(sector_returns.values())
        if returns:
            result["sector_dispersion"] = round(float(np.std(returns)), 6)
            result["sector_avg_return"] = round(float(np.mean(returns)), 6)
            result["sector_top_bottom_spread"] = round(float(max(returns) - min(returns)), 6)

            above_zero = sum(1 for r in returns if r > 0)
            result["sector_positive_ratio"] = round(float(above_zero / len(returns)), 4)

            result["sector_rotation_intensity"] = round(
                float(np.mean([abs(r) for r in returns])), 6
            )

            sorted_rets = sorted(returns)
            n = len(sorted_rets)
            top_quartile = np.mean(sorted_rets[-max(n // 4, 1):])
            bot_quartile = np.mean(sorted_rets[:max(n // 4, 1)])
            if abs(bot_quartile) > 1e-10:
                result["sector_lead_lag_ratio"] = round(float(top_quartile / abs(bot_quartile)), 4)
            else:
                result["sector_lead_lag_ratio"] = 1.0

    return result
