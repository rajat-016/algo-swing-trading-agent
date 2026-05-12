from __future__ import annotations
from typing import Any
from collections import defaultdict

import numpy as np
import pandas as pd

from core.logging import logger
from intelligence.trade_analysis.sector_map import SECTOR_CATEGORIES, SECTOR_MAP, get_sector
from intelligence.portfolio_analysis.correlation.models import (
    SectorCluster,
    SectorClusteringReport,
)


class SectorClusteringEngine:
    def __init__(self, high_threshold: float = 0.80):
        self.high_threshold = high_threshold

    def analyze(self, holdings: list[dict[str, Any]],
                price_data: pd.DataFrame | None = None,
                returns_data: pd.DataFrame | None = None) -> SectorClusteringReport:
        if not holdings:
            return self._empty_report()

        symbols = []
        for h in holdings:
            sym = (h.get("symbol") or "").upper().replace(".NS", "")
            symbols.append(sym)

        if price_data is not None and not price_data.empty:
            returns = price_data.pct_change().dropna()
        elif returns_data is not None and not returns_data.empty:
            returns = returns_data
        else:
            return self._sector_only_analysis(holdings, symbols)

        if returns.empty:
            return self._sector_only_analysis(holdings, symbols)

        sector_membership: dict[str, list[str]] = {}
        for sym in symbols:
            sec = get_sector(sym) or "Unknown"
            if sec not in sector_membership:
                sector_membership[sec] = []
            sector_membership[sec].append(sym)

        sectors = sorted(sector_membership.keys())

        aligned_symbols = [s for s in symbols if s in returns.columns]
        if len(aligned_symbols) < 2:
            return self._sector_only_analysis(holdings, symbols)

        aligned_returns = returns[aligned_symbols]
        corr_matrix = aligned_returns.corr()

        cluster_list = []
        for sec in sectors:
            sec_syms = [s for s in aligned_symbols if s in (sector_membership.get(sec) or [])]
            if len(sec_syms) < 1:
                continue

            other_syms = [s for s in aligned_symbols if s not in sec_syms]
            intra_corrs = []
            for i in range(len(sec_syms)):
                for j in range(i + 1, len(sec_syms)):
                    val = corr_matrix.loc[sec_syms[i], sec_syms[j]]
                    if not (np.isnan(val) or np.isinf(val)):
                        intra_corrs.append(val)

            inter_corrs = []
            for sym in sec_syms:
                for o in other_syms:
                    val = corr_matrix.loc[sym, o]
                    if not (np.isnan(val) or np.isinf(val)):
                        inter_corrs.append(val)

            intra_avg = float(np.mean(intra_corrs)) if intra_corrs else 0.0
            intra_min = float(np.min(intra_corrs)) if intra_corrs else 0.0
            intra_max = float(np.max(intra_corrs)) if intra_corrs else 0.0
            inter_avg = float(np.mean(inter_corrs)) if inter_corrs else 0.0

            total_val = sum(
                float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0))
                for h in holdings
            )
            sec_val = sum(
                float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0))
                for h in holdings
                if (h.get("symbol") or "").upper().replace(".NS", "") in sec_syms
            )
            conc_pct = (sec_val / total_val * 100) if total_val > 0 else 0.0

            cluster_list.append(SectorCluster(
                sector=sec,
                symbols=sec_syms,
                intra_sector_avg_corr=round(intra_avg, 4),
                intra_sector_min_corr=round(intra_min, 4),
                intra_sector_max_corr=round(intra_max, 4),
                inter_sector_avg_corr=round(inter_avg, 4),
                concentration_pct=round(conc_pct, 2),
                is_diversified=intra_avg < 0.7 if intra_corrs else True,
            ))

        n_sectors = len(sectors)
        inter_matrix = [[0.0] * n_sectors for _ in range(n_sectors)]
        cross_pairs = []

        for i, si in enumerate(sectors):
            for j, sj in enumerate(sectors):
                if i == j:
                    inter_matrix[i][j] = 1.0
                else:
                    si_syms = [s for s in aligned_symbols if s in (sector_membership.get(si) or [])]
                    sj_syms = [s for s in aligned_symbols if s in (sector_membership.get(sj) or [])]
                    vals = []
                    for a in si_syms:
                        for b in sj_syms:
                            if a in corr_matrix.columns and b in corr_matrix.columns:
                                val = corr_matrix.loc[a, b]
                                if not (np.isnan(val) or np.isinf(val)):
                                    vals.append(val)
                    avg_val = float(np.mean(vals)) if vals else 0.0
                    inter_matrix[i][j] = round(avg_val, 4)
                    if vals:
                        cross_pairs.append({
                            "sector_a": si, "sector_b": sj,
                            "avg_correlation": round(avg_val, 4),
                        })

        all_inter = [p["avg_correlation"] for p in cross_pairs]
        overall_inter_avg = float(np.mean(all_inter)) if all_inter else 0.0

        return SectorClusteringReport(
            clusters=cluster_list,
            inter_sector_matrix=inter_matrix,
            sectors=sectors,
            cross_sector_pairs=sorted(cross_pairs, key=lambda p: abs(p["avg_correlation"]), reverse=True),
            overall_inter_sector_avg=round(overall_inter_avg, 4),
        )

    def _sector_only_analysis(self, holdings: list[dict[str, Any]],
                               symbols: list[str]) -> SectorClusteringReport:
        sector_membership: dict[str, list[str]] = {}
        for sym in symbols:
            sec = get_sector(sym) or "Unknown"
            if sec not in sector_membership:
                sector_membership[sec] = []
            sector_membership[sec].append(sym)

        sectors = sorted(sector_membership.keys())
        n = len(sectors)
        inter_matrix = [[0.0] * n for _ in range(n)]
        for i in range(n):
            inter_matrix[i][i] = 1.0

        total_val = sum(
            float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0))
            for h in holdings
        ) or 1.0

        clusters = []
        for sec in sectors:
            sec_syms = sector_membership[sec]
            sec_val = sum(
                float(h.get("entry_quantity", 0)) * float(h.get("entry_price", 0))
                for h in holdings
                if (h.get("symbol") or "").upper().replace(".NS", "") in sec_syms
            )
            clusters.append(SectorCluster(
                sector=sec, symbols=sec_syms,
                intra_sector_avg_corr=0.0,
                intra_sector_min_corr=0.0,
                intra_sector_max_corr=0.0,
                inter_sector_avg_corr=0.0,
                concentration_pct=round(sec_val / total_val * 100, 2),
                is_diversified=True,
            ))

        return SectorClusteringReport(
            clusters=clusters,
            inter_sector_matrix=inter_matrix,
            sectors=sectors,
            cross_sector_pairs=[],
            overall_inter_sector_avg=0.0,
        )

    def _empty_report(self) -> SectorClusteringReport:
        return SectorClusteringReport(
            clusters=[], inter_sector_matrix=[], sectors=[],
            cross_sector_pairs=[], overall_inter_sector_avg=0.0,
        )
