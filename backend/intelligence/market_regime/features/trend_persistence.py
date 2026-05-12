import numpy as np
import pandas as pd
from typing import Dict, Optional


TREND_PERSISTENCE_VERSION = "1.0.0"


def compute_trend_persistence(df: pd.DataFrame) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values.astype(np.float64)
    if len(close) < 30:
        return result

    result["trend_persistence_adx_slope"] = _adx_slope(df)
    result["trend_persistence_ema_alignment"] = _ema_alignment_score(df)
    result["trend_persistence_trend_consistency"] = _trend_consistency(close, period=10)
    result["trend_persistence_macd_persistence"] = _macd_persistence(df)
    result["trend_persistence_lr_slope_stability"] = _lr_slope_stability(close)
    result["trend_persistence_choppiness"] = _choppiness_index(df)
    result["trend_persistence_directional"] = _directional_persistence(close)
    result["trend_persistence_trend_strength_ema"] = _trend_strength_vs_ema(close)
    result["trend_persistence_seq_consecutive"] = _consecutive_bars(close)
    result["trend_persistence_slope_consistency"] = _slope_consistency(close)

    return result


def _adx_slope(df: pd.DataFrame) -> float:
    if "high" not in df.columns or "low" not in df.columns or "close" not in df.columns:
        return 0.0
    if len(df) < 30:
        return 0.0

    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    close = df["close"].values.astype(np.float64)

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

    atr = pd.Series(tr).rolling(14).mean().values

    up_move = np.diff(high)
    down_move = np.diff(low)
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    if len(plus_dm) < 14:
        return 0.0

    di_plus = pd.Series(plus_dm).rolling(14).mean().values / (atr[1:] + 1e-10) * 100
    di_minus = pd.Series(minus_dm).rolling(14).mean().values / (atr[1:] + 1e-10) * 100

    dx = np.abs(di_plus - di_minus) / (di_plus + di_minus + 1e-10) * 100
    adx = pd.Series(dx).rolling(14).mean().values

    if len(adx) < 5:
        return 0.0

    recent = adx[-5:]
    slope = np.polyfit(np.arange(len(recent)), recent, 1)[0]
    normalized = max(-1.0, min(1.0, slope / 10.0))
    return round(float(normalized), 4)


def _ema_alignment_score(df: pd.DataFrame) -> float:
    required = {"close"}
    if not required.issubset(df.columns):
        return 0.0
    close = df["close"].values.astype(np.float64)
    if len(close) < 200:
        return 0.0

    ema_20 = pd.Series(close).ewm(span=20, adjust=False).mean().values
    ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    ema_200 = pd.Series(close).ewm(span=200, adjust=False).mean().values

    aligned = 0
    total = 0
    for i in range(199, len(close)):
        above_20 = close[i] > ema_20[i]
        above_50 = close[i] > ema_50[i]
        above_200 = close[i] > ema_200[i]
        ema_20_above_50 = ema_20[i] > ema_50[i]
        ema_50_above_200 = ema_50[i] > ema_200[i]

        if above_20 and above_50 and above_200 and ema_20_above_50 and ema_50_above_200:
            aligned += 1
        elif not above_20 and not above_50 and not above_200 and not ema_20_above_50 and not ema_50_above_200:
            aligned += 1
        total += 1

    if total == 0:
        return 0.0
    score = aligned / total
    return round(float(score), 4)


def _trend_consistency(close: np.ndarray, period: int = 10) -> float:
    if len(close) < period + 5:
        return 0.0
    returns = np.diff(np.log(close))
    if len(returns) < period:
        return 0.0
    recent = returns[-period:]
    positive = (recent > 0).sum()
    negative = (recent < 0).sum()
    max_side = max(positive, negative)
    consistency = max_side / period if period > 0 else 0
    return round(float(consistency), 4)


def _macd_persistence(df: pd.DataFrame) -> float:
    if "close" not in df.columns:
        return 0.0
    close = df["close"].values.astype(np.float64)
    if len(close) < 35:
        return 0.0

    ema_12 = pd.Series(close).ewm(span=12, adjust=False).mean().values
    ema_26 = pd.Series(close).ewm(span=26, adjust=False).mean().values
    macd_line = ema_12 - ema_26
    signal = pd.Series(macd_line).ewm(span=9, adjust=False).mean().values
    hist = macd_line - signal

    recent_hist = hist[-10:]
    if len(recent_hist) < 5:
        return 0.0
    positive = (recent_hist > 0).sum()
    negative = (recent_hist < 0).sum()
    max_side = max(positive, negative)
    persistence = max_side / len(recent_hist)
    hist_direction = 1 if recent_hist[-1] > recent_hist[0] else -1
    score = persistence * (1 if hist_direction > 0 else 1)
    return round(float(score), 4)


def _lr_slope_stability(close: np.ndarray) -> float:
    if len(close) < 30:
        return 0.0

    slopes = []
    for i in range(20, min(30, len(close))):
        segment = close[-i:]
        x = np.arange(len(segment))
        slope, _ = np.polyfit(x, segment, 1)
        slopes.append(slope)

    if len(slopes) < 2:
        return 0.0
    slopes = np.array(slopes)
    mean_slope = np.mean(slopes)
    if mean_slope == 0:
        return 0.0
    cv = np.std(slopes) / abs(mean_slope)
    stability = max(0.0, 1.0 - min(cv, 2.0) / 2.0)
    return round(float(stability), 4)


def _choppiness_index(df: pd.DataFrame) -> float:
    if "high" not in df.columns or "low" not in df.columns or "close" not in df.columns:
        return 0.0
    if len(df) < 20:
        return 0.0

    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    close_vals = df["close"].values.astype(np.float64)

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close_vals[i - 1]), abs(low[i] - close_vals[i - 1]))

    sum_tr = pd.Series(tr).rolling(14).sum().values
    highest = pd.Series(high).rolling(14).max().values
    lowest = pd.Series(low).rolling(14).min().values

    denominator = np.log(highest / lowest)
    with np.errstate(divide="ignore", invalid="ignore"):
        chop = 100 * np.log(sum_tr / (highest - lowest + 1e-10)) / (np.log(14) + 1e-10)
    chop = np.nan_to_num(chop, nan=50.0)
    latest = chop[-1] if len(chop) > 0 else 50
    latest = max(0, min(100, latest))
    normalized = 1.0 - abs(latest - 50) / 50
    return round(float(normalized), 4)


def _directional_persistence(close: np.ndarray) -> float:
    if len(close) < 20:
        return 0.0
    returns = np.diff(np.log(close))
    if len(returns) < 10:
        return 0.0
    recent = returns[-10:]
    cum_return = np.sum(recent)
    abs_sum = np.sum(np.abs(recent))
    if abs_sum == 0:
        return 0.0
    persistence = abs(cum_return) / abs_sum
    return round(float(persistence), 4)


def _trend_strength_vs_ema(close: np.ndarray) -> float:
    if len(close) < 50:
        return 0.0
    ema_50 = pd.Series(close).ewm(span=50, adjust=False).mean().values
    deviation = (close[-1] - ema_50[-1]) / ema_50[-1]
    return round(float(min(abs(deviation) * 10, 1.0)), 4)


def _consecutive_bars(close: np.ndarray) -> float:
    if len(close) < 10:
        return 0.0
    returns = np.diff(np.log(close))
    recent = returns[-10:]
    max_consec = 0
    current = 0
    for r in recent:
        if r > 0:
            current += 1
            max_consec = max(max_consec, current)
        else:
            current = 0
    neg_max = 0
    current = 0
    for r in recent:
        if r < 0:
            current += 1
            neg_max = max(neg_max, current)
        else:
            current = 0
    score = max(max_consec, neg_max) / 10
    return round(float(score), 4)


def _slope_consistency(close: np.ndarray) -> float:
    if len(close) < 30:
        return 0.0
    slopes = []
    for i in range(5, min(30, len(close)), 5):
        segment = close[-i:]
        x = np.arange(len(segment))
        try:
            s, _ = np.polyfit(x, segment, 1)
            slopes.append(s)
        except Exception:
            slopes.append(0)
    if len(slopes) < 2:
        return 0.0
    slopes = np.array(slopes)
    same_sign = (slopes > 0).sum() / len(slopes)
    other_sign = (slopes < 0).sum() / len(slopes)
    return round(float(max(same_sign, other_sign)), 4)
