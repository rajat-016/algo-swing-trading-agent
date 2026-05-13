from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    feature_name: str
    baseline_importance: float = 0.0
    current_importance: float = 0.0
    importance_change: float = 0.0
    importance_change_pct: float = 0.0
    rank_baseline: int = 0
    rank_current: int = 0
    rank_shift: int = 0
    status: str = "NORMAL"


class ContributionDriftReport(BaseModel):
    feature_contributions: list[FeatureContribution] = Field(default_factory=list)
    total_features: int = 0
    drifted_features: int = 0
    top_features_changed: bool = False
    feature_rank_stability: float = 0.0
    prediction_confidence_trend: str = "unknown"
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class PredictionContributionAnalyzer:
    def __init__(self, analytics_db=None, prediction_monitor=None):
        self._analytics_db = analytics_db
        self._prediction_monitor = prediction_monitor
        self._baseline_importance: dict[str, float] = {}

    def set_baseline_importance(self, importance_map: dict[str, float]):
        self._baseline_importance = dict(importance_map)

    def get_baseline_importance(self, feature_name: str) -> Optional[float]:
        return self._baseline_importance.get(feature_name)

    def analyze_contribution_drift(
        self,
        current_importance: dict[str, float],
        prediction_logs: Optional[list[dict]] = None,
        contribution_change_threshold: float = 20.0,
    ) -> ContributionDriftReport:
        if not self._baseline_importance:
            self.set_baseline_importance(current_importance)
            return ContributionDriftReport(summary="Baseline established from current data")

        all_features = set(list(self._baseline_importance.keys()) + list(current_importance.keys()))
        contributions: list[FeatureContribution] = []
        baseline_sorted = sorted(self._baseline_importance.items(), key=lambda x: x[1], reverse=True)
        current_sorted = sorted(current_importance.items(), key=lambda x: x[1], reverse=True)
        baseline_rank_map = {name: i for i, (name, _) in enumerate(baseline_sorted)}
        current_rank_map = {name: i for i, (name, _) in enumerate(current_sorted)}

        for fname in all_features:
            base_val = self._baseline_importance.get(fname, 0.0)
            curr_val = current_importance.get(fname, 0.0)
            importance_change = curr_val - base_val
            importance_change_pct = (importance_change / abs(base_val)) * 100 if base_val != 0 else 0.0
            rank_baseline = baseline_rank_map.get(fname, len(baseline_sorted))
            rank_current = current_rank_map.get(fname, len(current_sorted))
            rank_shift = rank_current - rank_baseline

            if abs(importance_change_pct) > contribution_change_threshold:
                status = "DRIFT"
            elif abs(importance_change_pct) > contribution_change_threshold * 0.5:
                status = "WARNING"
            else:
                status = "NORMAL"

            contributions.append(FeatureContribution(
                feature_name=fname,
                baseline_importance=round(base_val, 6),
                current_importance=round(curr_val, 6),
                importance_change=round(importance_change, 6),
                importance_change_pct=round(importance_change_pct, 2),
                rank_baseline=rank_baseline + 1,
                rank_current=rank_current + 1,
                rank_shift=rank_shift,
                status=status,
            ))

        drifted = [c for c in contributions if c.status == "DRIFT"]

        baseline_top5 = set(name for name, _ in baseline_sorted[:5])
        current_top5 = set(name for name, _ in current_sorted[:5])
        top_features_changed = baseline_top5 != current_top5

        rank_changes = [abs(c.rank_shift) for c in contributions if c.rank_shift != 0]
        rank_stability = 1.0 - (sum(rank_changes) / (len(rank_changes) * max(max(rank_changes), 1))) if rank_changes else 1.0

        confidence_trend = self._compute_confidence_trend(prediction_logs)

        summary_parts = []
        if drifted:
            summary_parts.append(f"{len(drifted)} features with importance drift")
        if top_features_changed:
            summary_parts.append("top features changed")
        summary_parts.append(f"rank stability: {rank_stability:.0%}")

        return ContributionDriftReport(
            feature_contributions=contributions,
            total_features=len(contributions),
            drifted_features=len(drifted),
            top_features_changed=top_features_changed,
            feature_rank_stability=round(rank_stability, 4),
            prediction_confidence_trend=confidence_trend,
            summary=" | ".join(summary_parts),
        )

    def _compute_confidence_trend(self, logs: Optional[list[dict]]) -> str:
        if logs is None:
            if self._prediction_monitor is not None:
                try:
                    logs = self._prediction_monitor.get_recent_predictions(limit=100)
                except Exception:
                    return "unknown"
            else:
                return "unknown"

        if not logs:
            return "unknown"

        confidences = [float(l.get("confidence", 0)) for l in logs if l.get("confidence") is not None]
        if len(confidences) < 10:
            return "insufficient_data"

        mid = len(confidences) // 2
        first_half = confidences[:mid]
        second_half = confidences[mid:]
        avg_first = float(np.mean(first_half)) if first_half else 0
        avg_second = float(np.mean(second_half)) if second_half else 0

        if avg_first > 0:
            change = ((avg_second - avg_first) / avg_first) * 100
            if change > 5:
                return "improving"
            elif change < -5:
                return "degrading"
        return "stable"
