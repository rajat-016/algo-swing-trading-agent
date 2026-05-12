from __future__ import annotations
from typing import Any
from dataclasses import dataclass

import numpy as np
import pandas as pd

from core.logging import logger


@dataclass
class HoldingVolatility:
    symbol: str
    daily_vol_pct: float
    annualized_vol_pct: float
    classification: str


@dataclass
class VolatilityReport:
    portfolio_daily_vol_pct: float
    portfolio_annualized_vol_pct: float
    holding_volatilities: list[HoldingVolatility]
    weighted_vol_pct: float
    high_vol_holdings: list[str]
    low_vol_holdings: list[str]


class VolatilityAnalyzer:
    def __init__(self, high_threshold_pct: float = 4.0,
                 low_threshold_pct: float = 1.5):
        self.high_threshold_pct = high_threshold_pct
        self.low_threshold_pct = low_threshold_pct

    def analyze(self, price_data: pd.DataFrame | None = None,
                holdings: list[dict[str, Any]] | None = None) -> VolatilityReport:
        if price_data is not None and not price_data.empty:
            return self._from_price_data(price_data, holdings)

        if holdings:
            return self._from_holdings(holdings)

        return self._empty_report()

    def _from_price_data(self, price_data: pd.DataFrame,
                         holdings: list[dict[str, Any]] | None = None) -> VolatilityReport:
        returns = price_data.pct_change().dropna()
        if returns.empty:
            return self._empty_report()

        daily_vols = returns.std()
        annualized_vols = daily_vols * np.sqrt(252)

        holding_vols = []
        high_vol = []
        low_vol = []
        for sym in price_data.columns:
            dv = float(daily_vols.get(sym, 0))
            av = float(annualized_vols.get(sym, 0))
            dv_pct = dv * 100
            cls = self._classify_volatility(dv_pct)
            holding_vols.append(HoldingVolatility(
                symbol=sym,
                daily_vol_pct=round(dv_pct, 4),
                annualized_vol_pct=round(av * 100, 4),
                classification=cls,
            ))
            if cls == "high":
                high_vol.append(sym)
            if cls == "low":
                low_vol.append(sym)

        weights = None
        if holdings:
            total_val = sum(
                float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0))
                for h in holdings
            )
            if total_val > 0:
                weights = {
                    h.get("symbol", "").upper().replace(".NS", ""):
                        float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0)) / total_val
                    for h in holdings
                }

        if weights and price_data.columns.isin(list(weights.keys())).all():
            w = np.array([weights.get(sym, 0) for sym in price_data.columns])
            w = w / w.sum()
            cov = returns.cov()
            portfolio_var = w.T @ cov.values @ w
            port_vol_daily = float(np.sqrt(portfolio_var)) if portfolio_var > 0 else 0.0
            weighted_vol = port_vol_daily * 100
        else:
            if daily_vols.empty:
                portfolio_daily = 0.0
            else:
                portfolio_daily = float(np.sqrt((daily_vols ** 2).mean()))
            weighted_vol = portfolio_daily * 100

        portfolio_daily = float(np.sqrt((daily_vols ** 2).mean())) if not daily_vols.empty else 0.0
        portfolio_annualized = portfolio_daily * np.sqrt(252)

        return VolatilityReport(
            portfolio_daily_vol_pct=round(portfolio_daily * 100, 4),
            portfolio_annualized_vol_pct=round(portfolio_annualized * 100, 4),
            holding_volatilities=holding_vols,
            weighted_vol_pct=round(weighted_vol, 4),
            high_vol_holdings=high_vol,
            low_vol_holdings=low_vol,
        )

    def _from_holdings(self, holdings: list[dict[str, Any]]) -> VolatilityReport:
        holding_vols = []
        high_vol = []
        low_vol = []
        for h in holdings:
            sym = h.get("symbol", "UNKNOWN")
            dv_pct = 2.0
            cls = self._classify_volatility(dv_pct)
            holding_vols.append(HoldingVolatility(
                symbol=sym,
                daily_vol_pct=dv_pct,
                annualized_vol_pct=round(dv_pct * np.sqrt(252), 4),
                classification=cls,
            ))
        return VolatilityReport(
            portfolio_daily_vol_pct=2.0,
            portfolio_annualized_vol_pct=round(2.0 * np.sqrt(252), 4),
            holding_volatilities=holding_vols,
            weighted_vol_pct=2.0,
            high_vol_holdings=high_vol,
            low_vol_holdings=low_vol,
        )

    def _classify_volatility(self, daily_vol_pct: float) -> str:
        if daily_vol_pct >= self.high_threshold_pct:
            return "high"
        if daily_vol_pct <= self.low_threshold_pct:
            return "low"
        return "medium"

    def _empty_report(self) -> VolatilityReport:
        return VolatilityReport(
            portfolio_daily_vol_pct=0.0,
            portfolio_annualized_vol_pct=0.0,
            holding_volatilities=[],
            weighted_vol_pct=0.0,
            high_vol_holdings=[],
            low_vol_holdings=[],
        )
