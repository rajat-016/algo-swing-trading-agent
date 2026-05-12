from __future__ import annotations
from typing import Any
from collections import defaultdict

import numpy as np
import pandas as pd

from core.logging import logger
from intelligence.trade_analysis.sector_map import get_sector, are_related_sectors
from intelligence.portfolio_analysis.correlation.models import (
    InstabilityAlert,
    InstabilityReport,
)


class InstabilityAnalyzer:
    def __init__(self, high_threshold: float = 0.80,
                 change_threshold: float = 0.15,
                 lookback_windows: int = 3,
                 regime_transition_sensitivity: float = 0.10):
        self.high_threshold = high_threshold
        self.change_threshold = change_threshold
        self.lookback_windows = lookback_windows
        self.regime_transition_sensitivity = regime_transition_sensitivity

    def analyze(self, price_data: pd.DataFrame | None = None,
                returns_data: pd.DataFrame | None = None,
                holdings: list[dict[str, Any]] | None = None,
                rolling_result=None) -> InstabilityReport:
        if rolling_result is not None:
            return self._from_rolling(rolling_result, holdings)

        if returns_data is not None and not returns_data.empty:
            df = returns_data
        elif price_data is not None and not price_data.empty:
            df = price_data.pct_change().dropna()
        else:
            return self._empty_report()

        if df.empty or df.shape[1] < 2:
            return self._empty_report()

        alerts = []
        symbols = list(df.columns)
        n = len(symbols)

        full_corr = df.corr()
        half = len(df) // 2
        first_half = df.iloc[:half].corr() if half >= 10 else full_corr
        second_half = df.iloc[half:].corr() if half >= 10 else full_corr

        for i in range(n):
            for j in range(i + 1, n):
                si, sj = symbols[i], symbols[j]
                curr_val = full_corr.iloc[i, j]
                prev_val = first_half.iloc[i, j] if half >= 10 else curr_val

                if np.isnan(curr_val) or np.isnan(prev_val):
                    continue
                curr_val = max(-1.0, min(1.0, curr_val))
                prev_val = max(-1.0, min(1.0, prev_val))

                change = curr_val - prev_val
                abs_change = abs(change)

                if abs_change >= self.change_threshold:
                    direction = "converging" if abs(curr_val) > abs(prev_val) else "diverging"
                    severity = "high" if abs_change >= self.change_threshold * 2 else "medium"

                    sec_a = get_sector(si)
                    sec_b = get_sector(sj)

                    if abs(curr_val) >= self.high_threshold and sec_a and sec_b and not are_related_sectors(sec_a, sec_b):
                        desc = (
                            f"{si}({sec_a}) and {sj}({sec_b}) developed "
                            f"high unexpected correlation: {prev_val:.2f} -> {curr_val:.2f}"
                        )
                        alerts.append(InstabilityAlert(
                            symbol_a=si, symbol_b=sj,
                            sector_a=sec_a, sector_b=sec_b,
                            corr_change=round(change, 4),
                            prev_corr=round(prev_val, 4),
                            curr_corr=round(curr_val, 4),
                            direction=direction, severity="high",
                            description=desc,
                        ))
                    else:
                        desc = (
                            f"Correlation between {si} and {sj} changed "
                            f"by {abs_change:.2f}: {prev_val:.2f} -> {curr_val:.2f}"
                        )
                        alerts.append(InstabilityAlert(
                            symbol_a=si, symbol_b=sj,
                            sector_a=sec_a, sector_b=sec_b,
                            corr_change=round(change, 4),
                            prev_corr=round(prev_val, 4),
                            curr_corr=round(curr_val, 4),
                            direction=direction, severity=severity,
                            description=desc,
                        ))

        regime = self._classify_regime(df, full_corr)
        avg_now = float(np.mean([
            full_corr.iloc[i, j] for i in range(n) for j in range(i + 1, n)
            if not (np.isnan(full_corr.iloc[i, j]) or np.isinf(full_corr.iloc[i, j]))
        ])) if n >= 2 else 0.0

        avg_before = float(np.mean([
            first_half.iloc[i, j] for i in range(n) for j in range(i + 1, n)
            if not (np.isnan(first_half.iloc[i, j]) or np.isinf(first_half.iloc[i, j]))
        ])) if half >= 10 and n >= 2 else avg_now

        transitions = self._detect_regime_transitions(df)

        return InstabilityReport(
            alerts=sorted(alerts, key=lambda a: abs(a.corr_change), reverse=True),
            correlation_regime=regime,
            avg_correlation_now=round(avg_now, 4),
            avg_correlation_before=round(avg_before, 4),
            avg_correlation_change=round(avg_now - avg_before, 4),
            regime_transitions=transitions,
        )

    def _from_rolling(self, rolling_result, holdings) -> InstabilityReport:
        if not rolling_result.windows or len(rolling_result.windows) < self.lookback_windows:
            return self._empty_report()

        alerts = []
        windows = rolling_result.windows
        current = windows[-1]
        previous = windows[-min(self.lookback_windows + 1, len(windows))]

        change = current.avg_correlation - previous.avg_correlation
        abs_change = abs(change)

        if abs_change >= self.change_threshold:
            alerts.append(InstabilityAlert(
                symbol_a="PORTFOLIO", symbol_b="PORTFOLIO",
                sector_a=None, sector_b=None,
                corr_change=round(change, 4),
                prev_corr=previous.avg_correlation,
                curr_corr=current.avg_correlation,
                direction="converging" if current.avg_correlation > previous.avg_correlation else "diverging",
                severity="high" if abs_change >= self.change_threshold * 2 else "medium",
                description=f"Portfolio avg correlation shifted {change:+.4f} over {self.lookback_windows} windows",
            ))

        regime = "stable"
        if abs_change > self.regime_transition_sensitivity * 2:
            regime = "shifting"
        elif abs_change > self.regime_transition_sensitivity:
            regime = "transitioning"

        return InstabilityReport(
            alerts=alerts,
            correlation_regime=regime,
            avg_correlation_now=current.avg_correlation,
            avg_correlation_before=previous.avg_correlation,
            avg_correlation_change=round(change, 4),
            regime_transitions=[],
        )

    def _classify_regime(self, df: pd.DataFrame, corr_matrix: pd.DataFrame) -> str:
        n = len(corr_matrix.columns)
        if n < 2:
            return "stable"

        values = []
        for i in range(n):
            for j in range(i + 1, n):
                val = corr_matrix.iloc[i, j]
                if not (np.isnan(val) or np.isinf(val)):
                    values.append(abs(val))

        if not values:
            return "stable"

        avg_corr = float(np.mean(values))
        std_corr = float(np.std(values))

        if std_corr > 0.3:
            return "fragmented"
        if avg_corr > 0.7:
            return "highly_correlated"
        if avg_corr < 0.3:
            return "low_correlation"
        return "stable"

    def _detect_regime_transitions(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        if len(df) < 40:
            return []

        transitions = []
        chunk_size = len(df) // 4
        prev_regime = None

        for k in range(4):
            start = k * chunk_size
            end = (k + 1) * chunk_size if k < 3 else len(df)
            chunk = df.iloc[start:end]
            if len(chunk) < 10:
                continue
            corr = chunk.corr()
            regime = self._classify_regime(chunk, corr)

            if prev_regime is not None and regime != prev_regime:
                transitions.append({
                    "from_regime": prev_regime,
                    "to_regime": regime,
                    "period": f"Q{k+1}",
                    "date_range": f"{chunk.index[0]} to {chunk.index[-1]}",
                })
            prev_regime = regime

        return transitions

    def _empty_report(self) -> InstabilityReport:
        return InstabilityReport(
            alerts=[], correlation_regime="stable",
            avg_correlation_now=0.0, avg_correlation_before=0.0,
            avg_correlation_change=0.0, regime_transitions=[],
        )
