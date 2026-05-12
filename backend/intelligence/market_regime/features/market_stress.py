import numpy as np
import pandas as pd
from typing import Dict, Optional


MARKET_STRESS_VERSION = "1.0.0"


def compute_market_stress(
    df: Optional[pd.DataFrame] = None,
    vix_level: Optional[float] = None,
    vix_change: Optional[float] = None,
    put_call_ratio: Optional[float] = None,
) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if vix_level is not None:
        result["stress_vix_level"] = round(float(vix_level), 4)
        normalised_vix = max(0.0, min(1.0, (vix_level - 10) / 40))
        result["stress_vix_normalised"] = round(float(normalised_vix), 4)

    if vix_change is not None:
        result["stress_vix_change"] = round(float(vix_change), 6)

    if put_call_ratio is not None:
        result["stress_pcr_gauge"] = round(float(put_call_ratio), 4)
        if put_call_ratio > 1.0:
            result["stress_fear_gauge"] = round(float(min((put_call_ratio - 1.0) * 2, 1.0)), 4)
        elif put_call_ratio < 0.5:
            result["stress_complacency_gauge"] = round(float(min((0.5 - put_call_ratio) * 2, 1.0)), 4)

    if df is None or df.empty:
        return result

    if "close" not in df.columns:
        return result

    close = df["close"].values.astype(np.float64)
    if len(close) < 20:
        return result

    returns = np.diff(np.log(close))
    if len(returns) < 5:
        return result

    result["stress_max_drawdown_20d"] = _max_drawdown(close[-20:])
    result["stress_max_drawdown_60d"] = _max_drawdown(close[-60:]) if len(close) >= 60 else 0.0

    result["stress_skew_5d"] = _skew_estimate(returns[-5:])
    result["stress_skew_20d"] = _skew_estimate(returns[-20:])

    result["stress_realized_vol_20d"] = _realized_vol(returns[-20:]) if len(returns) >= 20 else 0.0

    if "volume" in df.columns:
        vol = df["volume"].values.astype(np.float64)
        result["stress_volume_spike"] = _volume_spike(vol, close)

    if len(close) >= 50:
        result["stress_below_ma50"] = _below_ma(close[-1], close, 50)
    if len(close) >= 200:
        result["stress_below_ma200"] = _below_ma(close[-1], close, 200)

    if len(close) >= 10:
        result["stress_consecutive_losses"] = _consecutive_losses(returns[-10:])

    if len(close) >= 252:
        annualized = np.std(returns[-252:]) * np.sqrt(252)
    elif len(close) >= 60:
        annualized = np.std(returns[-60:]) * np.sqrt(252)
    else:
        annualized = np.std(returns) * np.sqrt(252)
    result["stress_annualized_vol"] = round(float(annualized), 6)

    if len(returns) >= 20:
        max_r = np.max(returns[-20:])
        min_r = np.min(returns[-20:])
        result["stress_range_20d"] = round(float(max_r - min_r), 6)

    if len(close) >= 20:
        high_20 = np.max(close[-20:])
        low_20 = np.min(close[-20:])
        dist_from_high = (high_20 - close[-1]) / close[-1]
        dist_from_low = (close[-1] - low_20) / close[-1]
        result["stress_distance_from_high"] = round(float(dist_from_high), 6)
        result["stress_distance_from_low"] = round(float(dist_from_low), 6)

    return result


def _max_drawdown(prices: np.ndarray) -> float:
    if len(prices) < 5:
        return 0.0
    peak = np.maximum.accumulate(prices)
    drawdown = (prices - peak) / peak
    mdd = np.min(drawdown)
    return round(float(abs(mdd)), 6)


def _skew_estimate(rets: np.ndarray) -> float:
    if len(rets) < 5:
        return 0.0
    s = np.std(rets)
    if s == 0:
        return 0.0
    n = len(rets)
    skew = (n / ((n - 1) * (n - 2))) * np.sum(((rets - np.mean(rets)) / s) ** 3)
    if np.isnan(skew):
        return 0.0
    return round(float(skew), 4)


def _realized_vol(rets: np.ndarray) -> float:
    if len(rets) < 5:
        return 0.0
    rv = np.std(rets) * np.sqrt(252)
    return round(float(rv), 6)


def _volume_spike(volume: np.ndarray, close: np.ndarray) -> float:
    if len(volume) < 20:
        return 0.0
    avg_vol = np.mean(volume[-20:])
    if avg_vol == 0:
        return 0.0
    spike_ratio = volume[-1] / avg_vol
    spike_score = min(spike_ratio / 5.0, 1.0)
    if len(close) >= 2:
        price_move = abs(close[-1] / close[-2] - 1)
        spike_score *= min(price_move * 20, 1.5)
    return round(float(spike_score), 4)


def _below_ma(current_price: float, prices: np.ndarray, period: int) -> float:
    if len(prices) < period:
        return 0.0
    ma = np.mean(prices[-period:])
    if ma == 0:
        return 0.0
    dist = (ma - current_price) / ma
    return round(float(max(dist, 0)), 6)


def _consecutive_losses(rets: np.ndarray) -> float:
    max_losses = 0
    current = 0
    for r in rets:
        if r < 0:
            current += 1
            max_losses = max(max_losses, current)
        else:
            current = 0
    return round(float(max_losses / len(rets)), 4)
