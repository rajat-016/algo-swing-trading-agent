from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
from loguru import logger

from intelligence.drift_detection.distribution_shift import DistributionShiftAnalyzer, ShiftResult
from intelligence.drift_detection.variance_tracker import VarianceTracker, VarianceReport
from intelligence.drift_detection.prediction_contribution import (
    ContributionDriftReport,
    PredictionContributionAnalyzer,
)
from intelligence.drift_detection.alerting import (
    AlertRule,
    DriftAlert,
    DriftAlertManager,
    DriftSeverity,
    DriftType,
)
from intelligence.drift_detection.baseline_manager import BaselineManager


class DriftDetectionService:
    def __init__(self, analytics_db=None, prediction_monitor=None):
        self._db = analytics_db
        self._shift_analyzer = DistributionShiftAnalyzer()
        self._variance_tracker = VarianceTracker()
        self._contribution_analyzer = PredictionContributionAnalyzer(
            analytics_db=analytics_db,
            prediction_monitor=prediction_monitor,
        )
        self._alert_manager = DriftAlertManager()
        self._baseline_manager = BaselineManager(analytics_db=analytics_db)
        self._setup_default_rules()
        self._prediction_monitor = prediction_monitor

    def _setup_default_rules(self):
        self._alert_manager.add_rule(AlertRule(
            rule_id="psi_drift_warning",
            name="PSI Drift Warning",
            drift_type=DriftType.DISTRIBUTION_SHIFT,
            severity=DriftSeverity.WARNING,
            metric="psi",
            operator=">=",
            threshold=0.1,
            cooldown_minutes=30,
            description="Triggers when PSI >= 0.1 (warning threshold)",
        ))
        self._alert_manager.add_rule(AlertRule(
            rule_id="psi_drift_critical",
            name="PSI Drift Critical",
            drift_type=DriftType.DISTRIBUTION_SHIFT,
            severity=DriftSeverity.CRITICAL,
            metric="psi",
            operator=">=",
            threshold=0.25,
            cooldown_minutes=60,
            description="Triggers when PSI >= 0.25 (drift threshold)",
        ))
        self._alert_manager.add_rule(AlertRule(
            rule_id="variance_anomaly",
            name="Variance Anomaly",
            drift_type=DriftType.VARIANCE_ANOMALY,
            severity=DriftSeverity.WARNING,
            metric="variance_change_pct",
            operator=">=",
            threshold=50.0,
            cooldown_minutes=30,
            description="Triggers when variance change exceeds 50%",
        ))
        self._alert_manager.add_rule(AlertRule(
            rule_id="contribution_drift",
            name="Feature Contribution Drift",
            drift_type=DriftType.CONTRIBUTION_DRIFT,
            severity=DriftSeverity.WARNING,
            metric="importance_change_pct",
            operator=">=",
            threshold=20.0,
            cooldown_minutes=60,
            description="Triggers when feature importance changes by 20%+",
        ))

    @property
    def shift_analyzer(self) -> DistributionShiftAnalyzer:
        return self._shift_analyzer

    @property
    def variance_tracker(self) -> VarianceTracker:
        return self._variance_tracker

    @property
    def contribution_analyzer(self) -> PredictionContributionAnalyzer:
        return self._contribution_analyzer

    @property
    def alert_manager(self) -> DriftAlertManager:
        return self._alert_manager

    @property
    def baseline_manager(self) -> BaselineManager:
        return self._baseline_manager

    def initialize_baselines(self, baseline_data: dict[str, list[float]], group_name: str = "general"):
        for feature_name, values in baseline_data.items():
            values_arr = np.asarray(values, dtype=np.float64)
            self._shift_analyzer.set_baseline(group_name, feature_name, values_arr)
            self._variance_tracker.set_baseline_variance(feature_name, float(np.var(values_arr)), float(np.mean(values_arr)), group_name)
            self._baseline_manager.store_baseline(feature_name, group_name, values)
        logger.info(f"Initialized baselines for {len(baseline_data)} features in group '{group_name}'")

    def analyze_feature_shift(
        self,
        feature_name: str,
        baseline_values: np.ndarray,
        current_values: np.ndarray,
        group_name: str = "general",
    ) -> ShiftResult:
        result = self._shift_analyzer.analyze_shift(
            feature_name=feature_name,
            baseline_values=baseline_values,
            current_values=current_values,
            group_name=group_name,
        )
        self._alert_manager.evaluate_psi(feature_name, result.psi, group_name)
        return result

    def analyze_batch_shift(
        self,
        feature_data: dict[str, dict[str, np.ndarray]],
        group_name: str = "general",
    ) -> list[ShiftResult]:
        results: list[ShiftResult] = []
        for feature_name, data in feature_data.items():
            baseline = data.get("baseline")
            current = data.get("current")
            if baseline is not None and current is not None:
                result = self.analyze_feature_shift(feature_name, baseline, current, group_name)
                results.append(result)
        return results

    def track_feature_variance(
        self,
        feature_name: str,
        current_values: Optional[np.ndarray] = None,
        group_name: str = "general",
    ):
        snapshot = self._variance_tracker.analyze_variance(feature_name, current_values, group_name)
        if snapshot is not None:
            self._alert_manager.evaluate_variance(
                feature_name, snapshot.z_score, snapshot.variance_change_pct, group_name,
            )
        return snapshot

    def track_batch_variance(
        self,
        feature_values: dict[str, np.ndarray],
        group_name: str = "general",
    ) -> VarianceReport:
        report = self._variance_tracker.analyze_all(feature_values, group_name)
        for snap in report.snapshots:
            if snap.is_anomaly:
                self._alert_manager.evaluate_variance(
                    snap.feature_name, snap.z_score, snap.variance_change_pct, group_name,
                )
        return report

    def analyze_prediction_contribution(
        self,
        current_importance: dict[str, float],
        prediction_logs: Optional[list[dict]] = None,
    ) -> ContributionDriftReport:
        report = self._contribution_analyzer.analyze_contribution_drift(current_importance, prediction_logs)
        for contrib in report.feature_contributions:
            if contrib.status in ("DRIFT", "WARNING"):
                self._alert_manager.evaluate_contribution(
                    contrib.feature_name, contrib.importance_change_pct,
                )
        return report

    def get_service_status(self) -> dict[str, Any]:
        return {
            "baseline_features": len(self._baseline_manager.list_baselines()),
            "tracked_features": len(self._variance_tracker.tracked_features),
            "alert_rules": len(self._alert_manager.get_rules()),
            "unacknowledged_alerts": self._alert_manager.get_unacknowledged_count(),
            "shift_methods": ["psi", "kl_divergence", "js_divergence"],
            "window_size": getattr(self._variance_tracker, "_window_size", 20),
        }

    def run_full_pipeline(
        self,
        feature_data: dict[str, np.ndarray],
        baseline_data: Optional[dict[str, np.ndarray]] = None,
        importance_data: Optional[dict[str, float]] = None,
        group_name: str = "general",
    ) -> dict[str, Any]:
        results: dict[str, Any] = {
            "timestamps": {"started_at": datetime.now(timezone.utc).isoformat()},
            "shift_results": [],
            "variance_report": None,
            "contribution_report": None,
            "alerts": [],
        }

        for feature_name, current_values in feature_data.items():
            if baseline_data and feature_name in baseline_data:
                shift_result = self.analyze_feature_shift(
                    feature_name, baseline_data[feature_name], current_values, group_name,
                )
                results["shift_results"].append(shift_result.model_dump())

        var_report = self.track_batch_variance(feature_data, group_name)
        results["variance_report"] = var_report.model_dump()

        if importance_data is not None:
            contrib_report = self.analyze_prediction_contribution(importance_data)
            results["contribution_report"] = contrib_report.model_dump()

        results["alerts"] = [
            a.model_dump() for a in self._alert_manager.get_alerts(limit=20, unacknowledged_only=True)
        ]
        results["timestamps"]["completed_at"] = datetime.now(timezone.utc).isoformat()
        return results
