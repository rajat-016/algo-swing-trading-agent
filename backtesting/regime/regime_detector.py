"""
Market Regime Detection Module

Detects market regime (trending vs sideways) and volatility conditions.
Lightweight and fast - uses pre-computed indicators (EMA, ATR).
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class RegimeDetector:
    """
    Detects market regime based on EMA and ATR indicators.
    
    Regimes:
    - TRENDING: EMA50 > EMA200 (uptrend)
    - SIDEWAYS: EMA50 ≈ EMA200 (within threshold)
    - Volatility: Based on ATR as percentage of price
    """

    def __init__(
        self,
        ema_short: int = 50,
        ema_long: int = 200,
        sideways_threshold_pct: float = 0.02,  # 2% band for sideways detection
        high_vol_atr_pct: float = 0.03,  # 3% ATR/price = high vol
        low_vol_atr_pct: float = 0.015,  # 1.5% ATR/price = low vol
    ):
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.sideways_threshold_pct = sideways_threshold_pct
        self.high_vol_atr_pct = high_vol_atr_pct
        self.low_vol_atr_pct = low_vol_atr_pct

    def detect(
        self,
        df: pd.DataFrame,
        current_idx: int = -1,
    ) -> Dict:
        """
        Detect regime for the current bar.
        
        Args:
            df: DataFrame with columns: close, ema_50, ema_200, atr_14
            current_idx: Index to analyze (-1 for latest)
            
        Returns:
            Dict with keys: trend, volatility
        """
        if df.empty:
            return {"trend": "UNKNOWN", "volatility": "NORMAL"}

        idx = current_idx if current_idx >= 0 else len(df) - 1
        if idx >= len(df):
            idx = len(df) - 1

        row = df.iloc[idx]

        # Get indicator values
        close = row.get("close", 0)
        ema_50 = row.get("ema_50", None)
        ema_200 = row.get("ema_200", None)
        atr_14 = row.get("atr_14", None)

        # Default values
        trend = "UNKNOWN"
        volatility = "NORMAL"

        # Trend detection
        if ema_50 is not None and ema_200 is not None:
            ema_diff_pct = (ema_50 - ema_200) / ema_200

            if abs(ema_diff_pct) <= self.sideways_threshold_pct:
                trend = "SIDEWAYS"
            elif ema_50 > ema_200:
                trend = "TRENDING"  # Uptrend (simplified - could add DOWNTREND)
            else:
                trend = "TRENDING"  # Downtrend

        # Volatility detection
        if atr_14 is not None and close > 0:
            atr_pct = atr_14 / close

            if atr_pct >= self.high_vol_atr_pct:
                volatility = "HIGH"
            elif atr_pct <= self.low_vol_atr_pct:
                volatility = "LOW"
            else:
                volatility = "NORMAL"

        regime = {"trend": trend, "volatility": volatility}

        logger.debug(f"Regime detected: {regime}")
        return regime

    def detect_series(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Detect regime for entire series (vectorized).
        
        Returns DataFrame with 'regime_trend' and 'regime_volatility' columns.
        """
        if df.empty:
            return df

        result = df.copy()

        if "ema_50" in df.columns and "ema_200" in df.columns:
            ema_diff_pct = (df["ema_50"] - df["ema_200"]) / df["ema_200"]
            result["regime_trend"] = np.where(
                abs(ema_diff_pct) <= self.sideways_threshold_pct,
                "SIDEWAYS",
                np.where(df["ema_50"] > df["ema_200"], "TRENDING", "TRENDING")
            )

        if "atr_14" in df.columns and "close" in df.columns:
            atr_pct = df["atr_14"] / df["close"]
            result["regime_volatility"] = np.where(
                atr_pct >= self.high_vol_atr_pct,
                "HIGH",
                np.where(atr_pct <= self.low_vol_atr_pct, "LOW", "NORMAL")
            )

        return result
