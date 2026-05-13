from __future__ import annotations

import statistics
from typing import Any, Optional

from core.evaluation.base import MetricType
from core.evaluation.metrics_store import EvalMetricsStore


class RegressionDetector:
    def __init__(self, store: Optional[EvalMetricsStore] = None):
        self._store = store or EvalMetricsStore()

    def check_regression(
        self,
        metric_name: str,
        zscore_threshold: float = 2.0,
        min_samples: int = 5,
    ) -> dict[str, Any]:
        history = self._store.get_metric_history(metric_name, limit=100)
        if len(history) < min_samples:
            return {
                "metric": metric_name,
                "regression_detected": False,
                "reason": f"Need at least {min_samples} samples, got {len(history)}",
                "current_value": history[0]["value"] if history else None,
                "historical_avg": None,
                "historical_std": None,
                "zscore": None,
            }

        values = [h["value"] for h in history]
        current = values[0]
        historical = values[1:]

        avg = statistics.mean(historical)
        stdev = statistics.stdev(historical) if len(historical) > 1 else 0.0

        if stdev < 1e-9:
            is_regression = abs(current - avg) > 1e-6
        else:
            zscore = (current - avg) / stdev
            is_regression = abs(zscore) > zscore_threshold

        return {
            "metric": metric_name,
            "regression_detected": is_regression,
            "current_value": current,
            "historical_avg": round(avg, 4),
            "historical_std": round(stdev, 4),
            "zscore": round(zscore, 4) if stdev >= 1e-9 else None,
            "samples_analyzed": len(history),
            "threshold": zscore_threshold,
        }

    def check_all_regressions(
        self,
        metric_types: Optional[list[MetricType]] = None,
        zscore_threshold: float = 2.0,
    ) -> list[dict[str, Any]]:
        results = []
        all_types = metric_types or list(MetricType)
        seen = set()
        for mt in all_types:
            history = self._store.get_metric_history(mt.value, limit=1)
            if history:
                check = self.check_regression(mt.value, zscore_threshold)
                results.append(check)
                seen.add(mt.value)
        return results

    def get_health_score(self) -> dict[str, Any]:
        regressions = self.check_all_regressions()
        total = len(regressions)
        regression_count = sum(1 for r in regressions if r["regression_detected"])
        healthy_count = total - regression_count
        score = healthy_count / total if total > 0 else 1.0
        return {
            "health_score": round(score, 4),
            "total_metrics": total,
            "healthy_metrics": healthy_count,
            "regression_count": regression_count,
            "regressions": [r for r in regressions if r["regression_detected"]],
        }
