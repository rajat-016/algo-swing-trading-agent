from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field


SHIFT_METHOD_PSI = "psi"
SHIFT_METHOD_KL = "kl_divergence"
SHIFT_METHOD_JSD = "js_divergence"


class ShiftResult(BaseModel):
    feature_name: str
    group_name: str = "general"
    psi: float = 0.0
    kl_divergence: float = 0.0
    js_divergence: float = 0.0
    shift_score: float = 0.0
    status: str = "NORMAL"
    window_label: str = ""
    sample_sizes: dict[str, int] = Field(default_factory=lambda: {"baseline": 0, "current": 0})
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DistributionShiftAnalyzer:
    def __init__(self):
        self._baselines: dict[str, dict[str, np.ndarray]] = {}

    def set_baseline(self, group_name: str, feature_name: str, values: np.ndarray):
        key = f"{group_name}__{feature_name}"
        self._baselines[key] = np.asarray(values, dtype=np.float64)

    def get_baseline(self, group_name: str, feature_name: str) -> Optional[np.ndarray]:
        key = f"{group_name}__{feature_name}"
        arr = self._baselines.get(key)
        return arr.copy() if arr is not None else None

    def compute_psi(self, expected: np.ndarray, actual: np.ndarray, buckets: int = 10) -> float:
        expected = np.asarray(expected, dtype=np.float64)
        actual = np.asarray(actual, dtype=np.float64)
        expected = expected[~np.isnan(expected)]
        actual = actual[~np.isnan(actual)]
        if len(expected) < 2 or len(actual) == 0:
            return 0.0
        if len(actual) == 1:
            actual = np.repeat(actual, min(10, len(expected)))
        combined = np.concatenate([expected, actual])
        if np.std(combined) == 0:
            return 0.0
        percentiles = np.linspace(0, 100, buckets + 1)[1:-1]
        edges = np.percentile(expected, percentiles)
        edges = np.clip(edges, np.min(combined), np.max(combined))
        if len(np.unique(edges)) < 2:
            return 0.0
        bin_edges = np.concatenate([[-np.inf], edges, [np.inf]])
        expected_counts, _ = np.histogram(expected, bins=bin_edges)
        actual_counts, _ = np.histogram(actual, bins=bin_edges)
        expected_pct = expected_counts / len(expected)
        actual_pct = actual_counts / len(actual)
        psi = 0.0
        for e, a in zip(expected_pct, actual_pct):
            if e == 0:
                e = 0.0001
            if a == 0:
                a = 0.0001
            psi += (a - e) * np.log(a / e)
        return round(float(psi), 6)

    def compute_kl_divergence(self, p: np.ndarray, q: np.ndarray, buckets: int = 10) -> float:
        p = np.asarray(p, dtype=np.float64)
        q = np.asarray(q, dtype=np.float64)
        p = p[~np.isnan(p)]
        q = q[~np.isnan(q)]
        if len(p) < 2 or len(q) < 2:
            return 0.0
        combined = np.concatenate([p, q])
        if np.std(combined) == 0:
            return 0.0
        edges = np.percentile(combined, np.linspace(0, 100, buckets + 1)[1:-1])
        bin_edges = np.concatenate([[-np.inf], edges, [np.inf]])
        p_counts, _ = np.histogram(p, bins=bin_edges)
        q_counts, _ = np.histogram(q, bins=bin_edges)
        p_pct = p_counts / len(p)
        q_pct = q_counts / len(q)
        p_pct = np.clip(p_pct, 0.0001, None)
        q_pct = np.clip(q_pct, 0.0001, None)
        kl = float(np.sum(p_pct * np.log(p_pct / q_pct)))
        return round(kl, 6)

    def compute_js_divergence(self, p: np.ndarray, q: np.ndarray, buckets: int = 10) -> float:
        p = np.asarray(p, dtype=np.float64)
        q = np.asarray(q, dtype=np.float64)
        p = p[~np.isnan(p)]
        q = q[~np.isnan(q)]
        if len(p) < 2 or len(q) < 2:
            return 0.0
        m = 0.5 * (self._to_distribution(p, buckets) + self._to_distribution(q, buckets))
        p_dist = self._to_distribution(p, buckets)
        q_dist = self._to_distribution(q, buckets)
        p_dist = np.clip(p_dist, 0.0001, None)
        q_dist = np.clip(q_dist, 0.0001, None)
        m = np.clip(m, 0.0001, None)
        js = 0.5 * float(np.sum(p_dist * np.log(p_dist / m)) + np.sum(q_dist * np.log(q_dist / m)))
        return round(js, 6)

    def _to_distribution(self, data: np.ndarray, buckets: int = 10) -> np.ndarray:
        if np.std(data) == 0:
            return np.ones(buckets) / buckets
        edges = np.percentile(data, np.linspace(0, 100, buckets + 1)[1:-1])
        bin_edges = np.concatenate([[-np.inf], edges, [np.inf]])
        counts, _ = np.histogram(data, bins=bin_edges)
        return counts / len(data)

    def analyze_shift(
        self,
        feature_name: str,
        baseline_values: np.ndarray,
        current_values: np.ndarray,
        group_name: str = "general",
        window_label: str = "",
        psi_threshold: float = 0.1,
        kl_threshold: float = 0.1,
        jsd_threshold: float = 0.05,
    ) -> ShiftResult:
        psi = self.compute_psi(baseline_values, current_values)
        kl = self.compute_kl_divergence(baseline_values, current_values)
        jsd = self.compute_js_divergence(baseline_values, current_values)

        shift_score = max(psi / 0.25, kl / 0.2, jsd / 0.1) if any([psi > 0, kl > 0, jsd > 0]) else 0.0
        shift_score = min(shift_score, 1.0)

        if psi >= 0.25:
            status = "DRIFT"
        elif psi >= psi_threshold:
            status = "WARNING"
        elif jsd >= jsd_threshold:
            status = "WARNING"
        else:
            status = "NORMAL"

        return ShiftResult(
            feature_name=feature_name,
            group_name=group_name,
            psi=psi,
            kl_divergence=kl,
            js_divergence=jsd,
            shift_score=round(shift_score, 4),
            status=status,
            window_label=window_label,
            sample_sizes={"baseline": len(baseline_values), "current": len(current_values)},
        )

    def analyze_sliding_window(
        self,
        feature_name: str,
        baseline_values: np.ndarray,
        all_values: np.ndarray,
        window_size: int = 20,
        step: int = 10,
        group_name: str = "general",
        psi_threshold: float = 0.1,
    ) -> list[ShiftResult]:
        results: list[ShiftResult] = []
        if len(all_values) < window_size:
            return results

        for start in range(0, len(all_values) - window_size + 1, step):
            window_data = all_values[start : start + window_size]
            window_label = f"window_{start}_{start + window_size}"
            result = self.analyze_shift(
                feature_name=feature_name,
                baseline_values=baseline_values,
                current_values=window_data,
                group_name=group_name,
                window_label=window_label,
                psi_threshold=psi_threshold,
            )
            results.append(result)

        return results

    def summarize_shift_trend(self, results: list[ShiftResult]) -> dict[str, Any]:
        if not results:
            return {"status": "NO_DATA", "trend": "unknown", "avg_psi": 0.0, "max_psi": 0.0}

        sorted_results = sorted(results, key=lambda r: r.window_label)
        drifts = [r for r in sorted_results if r.status == "DRIFT"]
        warnings = [r for r in sorted_results if r.status == "WARNING"]

        if len(sorted_results) >= 2:
            first_psi = sorted_results[0].psi
            last_psi = sorted_results[-1].psi
            if first_psi > 0:
                change_pct = ((last_psi - first_psi) / first_psi) * 100
                trend = "increasing" if change_pct > 20 else ("decreasing" if change_pct < -20 else "stable")
            else:
                trend = "stable"
        else:
            trend = "stable"

        return {
            "total_windows": len(sorted_results),
            "drift_windows": len(drifts),
            "warning_windows": len(warnings),
            "avg_psi": round(float(np.mean([r.psi for r in sorted_results])), 6),
            "max_psi": round(float(np.max([r.psi for r in sorted_results])), 6),
            "trend": trend,
            "status": "DRIFT" if len(drifts) > len(sorted_results) / 2 else ("WARNING" if warnings else "NORMAL"),
        }
