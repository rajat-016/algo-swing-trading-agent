from __future__ import annotations
from typing import Any
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from core.logging import logger


@dataclass
class CorrelationPair:
    symbol_a: str
    symbol_b: str
    correlation: float
    strength: str


@dataclass
class CorrelationCluster:
    symbols: list[str]
    avg_correlation: float
    min_correlation: float
    max_correlation: float


@dataclass
class CorrelationReport:
    pairs: list[CorrelationPair]
    clusters: list[CorrelationCluster]
    high_correlation_pairs: list[CorrelationPair]
    matrix: list[list[float]]
    symbols: list[str]


class CorrelationAnalyzer:
    def __init__(self, high_threshold: float = 0.80,
                 medium_threshold: float = 0.60,
                 min_trades: int = 5):
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold
        self.min_trades = min_trades

    def analyze(self, returns_data: pd.DataFrame | None = None,
                holdings: list[dict[str, Any]] | None = None,
                price_data: pd.DataFrame | None = None) -> CorrelationReport:
        if returns_data is not None and not returns_data.empty:
            return self._from_returns(returns_data)

        if price_data is not None and not price_data.empty:
            returns = price_data.pct_change().dropna()
            if returns.empty or returns.shape[1] < 2:
                return self._empty_report()
            return self._from_returns(returns)

        if holdings and len(holdings) >= 2:
            return self._from_holdings_fallback(holdings)

        return self._empty_report()

    def _from_returns(self, returns: pd.DataFrame) -> CorrelationReport:
        symbols = list(returns.columns)
        corr_matrix = returns.corr().values.tolist()

        pairs = []
        high_pairs = []
        n = len(symbols)
        for i in range(n):
            for j in range(i + 1, n):
                val = corr_matrix[i][j]
                val_clean = max(-1.0, min(1.0, val if not (np.isnan(val) or np.isinf(val)) else 0.0))
                strength = self._classify_correlation(val_clean)
                pair = CorrelationPair(symbols[i], symbols[j], round(val_clean, 4), strength)
                pairs.append(pair)
                if abs(val_clean) >= self.high_threshold:
                    high_pairs.append(pair)

        clusters = self._detect_clusters(corr_matrix, symbols)

        return CorrelationReport(
            pairs=sorted(pairs, key=lambda p: abs(p.correlation), reverse=True),
            clusters=clusters,
            high_correlation_pairs=high_pairs,
            matrix=corr_matrix,
            symbols=symbols,
        )

    def _from_holdings_fallback(self, holdings: list[dict[str, Any]]) -> CorrelationReport:
        symbols = [h.get("symbol", f"HOLDING_{i}") for i, h in enumerate(holdings)]
        n = len(symbols)
        identity = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        return CorrelationReport(
            pairs=[],
            clusters=[],
            high_correlation_pairs=[],
            matrix=identity,
            symbols=symbols,
        )

    def _detect_clusters(self, matrix: list[list[float]],
                         symbols: list[str]) -> list[CorrelationCluster]:
        n = len(symbols)
        if n < 2:
            return []

        adj = [[abs(matrix[i][j]) >= self.medium_threshold and i != j for j in range(n)]
               for i in range(n)]

        visited = set()
        clusters = []
        for i in range(n):
            if i in visited:
                continue
            component = self._bfs(i, adj, n)
            visited.update(component)
            if len(component) >= 2:
                comp_symbols = [symbols[idx] for idx in sorted(component)]
                corrs = []
                for a in component:
                    for b in component:
                        if a < b:
                            corrs.append(abs(matrix[a][b]))
                avg_c = float(np.mean(corrs)) if corrs else 0.0
                min_c = float(np.min(corrs)) if corrs else 0.0
                max_c = float(np.max(corrs)) if corrs else 0.0
                clusters.append(CorrelationCluster(
                    symbols=comp_symbols,
                    avg_correlation=round(avg_c, 4),
                    min_correlation=round(min_c, 4),
                    max_correlation=round(max_c, 4),
                ))

        return sorted(clusters, key=lambda c: c.avg_correlation, reverse=True)

    def _bfs(self, start: int, adj: list[list[bool]], n: int) -> set[int]:
        visited = set()
        queue = [start]
        while queue:
            node = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            for neighbor in range(n):
                if adj[node][neighbor] and neighbor not in visited:
                    queue.append(neighbor)
        return visited

    def _classify_correlation(self, val: float) -> str:
        abs_val = abs(val)
        if abs_val >= self.high_threshold:
            return "high"
        if abs_val >= self.medium_threshold:
            return "medium"
        return "low"

    def _empty_report(self) -> CorrelationReport:
        return CorrelationReport(
            pairs=[], clusters=[], high_correlation_pairs=[],
            matrix=[], symbols=[],
        )
