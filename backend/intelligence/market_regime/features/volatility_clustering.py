import numpy as np
import pandas as pd
from typing import Dict, Optional


VOLATILITY_CLUSTER_VERSION = "1.0.0"


def compute_volatility_clustering(df: pd.DataFrame) -> Dict[str, float]:
    result: Dict[str, float] = {}

    if df.empty or "close" not in df.columns:
        return result

    close = df["close"].values.astype(np.float64)
    if len(close) < 30:
        return result

    returns = np.diff(np.log(close))
    squared_returns = returns ** 2
    abs_returns = np.abs(returns)

    result["vol_cluster_ljung_box"] = _ljung_box_statistic(returns, lags=10)
    result["vol_cluster_serial_corr"] = _serial_correlation(squared_returns, lag=5)
    result["vol_cluster_half_life"] = _volatility_half_life(returns)
    result["vol_cluster_hv_percentile"] = _hv_percentile(returns)

    parkinson_vol = _parkinson_volatility(df, window=20)
    if parkinson_vol is not None:
        result["vol_cluster_parkinson"] = round(float(parkinson_vol), 6)

    yz_vol = _yang_zhang_volatility(df, window=20)
    if yz_vol is not None:
        result["vol_cluster_yang_zhang"] = round(float(yz_vol), 6)

    result["vol_cluster_vol_of_vol"] = _vol_of_vol(returns, window=20)
    result["vol_cluster_regime_vol"] = _regime_vol_level(returns)
    result["vol_cluster_garch_signal"] = _garch_like_signal(returns)
    result["vol_cluster_vol_meanrev_speed"] = _vol_mean_reversion_speed(returns)

    tail_ratio = _tail_ratio(returns)
    if tail_ratio is not None:
        result["vol_cluster_tail_ratio"] = round(float(tail_ratio), 4)

    result["vol_cluster_skew_5d"] = round(float(_rolling_skew(returns, window=5)), 4)
    result["vol_cluster_kurtosis_20d"] = round(float(_rolling_kurtosis(returns, window=20)), 4)

    return result


def _ljung_box_statistic(returns: np.ndarray, lags: int = 10) -> float:
    if len(returns) < lags + 5:
        return 0.0
    n = len(returns)
    sq_rets = returns ** 2
    acf = [1.0]
    for k in range(1, lags + 1):
        if len(sq_rets) <= k:
            acf.append(0.0)
            continue
        mu = np.mean(sq_rets)
        num = np.mean((sq_rets[:-k] - mu) * (sq_rets[k:] - mu))
        denom = np.mean((sq_rets - mu) ** 2) + 1e-10
        acf.append(num / denom)
    acf = np.array(acf[1:])
    if np.any(np.isnan(acf)):
        return 0.0
    q_stat = n * (n + 2) * np.sum(acf / (n - np.arange(1, lags + 1) + 1e-10))
    q_stat = max(0.0, q_stat)
    lb_normalized = min(q_stat / (lags * 2), 1.0)
    return round(float(lb_normalized), 4)


def _serial_correlation(squared_returns: np.ndarray, lag: int = 5) -> float:
    if len(squared_returns) < lag + 5:
        return 0.0
    std = np.std(squared_returns)
    if std == 0:
        return 0.0
    corr = np.corrcoef(squared_returns[:-lag], squared_returns[lag:])
    if np.isnan(corr[0, 1]):
        return 0.0
    return round(float(abs(corr[0, 1])), 4)


def _volatility_half_life(returns: np.ndarray) -> float:
    n = min(len(returns), 252)
    if n < 20:
        return 0.0
    sq_rets = returns[-n:] ** 2
    try:
        autocorr = np.corrcoef(sq_rets[:-1], sq_rets[1:])
        if np.isnan(autocorr[0, 1]):
            return 0.0
        rho = abs(autocorr[0, 1])
        if rho >= 1:
            return float(n)
        hl = np.log(0.5) / np.log(rho)
        return round(float(min(hl, n)), 2)
    except Exception:
        return 0.0


def _hv_percentile(returns: np.ndarray) -> float:
    if len(returns) < 252:
        return 0.5
    recent_hv = np.std(returns[-20:]) * np.sqrt(252)
    rolling_hv = pd.Series(returns).rolling(20).std().dropna() * np.sqrt(252)
    if len(rolling_hv) < 10:
        return 0.5
    pct = (recent_hv > rolling_hv.values).mean()
    return round(float(pct), 4)


def _parkinson_volatility(df: pd.DataFrame, window: int = 20) -> Optional[float]:
    if "high" not in df.columns or "low" not in df.columns:
        return None
    high = df["high"].values.astype(np.float64)
    low = df["low"].values.astype(np.float64)
    if len(high) < window:
        return None
    hl_ratio = np.log(high[-window:] / low[-window:])
    parkinson = np.sqrt(np.mean(hl_ratio ** 2) / (4 * np.log(2)))
    return parkinson * np.sqrt(252)


def _yang_zhang_volatility(df: pd.DataFrame, window: int = 20) -> Optional[float]:
    required = {"open", "high", "low", "close"}
    if not required.issubset(df.columns):
        return None
    o = df["open"].values.astype(np.float64)
    h = df["high"].values.astype(np.float64)
    l = df["low"].values.astype(np.float64)
    c = df["close"].values.astype(np.float64)
    if len(o) < window:
        return None
    o_c = np.log(o[-window:] / c[-window - 1: -1]) if window < len(o) else np.log(o / (c[0] if len(c) > 0 else 1))
    c_c = np.log(c[-window:] / c[-window - 1: -1]) if window < len(c) else np.log(c / (c[0] if len(c) > 0 else 1))
    h_l = np.log(h[-window:] / l[-window:])
    o_h = np.log(o[-window:] / h[-window:])
    o_l = np.log(o[-window:] / l[-window:])
    k = 0.34 / (1.34 + (window + 1) / (window - 1))
    overnight = (1 / (window - 1)) * np.sum(o_c ** 2)
    open_close = (1 / (window - 1)) * np.sum(c_c ** 2)
    rs = (1 / (window - 1)) * np.sum(h_l ** 2 - (2 * np.log(2) - 1) * o_h ** 2 - (2 * np.log(2) - 1) * o_l ** 2)
    yz = np.sqrt(overnight + k * open_close + (1 - k) * rs)
    return yz * np.sqrt(252)


def _vol_of_vol(returns: np.ndarray, window: int = 20) -> float:
    if len(returns) < window * 2:
        return 0.0
    hv = pd.Series(returns).rolling(window).std() * np.sqrt(252)
    hv = hv.dropna().values
    if len(hv) < window:
        return 0.0
    vov = np.std(hv[-window:])
    return round(float(vov), 6)


def _regime_vol_level(returns: np.ndarray) -> float:
    if len(returns) < 50:
        return 0.5
    recent = np.std(returns[-10:])
    medium = np.std(returns[-50:])
    if medium == 0:
        return 0.5
    ratio = recent / medium
    return round(float(min(ratio, 3.0) / 3.0), 4)


def _garch_like_signal(returns: np.ndarray) -> float:
    if len(returns) < 20:
        return 0.0
    sq = returns ** 2
    r = np.corrcoef(sq[:-1], sq[1:])
    if np.isnan(r[0, 1]):
        return 0.0
    ac = abs(r[0, 1])
    if ac > 0.5:
        return round(float(min((ac - 0.5) * 2, 1.0)), 4)
    return 0.0


def _vol_mean_reversion_speed(returns: np.ndarray) -> float:
    if len(returns) < 40:
        return 0.5
    hv_short = pd.Series(returns).rolling(5).std().dropna()
    hv_long = pd.Series(returns).rolling(20).std().dropna()
    aligned = pd.concat([hv_short, hv_long], axis=1).dropna().values
    if len(aligned) < 5:
        return 0.5
    corr = np.corrcoef(aligned[:, 0], aligned[:, 1])
    if np.isnan(corr[0, 1]):
        return 0.5
    speed = 1.0 - abs(corr[0, 1])
    return round(float(min(speed * 2, 1.0)), 4)


def _tail_ratio(returns: np.ndarray) -> Optional[float]:
    if len(returns) < 100:
        return None
    p95 = np.percentile(returns, 95)
    p99 = np.percentile(returns, 99)
    n05 = np.percentile(returns, 5)
    n01 = np.percentile(returns, 1)
    upper_tail = abs(p99) / abs(p95) if abs(p95) > 0 else 1
    lower_tail = abs(n01) / abs(n05) if abs(n05) > 0 else 1
    return (upper_tail + lower_tail) / 2


def _rolling_skew(returns: np.ndarray, window: int = 5) -> float:
    if len(returns) < window:
        return 0.0
    window_data = returns[-window:]
    if np.std(window_data) == 0:
        return 0.0
    return float(pd.Series(window_data).skew())


def _rolling_kurtosis(returns: np.ndarray, window: int = 20) -> float:
    if len(returns) < window:
        return 0.0
    window_data = returns[-window:]
    if np.std(window_data) == 0:
        return 0.0
    return float(pd.Series(window_data).kurtosis())
