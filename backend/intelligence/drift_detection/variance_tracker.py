from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field


class FeatureVarianceSnapshot(BaseModel):
    feature_name: str
    group_name: str
    current_variance: float = 0.0
    baseline_variance: float = 0.0
    variance_change_pct: float = 0.0
    z_score: float = 0.0
    status: str = "NORMAL"
    is_anomaly: bool = False
    window_size: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class VarianceReport(BaseModel):
    snapshots: list[FeatureVarianceSnapshot] = Field(default_factory=list)
    total_features: int = 0
    anomalous_features: int = 0
    warning_features: int = 0
    normal_features: int = 0
    most_volatile_feature: Optional[str] = None
    max_variance_change: float = 0.0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class VarianceTracker:
    def __init__(self, window_size: int = 20, z_score_threshold: float = 2.0, variance_change_threshold: float = 50.0):
        self._window_size = window_size
        self._z_score_threshold = z_score_threshold
        self._variance_change_threshold = variance_change_threshold
        self._history: dict[str, deque] = {}
        self._baselines: dict[str, dict[str, float]] = {}

    def configure(self, window_size: Optional[int] = None, z_score_threshold: Optional[float] = None, variance_change_threshold: Optional[float] = None):
        if window_size is not None:
            self._window_size = window_size
        if z_score_threshold is not None:
            self._z_score_threshold = z_score_threshold
        if variance_change_threshold is not None:
            self._variance_change_threshold = variance_change_threshold

    def set_baseline_variance(self, feature_name: str, variance: float, mean: float = 0.0, group_name: str = "general"):
        key = f"{group_name}__{feature_name}"
        self._baselines[key] = {"variance": variance, "mean": mean}

    def get_baseline_variance(self, feature_name: str, group_name: str = "general") -> Optional[float]:
        key = f"{group_name}__{feature_name}"
        entry = self._baselines.get(key)
        return entry["variance"] if entry else None

    def record_value(self, feature_name: str, value: float, group_name: str = "general"):
        key = f"{group_name}__{feature_name}"
        if key not in self._history:
            self._history[key] = deque(maxlen=self._window_size * 2)
        self._history[key].append(value)

    def record_batch(self, features: dict[str, float], group_name: str = "general"):
        for fname, value in features.items():
            self.record_value(fname, value, group_name)

    def analyze_variance(
        self,
        feature_name: str,
        current_values: Optional[np.ndarray] = None,
        group_name: str = "general",
    ) -> Optional[FeatureVarianceSnapshot]:
        key = f"{group_name}__{feature_name}"

        if current_values is not None:
            values = np.asarray(current_values, dtype=np.float64)
        elif key in self._history:
            values = np.array(list(self._history[key]), dtype=np.float64)
        else:
            return None

        values = values[~np.isnan(values)]
        if len(values) < 2:
            return None

        current_var = float(np.var(values))
        current_mean = float(np.mean(values))

        baseline_var = self.get_baseline_variance(feature_name, group_name)
        if baseline_var is not None and baseline_var > 0:
            variance_change = ((current_var - baseline_var) / baseline_var) * 100
            z_score = (current_var - baseline_var) / (baseline_var * 0.5 + 1e-10)
        else:
            variance_change = 0.0
            z_score = 0.0

        if abs(z_score) > self._z_score_threshold or abs(variance_change) > self._variance_change_threshold:
            if abs(z_score) > self._z_score_threshold * 1.5:
                status = "DRIFT"
            else:
                status = "WARNING"
            is_anomaly = True
        else:
            status = "NORMAL"
            is_anomaly = False

        return FeatureVarianceSnapshot(
            feature_name=feature_name,
            group_name=group_name,
            current_variance=round(current_var, 6),
            baseline_variance=round(baseline_var or 0.0, 6),
            variance_change_pct=round(variance_change, 2),
            z_score=round(z_score, 4),
            status=status,
            is_anomaly=is_anomaly,
            window_size=self._window_size,
        )

    def analyze_all(
        self,
        feature_values: Optional[dict[str, np.ndarray]] = None,
        group_name: str = "general",
    ) -> VarianceReport:
        snapshots: list[FeatureVarianceSnapshot] = []
        if feature_values:
            for fname, values in feature_values.items():
                snap = self.analyze_variance(fname, current_values=values, group_name=group_name)
                if snap is not None:
                    snapshots.append(snap)
        else:
            seen = set()
            for key in list(self._history.keys()):
                g, fname = key.split("__", 1)
                if g == group_name and fname not in seen:
                    snap = self.analyze_variance(fname, group_name=group_name)
                    if snap is not None:
                        snapshots.append(snap)
                    seen.add(fname)

        if not snapshots:
            return VarianceReport(summary="No variance data available")

        anomalous = [s for s in snapshots if s.is_anomaly]
        warning = [s for s in snapshots if s.status == "WARNING"]
        normal = [s for s in snapshots if s.status == "NORMAL"]

        sorted_by_change = sorted(snapshots, key=lambda s: abs(s.variance_change_pct), reverse=True)
        most_volatile = sorted_by_change[0].feature_name if sorted_by_change else None
        max_change = abs(sorted_by_change[0].variance_change_pct) if sorted_by_change else 0.0

        summary_parts = []
        if anomalous:
            summary_parts.append(f"{len(anomalous)} features with anomalous variance")
        if warning:
            summary_parts.append(f"{len(warning)} in warning zone")
        summary_parts.append(f"{len(snapshots)} features tracked")
        if most_volatile:
            summary_parts.append(f"most volatile: {most_volatile} ({max_change:.1f}% change)")

        return VarianceReport(
            snapshots=snapshots,
            total_features=len(snapshots),
            anomalous_features=len(anomalous),
            warning_features=len(warning),
            normal_features=len(normal),
            most_volatile_feature=most_volatile,
            max_variance_change=round(max_change, 2),
            summary=" | ".join(summary_parts),
        )

    def get_variance_history(self, feature_name: str, group_name: str = "general") -> list[float]:
        key = f"{group_name}__{feature_name}"
        if key in self._history:
            return list(self._history[key])
        return []

    @property
    def tracked_features(self) -> list[str]:
        return list(self._history.keys())
