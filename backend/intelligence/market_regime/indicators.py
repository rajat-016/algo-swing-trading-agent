import pandas as pd
import numpy as np
from typing import Optional, Tuple


def compute_trend_indicators(
    df: pd.DataFrame,
    ema_short: int = 50,
    ema_long: int = 200,
) -> dict:
    result = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values
    if len(close) < ema_long:
        return result

    ema_s = _ema(close, ema_short)
    ema_l = _ema(close, ema_long)
    ema_diff_pct = (ema_s[-1] - ema_l[-1]) / ema_l[-1] if ema_l[-1] != 0 else 0
    result["ema_diff_pct"] = round(float(ema_diff_pct), 6)

    price_vs_ema = (close[-1] - ema_l[-1]) / ema_l[-1] if ema_l[-1] != 0 else 0
    result["price_vs_ema"] = round(float(price_vs_ema), 6)

    adx = _compute_adx(df, period=14)
    if adx is not None:
        result["adx"] = round(float(adx), 4)

    macd_hist = _compute_macd_histogram(close)
    if macd_hist is not None:
        result["macd_histogram"] = round(float(macd_hist), 6)

    return result


def compute_volatility_indicators(
    df: pd.DataFrame,
    high_vol_atr_pct: float = 0.03,
    low_vol_atr_pct: float = 0.015,
) -> dict:
    result = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values
    atr = _compute_atr(df, period=14)
    if atr is not None and close[-1] > 0:
        atr_pct = atr / close[-1]
        result["atr_pct"] = round(float(atr_pct), 6)

    bb_width_arr = _compute_bb_width(df, period=20, std_dev=2)
    if bb_width_arr is not None and len(bb_width_arr) > 0:
        bw = float(bb_width_arr[-1])
        result["bb_width"] = round(bw, 6)
        if not np.isnan(bw) and bw > 0:
            bb_ma = _sma(bb_width_arr, 20)
            if bb_ma is not None and not np.isnan(bb_ma[-1]) and bb_ma[-1] > 0:
                result["bb_width_ratio"] = round(float(bb_width_arr[-1] / bb_ma[-1]), 4)

    return result


def compute_volume_indicators(
    df: pd.DataFrame,
    breakout_volume_ratio: float = 1.5,
    event_volume_spike_ratio: float = 3.0,
) -> dict:
    result = {}

    if df.empty or "volume" not in df.columns:
        return result

    volume = df["volume"].values
    if len(volume) < 21:
        return result

    vol_ma = _sma(volume, 20)
    if vol_ma is not None and vol_ma[-1] > 0:
        vol_ratio = volume[-1] / vol_ma[-1]
        result["volume_ratio"] = round(float(vol_ratio), 4)
        result["is_spike"] = bool(vol_ratio >= event_volume_spike_ratio)

    return result


def compute_breadth_indicators(
    df: pd.DataFrame,
    ema_long: int = 200,
) -> dict:
    result = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values
    if len(close) >= ema_long:
        ema_l = _ema(close, ema_long)
        pct_above = float(np.mean(close > ema_l) * 100)
        result["pct_above_ma200"] = round(pct_above, 2)

    return result


def compute_momentum_indicators(df: pd.DataFrame) -> dict:
    result = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values
    if len(close) >= 14:
        rsi = _compute_rsi(close, period=14)
        if rsi is not None:
            result["rsi_14"] = round(float(rsi), 2)

    return result


def _ema(data: np.ndarray, period: int) -> np.ndarray:
    if len(data) < period:
        return data.astype(np.float64)
    data = data.astype(np.float64)
    multiplier = 2.0 / (period + 1)
    result = np.empty_like(data)
    result[:period] = np.nan
    result[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        result[i] = (data[i] - result[i - 1]) * multiplier + result[i - 1]
    result = _fill_forward(result)
    return result


def _sma(data: np.ndarray, period: int) -> Optional[np.ndarray]:
    if len(data) < period:
        return None
    data = data.astype(np.float64)
    result = np.empty_like(data)
    result[:period - 1] = np.nan
    for i in range(period - 1, len(data)):
        result[i] = np.mean(data[i - period + 1:i + 1])
    result = _fill_forward(result)
    return result


def _fill_forward(arr: np.ndarray) -> np.ndarray:
    result = arr.copy()
    last_valid = None
    for i in range(len(result)):
        if not np.isnan(result[i]):
            last_valid = result[i]
        elif last_valid is not None:
            result[i] = last_valid
    return result


def _compute_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        return None
    if len(df) < period + 1:
        return None

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(
            high[i] - low[i],
            abs(high[i] - close[i - 1]),
            abs(low[i] - close[i - 1]),
        )

    atr = np.mean(tr[-period:])
    return float(atr)


def _compute_adx(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    required = {"high", "low", "close"}
    if not required.issubset(df.columns):
        return None
    if len(df) < period * 2:
        return None

    high = df["high"].values
    low = df["low"].values
    close = df["close"].values

    up_move = np.diff(high)
    down_move = np.diff(low)
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    tr = np.zeros(len(df))
    tr[0] = high[0] - low[0]
    for i in range(1, len(df)):
        tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))

    atr_series = np.array([np.mean(tr[i - period + 1:i + 1]) for i in range(period - 1, len(tr))])

    if len(plus_dm) >= period:
        avg_plus = np.mean(plus_dm[-period:])
        avg_minus = np.mean(minus_dm[-period:])
        if atr_series[-1] > 0:
            di_plus = 100 * avg_plus / atr_series[-1]
            di_minus = 100 * avg_minus / atr_series[-1]
            dx = 100 * abs(di_plus - di_minus) / (di_plus + di_minus) if (di_plus + di_minus) > 0 else 0
            return float(dx)

    return None


def _compute_macd_histogram(close: np.ndarray) -> Optional[float]:
    if len(close) < 26:
        return None
    ema_12 = _ema(close, 12)
    ema_26 = _ema(close, 26)
    if np.isnan(ema_12[-1]) or np.isnan(ema_26[-1]):
        return None
    macd_line = ema_12[-1] - ema_26[-1]
    macd_series = ema_12 - ema_26
    signal_line = _ema(macd_series, 9)
    if signal_line is None or np.isnan(signal_line[-1]):
        return None
    return float(macd_line - signal_line[-1])


def _compute_bb_width(
    df: pd.DataFrame,
    period: int = 20,
    std_dev: float = 2.0,
) -> Optional[np.ndarray]:
    if "close" not in df.columns or len(df) < period:
        return None
    close = df["close"].values.astype(np.float64)
    middle = _sma(close, period)
    rolling_std = np.array([
        float(np.std(close[i - period + 1:i + 1])) if i >= period - 1 else np.nan
        for i in range(len(close))
    ]).astype(np.float64)
    upper = middle + std_dev * rolling_std
    lower = middle - std_dev * rolling_std
    width = (upper - lower) / middle
    width = _fill_forward(width)
    return width


def _compute_rsi(close: np.ndarray, period: int = 14) -> Optional[float]:
    if len(close) < period + 1:
        return None
    deltas = np.diff(close)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return float(100 - (100 / (1 + rs)))
