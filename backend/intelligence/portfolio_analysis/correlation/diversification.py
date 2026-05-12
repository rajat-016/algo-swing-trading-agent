from __future__ import annotations
from typing import Any

import numpy as np
import pandas as pd

from core.logging import logger
from intelligence.trade_analysis.sector_map import get_sector
from intelligence.portfolio_analysis.correlation.models import (
    DiversificationScore,
    DiversificationBreakdown,
)


class DiversificationScorer:
    def __init__(self, target_effective_n: float = 5.0,
                 target_sector_count: int = 3):
        self.target_effective_n = target_effective_n
        self.target_sector_count = target_sector_count

    def score(self, holdings: list[dict[str, Any]],
              price_data: pd.DataFrame | None = None,
              sector_clustering_report=None,
              total_capital: float | None = None) -> DiversificationScore:
        if not holdings or len(holdings) < 1:
            return self._empty_score()

        total_val = total_capital or sum(
            abs(float(h.get("entry_quantity", 0))) * float(h.get("entry_price", 0))
            for h in holdings
        ) or 1.0

        n_holdings = len(holdings)
        stocks = [(h.get("symbol") or "").upper().replace(".NS", "") for h in holdings]

        sectors = set()
        for s in stocks:
            sec = get_sector(s)
            if sec:
                sectors.add(sec)
        n_sectors = len(sectors)

        avg_corr = 0.0
        if price_data is not None and not price_data.empty and n_holdings >= 2:
            aligned = [s for s in stocks if s in price_data.columns]
            if len(aligned) >= 2:
                returns = price_data[aligned].pct_change().dropna()
                corr = returns.corr()
                vals = []
                col_list = list(corr.columns)
                for i in range(len(col_list)):
                    for j in range(i + 1, len(col_list)):
                        v = corr.iloc[i, j]
                        if not (np.isnan(v) or np.isinf(v)):
                            vals.append(abs(v))
                avg_corr = float(np.mean(vals)) if vals else 0.0

        if avg_corr > 0:
            effective_n = (1 + (n_holdings - 1) * avg_corr) / avg_corr if avg_corr > 0 else float(n_holdings)
        else:
            effective_n = float(n_holdings)

        weights = []
        for h in holdings:
            val = abs(float(h.get("entry_quantity", 0))) * float(h.get("entry_price", 0))
            weights.append(val / total_val)
        weights_sum_sq = sum(w ** 2 for w in weights)
        hhi_effective_n = 1.0 / weights_sum_sq if weights_sum_sq > 0 else float(n_holdings)

        eff_n = min(hhi_effective_n, effective_n)

        pair_corr_score = max(0, 100 * (1 - avg_corr / 0.8))

        sec_score = min(100, (n_sectors / self.target_sector_count) * 100)

        conc_penalty = 0.0
        holdings_sorted = sorted(
            [(h, abs(float(h.get("entry_quantity", 0))) * float(h.get("entry_price", 0)) / total_val)
             for h in holdings],
            key=lambda x: x[1], reverse=True,
        )
        top_pct = holdings_sorted[0][1] if holdings_sorted else 0
        if top_pct > 0.30:
            conc_penalty = (top_pct - 0.30) * 100

        eff_n_score = min(100, (eff_n / self.target_effective_n) * 100)

        breakdown = [
            DiversificationBreakdown(
                component="Effective N", value=round(eff_n, 2),
                score=round(eff_n_score, 1), weight=0.30,
                status="good" if eff_n_score >= 70 else "fair" if eff_n_score >= 40 else "poor",
            ),
            DiversificationBreakdown(
                component="Average Correlation", value=round(avg_corr, 4),
                score=round(pair_corr_score, 1), weight=0.25,
                status="good" if pair_corr_score >= 70 else "fair" if pair_corr_score >= 40 else "poor",
            ),
            DiversificationBreakdown(
                component="Sector Diversification", value=n_sectors,
                score=round(sec_score, 1), weight=0.25,
                status="good" if sec_score >= 70 else "fair" if sec_score >= 40 else "poor",
            ),
            DiversificationBreakdown(
                component="Concentration Penalty", value=round(top_pct * 100, 1),
                score=round(max(0, 100 - conc_penalty), 1), weight=0.20,
                status="good" if conc_penalty <= 5 else "fair" if conc_penalty <= 15 else "poor",
            ),
        ]

        total_score = sum(b.score * b.weight for b in breakdown)

        return DiversificationScore(
            effective_n=round(eff_n, 2),
            avg_pairwise_correlation=round(avg_corr, 4),
            sector_diversification_score=round(sec_score, 1),
            concentration_penalty=round(conc_penalty, 1),
            regime_context_score=round(total_score, 1),
            overall_score=round(total_score, 1),
            breakdown=breakdown,
            total_holdings=n_holdings,
            num_sectors=n_sectors,
        )

    def _empty_score(self) -> DiversificationScore:
        return DiversificationScore(
            effective_n=0.0, avg_pairwise_correlation=0.0,
            sector_diversification_score=0.0, concentration_penalty=0.0,
            regime_context_score=0.0, overall_score=0.0,
            breakdown=[], total_holdings=0, num_sectors=0,
        )
