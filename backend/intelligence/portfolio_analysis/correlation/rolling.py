from __future__ import annotations
from typing import Any
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from core.logging import logger
from intelligence.portfolio_analysis.correlation.models import (
    RollingCorrelationResult,
    RollingWindowSnapshot,
)


class RollingCorrelationAnalyzer:
    def __init__(self, window_size_days: int = 60, step_days: int = 10,
                 high_threshold: float = 0.80):
        self.window_size_days = window_size_days
        self.step_days = step_days
        self.high_threshold = high_threshold

    def analyze(self, price_data: pd.DataFrame | None = None,
                returns_data: pd.DataFrame | None = None) -> RollingCorrelationResult:
        if returns_data is not None and not returns_data.empty:
            df = returns_data
        elif price_data is not None and not price_data.empty:
            df = price_data.pct_change().dropna()
        else:
            return self._empty_result()

        if df.empty or df.shape[1] < 2:
            return self._empty_result()

        windows = self._compute_rolling_windows(df)
        if not windows:
            return self._empty_result()

        trend = self._detect_trend(windows)
        stability = self._compute_stability(windows)

        timeseries = [
            {
                "date": w.end_date,
                "avg_correlation": w.avg_correlation,
                "min_correlation": w.min_correlation,
                "max_correlation": w.max_correlation,
                "high_corr_count": w.high_corr_count,
                "pair_count": w.pair_count,
            }
            for w in windows
        ]

        return RollingCorrelationResult(
            windows=windows,
            correlation_timeseries=timeseries,
            current_avg_correlation=windows[-1].avg_correlation if windows else 0.0,
            trend=trend,
            stability_score=round(stability, 4),
            window_size_days=self.window_size_days,
            step_days=self.step_days,
        )

    def _compute_rolling_windows(self, df: pd.DataFrame) -> list[RollingWindowSnapshot]:
        dates = df.index
        if isinstance(dates, pd.DatetimeIndex):
            date_min = dates.min()
            date_max = dates.max()
        else:
            date_min = pd.Timestamp(dates[0])
            date_max = pd.Timestamp(dates[-1])

        windows = []
        current_start = date_min

        while current_start + timedelta(days=self.window_size_days) <= date_max:
            window_end = current_start + timedelta(days=self.window_size_days)
            window_data = df.loc[current_start:window_end]

            if len(window_data) >= max(5, int(self.window_size_days * 0.3)):
                corr = window_data.corr()
                n = len(corr.columns)
                if n < 2:
                    current_start += timedelta(days=self.step_days)
                    continue

                pairs = []
                for i in range(n):
                    for j in range(i + 1, n):
                        val = corr.iloc[i, j]
                        if not (np.isnan(val) or np.isinf(val)):
                            pairs.append(val)

                if pairs:
                    avg_c = float(np.mean(pairs))
                    min_c = float(np.min(pairs))
                    max_c = float(np.max(pairs))
                    high_count = sum(1 for p in pairs if abs(p) >= self.high_threshold)
                    windows.append(RollingWindowSnapshot(
                        end_date=window_end.isoformat() if hasattr(window_end, 'isoformat') else str(window_end),
                        window_start=str(current_start.date() if hasattr(current_start, 'date') else current_start),
                        window_end=str(window_end.date() if hasattr(window_end, 'date') else window_end),
                        avg_correlation=round(avg_c, 4),
                        min_correlation=round(min_c, 4),
                        max_correlation=round(max_c, 4),
                        pair_count=len(pairs),
                        high_corr_count=high_count,
                    ))

            current_start += timedelta(days=self.step_days)

        return windows

    def _detect_trend(self, windows: list[RollingWindowSnapshot]) -> str:
        if len(windows) < 3:
            return "stable"

        recent = [w.avg_correlation for w in windows[-min(5, len(windows)):]]
        if len(recent) < 2:
            return "stable"

        slope = np.polyfit(range(len(recent)), recent, 1)[0]
        avg_val = np.mean(recent) if recent else 0

        if avg_val != 0 and abs(slope / avg_val) > 0.05:
            if slope > 0:
                return "rising"
            return "falling"
        return "stable"

    def _compute_stability(self, windows: list[RollingWindowSnapshot]) -> float:
        if len(windows) < 3:
            return 1.0

        values = [w.avg_correlation for w in windows]
        std = float(np.std(values))
        return max(0.0, min(1.0, 1.0 - std))

    def _empty_result(self) -> RollingCorrelationResult:
        return RollingCorrelationResult(
            windows=[], correlation_timeseries=[],
            current_avg_correlation=0.0, trend="stable",
            stability_score=1.0,
            window_size_days=self.window_size_days,
            step_days=self.step_days,
        )
