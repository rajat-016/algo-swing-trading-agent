import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

import numpy as np
import pytest

from intelligence.drift_detection.distribution_shift import DistributionShiftAnalyzer, ShiftResult
from intelligence.drift_detection.variance_tracker import VarianceTracker, VarianceReport
from intelligence.drift_detection.prediction_contribution import (
    PredictionContributionAnalyzer,
    ContributionDriftReport,
    FeatureContribution,
)
from intelligence.drift_detection.alerting import (
    DriftAlertManager,
    DriftAlert,
    AlertRule,
    DriftSeverity,
    DriftType,
)
from intelligence.drift_detection.baseline_manager import BaselineManager
from intelligence.drift_detection.service import DriftDetectionService


def _make_baseline_importance():
    return {"ma_20": 0.35, "rsi": 0.25, "volume": 0.20, "volatility": 0.15, "trend": 0.05}


class TestDistributionShiftAnalyzer:

    def setup_method(self):
        self.analyzer = DistributionShiftAnalyzer()
        self.baseline = np.array([10.0, 12.0, 11.0, 13.0, 10.5, 11.5, 12.5, 9.5, 11.0, 12.0])
        self.current = np.array([15.0, 16.0, 14.5, 15.5, 16.0, 15.0, 14.0, 15.5, 16.5, 15.0])

    def test_compute_psi_no_shift(self):
        psi = self.analyzer.compute_psi(self.baseline, self.baseline)
        assert psi == 0.0

    def test_compute_psi_with_shift(self):
        psi = self.analyzer.compute_psi(self.baseline, self.current)
        assert psi > 0.0

    def test_compute_psi_empty(self):
        psi = self.analyzer.compute_psi(np.array([]), self.current)
        assert psi == 0.0

    def test_compute_psi_single_value(self):
        psi = self.analyzer.compute_psi(np.array([5.0]), self.current)
        assert psi == 0.0

    def test_compute_kl_divergence(self):
        kl = self.analyzer.compute_kl_divergence(self.baseline, self.current)
        assert kl >= 0.0

    def test_compute_kl_divergence_no_shift(self):
        kl = self.analyzer.compute_kl_divergence(self.baseline, self.baseline)
        assert kl >= 0.0

    def test_compute_js_divergence(self):
        jsd = self.analyzer.compute_js_divergence(self.baseline, self.current)
        assert jsd >= 0.0

    def test_compute_js_divergence_no_shift(self):
        jsd = self.analyzer.compute_js_divergence(self.baseline, self.baseline)
        assert jsd == 0.0

    def test_analyze_shift_normal(self):
        result = self.analyzer.analyze_shift("test_feat", self.baseline, self.baseline)
        assert isinstance(result, ShiftResult)
        assert result.status == "NORMAL"
        assert result.feature_name == "test_feat"
        assert result.shift_score == 0.0

    def test_analyze_shift_drift(self):
        shifted = self.baseline + 5.0
        result = self.analyzer.analyze_shift("test_feat", self.baseline, shifted)
        assert result.status in ("WARNING", "DRIFT")
        assert result.psi > 0.1

    def test_analyze_shift_with_group_and_window(self):
        result = self.analyzer.analyze_shift(
            "feat1", self.baseline, self.current,
            group_name="group_a", window_label="w1",
        )
        assert result.group_name == "group_a"
        assert result.window_label == "w1"
        assert result.sample_sizes["baseline"] == len(self.baseline)

    def test_set_and_get_baseline(self):
        self.analyzer.set_baseline("g1", "f1", self.baseline)
        retrieved = self.analyzer.get_baseline("g1", "f1")
        assert retrieved is not None
        np.testing.assert_array_equal(retrieved, self.baseline)

    def test_get_baseline_nonexistent(self):
        assert self.analyzer.get_baseline("nope", "nope") is None

    def test_sliding_window(self):
        all_vals = np.concatenate([self.baseline, self.current])
        results = self.analyzer.analyze_sliding_window("feat1", self.baseline, all_vals, window_size=5, step=5)
        assert len(results) > 0
        assert all(isinstance(r, ShiftResult) for r in results)

    def test_sliding_window_too_small(self):
        results = self.analyzer.analyze_sliding_window("feat1", self.baseline, np.array([1.0, 2.0]), window_size=5, step=1)
        assert len(results) == 0

    def test_summarize_shift_trend_empty(self):
        summary = self.analyzer.summarize_shift_trend([])
        assert summary["status"] == "NO_DATA"

    def test_summarize_shift_trend_normal(self):
        results = [
            self.analyzer.analyze_shift("f1", self.baseline, self.baseline, window_label="w1"),
            self.analyzer.analyze_shift("f1", self.baseline, self.baseline, window_label="w2"),
        ]
        summary = self.analyzer.summarize_shift_trend(results)
        assert summary["total_windows"] == 2

    def test_to_distribution(self):
        dist = self.analyzer._to_distribution(self.baseline, buckets=5)
        assert abs(dist.sum() - 1.0) < 0.01
        assert len(dist) == 5

    def test_psi_with_identical_single_values(self):
        a = np.array([5.0, 5.0, 5.0])
        b = np.array([5.0, 5.0, 5.0])
        psi = self.analyzer.compute_psi(a, b)
        assert psi == 0.0


class TestVarianceTracker:

    def setup_method(self):
        self.tracker = VarianceTracker(window_size=10, z_score_threshold=2.0, variance_change_threshold=50.0)

    def test_analyze_variance_insufficient_data(self):
        result = self.tracker.analyze_variance("feat1", current_values=np.array([1.0]))
        assert result is None

    def test_analyze_variance_normal(self):
        values = np.random.randn(20) * 0.1 + 10.0
        result = self.tracker.analyze_variance("feat1", current_values=values)
        assert result is not None
        assert isinstance(result.current_variance, float)
        assert result.status in ("NORMAL", "WARNING")

    def test_analyze_variance_with_baseline(self):
        self.tracker.set_baseline_variance("feat1", 0.01, 10.0)
        values = np.random.randn(20) * 0.1 + 10.0
        result = self.tracker.analyze_variance("feat1", current_values=values)
        assert result is not None
        assert result.baseline_variance == 0.01

    def test_variance_anomaly_detected(self):
        stable = np.random.randn(30) * 0.1 + 10.0
        self.tracker.set_baseline_variance("feat1", float(np.var(stable)), float(np.mean(stable)))
        volatile = np.random.randn(30) * 2.0 + 15.0
        result = self.tracker.analyze_variance("feat1", current_values=volatile)
        assert result is not None
        assert result.is_anomaly or abs(result.variance_change_pct) > 10

    def test_record_and_analyze(self):
        self.tracker.set_baseline_variance("feat1", 0.01)
        for i in range(15):
            self.tracker.record_value("feat1", 10.0 + np.random.randn() * 0.1)
        result = self.tracker.analyze_variance("feat1")
        assert result is not None

    def test_record_batch(self):
        self.tracker.set_baseline_variance("f1", 0.01)
        self.tracker.set_baseline_variance("f2", 0.01)
        for i in range(15):
            self.tracker.record_batch({"f1": 10.0, "f2": 20.0})
        report = self.tracker.analyze_all()
        assert report.total_features == 2

    def test_analyze_all_with_values(self):
        report = self.tracker.analyze_all({
            "f1": np.random.randn(20) * 0.1 + 10.0,
            "f2": np.random.randn(20) * 0.2 + 20.0,
        })
        assert isinstance(report, VarianceReport)
        assert report.total_features == 2

    def test_analyze_all_empty(self):
        report = self.tracker.analyze_all({})
        assert report.total_features == 0

    def test_get_variance_history(self):
        for i in range(15):
            self.tracker.record_value("f1", float(i))
        history = self.tracker.get_variance_history("f1")
        assert len(history) == 15

    def test_tracked_features(self):
        self.tracker.record_value("f1", 1.0)
        self.tracker.record_value("f2", 2.0)
        assert len(self.tracker.tracked_features) == 2

    def test_get_baseline_variance_nonexistent(self):
        assert self.tracker.get_baseline_variance("nope") is None

    def test_configure(self):
        self.tracker.configure(window_size=30, z_score_threshold=3.0)
        result = self.tracker.analyze_variance("f1", current_values=np.random.randn(25) * 0.1 + 10.0)
        assert result is not None

    def test_variance_zero_baseline(self):
        self.tracker.set_baseline_variance("feat1", 0.0)
        values = np.random.randn(10) * 0.1 + 10.0
        result = self.tracker.analyze_variance("feat1", current_values=values)
        assert result is not None


class TestPredictionContributionAnalyzer:

    def setup_method(self):
        self.analyzer = PredictionContributionAnalyzer()
        self.baseline_importance = {
            "ma_20": 0.35, "rsi": 0.25, "volume": 0.20, "volatility": 0.15, "trend": 0.05,
        }
        self.analyzer.set_baseline_importance(self.baseline_importance)

    def test_first_call_establishes_baseline(self):
        fresh = PredictionContributionAnalyzer()
        report = fresh.analyze_contribution_drift(self.baseline_importance)
        assert "Baseline established" in report.summary

    def test_no_drift_when_unchanged(self):
        report = self.analyzer.analyze_contribution_drift(self.baseline_importance)
        drifted = [c for c in report.feature_contributions if c.status == "DRIFT"]
        assert len(drifted) == 0

    def test_drift_detected(self):
        shifted = {k: v * 0.5 if k == "ma_20" else v * 1.3 for k, v in self.baseline_importance.items()}
        report = self.analyzer.analyze_contribution_drift(shifted)
        drifted = [c for c in report.feature_contributions if c.status == "DRIFT"]
        assert len(drifted) > 0

    def test_feature_contributions_structure(self):
        report = self.analyzer.analyze_contribution_drift(self.baseline_importance)
        assert report.total_features == len(self.baseline_importance)
        for c in report.feature_contributions:
            assert isinstance(c, FeatureContribution)
            assert c.rank_baseline >= 1
            assert c.rank_current >= 1

    def test_new_feature_appears(self):
        extended = dict(self.baseline_importance)
        extended["new_feat"] = 0.10
        report = self.analyzer.analyze_contribution_drift(extended)
        assert report.total_features == len(extended)
        new_contrib = [c for c in report.feature_contributions if c.feature_name == "new_feat"]
        assert len(new_contrib) == 1

    def test_top_features_changed(self):
        reversed_imp = {k: 1.0 - v for k, v in self.baseline_importance.items()}
        report = self.analyzer.analyze_contribution_drift(reversed_imp)
        rank_shifts = [c.rank_shift for c in report.feature_contributions]
        assert any(abs(s) > 0 for s in rank_shifts), "expected some rank shifts"
        assert report.drifted_features > 0

    def test_compute_confidence_trend_unknown(self):
        trend = self.analyzer._compute_confidence_trend(None)
        assert trend == "unknown"

    def test_compute_confidence_trend_insufficient(self):
        trend = self.analyzer._compute_confidence_trend([{"confidence": 0.9}])
        assert trend == "insufficient_data"

    def test_compute_confidence_trend_improving(self):
        logs = [{"confidence": 0.5 + i * 0.01} for i in range(40)]
        trend = self.analyzer._compute_confidence_trend(logs)
        assert trend == "improving" or trend == "stable"

    def test_compute_confidence_trend_degrading(self):
        logs = [{"confidence": 0.9 - i * 0.01} for i in range(40)]
        trend = self.analyzer._compute_confidence_trend(logs)
        assert trend in ("degrading", "stable")

    def test_get_baseline_importance(self):
        val = self.analyzer.get_baseline_importance("ma_20")
        assert val == 0.35

    def test_get_baseline_importance_nonexistent(self):
        assert self.analyzer.get_baseline_importance("nope") is None


class TestDriftAlertManager:

    def setup_method(self):
        self.manager = DriftAlertManager()
        self.psi_rule = AlertRule(
            rule_id="test_psi",
            name="Test PSI Rule",
            drift_type=DriftType.DISTRIBUTION_SHIFT,
            severity=DriftSeverity.WARNING,
            metric="psi",
            threshold=0.1,
        )
        self.manager.add_rule(self.psi_rule)

    def test_add_rule(self):
        assert len(self.manager.get_rules()) == 1

    def test_add_rule_auto_id(self):
        m = DriftAlertManager()
        rule = AlertRule(name="Auto", drift_type=DriftType.DISTRIBUTION_SHIFT, severity=DriftSeverity.INFO, metric="psi", threshold=0.1)
        m.add_rule(rule)
        assert rule.rule_id.startswith("rule_")

    def test_remove_rule(self):
        ok = self.manager.remove_rule("test_psi")
        assert ok
        assert len(self.manager.get_rules()) == 0

    def test_remove_rule_nonexistent(self):
        assert not self.manager.remove_rule("nope")

    def test_evaluate_psi_triggers_alert(self):
        alert = self.manager.evaluate_psi("feat1", 0.15)
        assert alert is not None
        assert alert.feature_name == "feat1"
        assert alert.metric_value == 0.15

    def test_evaluate_psi_below_threshold(self):
        alert = self.manager.evaluate_psi("feat1", 0.05)
        assert alert is None

    def test_cooldown(self):
        self.manager.evaluate_psi("feat1", 0.15)
        alert2 = self.manager.evaluate_psi("feat1", 0.20)
        assert alert2 is None

    def test_evaluate_variance(self):
        var_rule = AlertRule(
            rule_id="test_var",
            name="Test Var",
            drift_type=DriftType.VARIANCE_ANOMALY,
            severity=DriftSeverity.WARNING,
            metric="z_score",
            threshold=2.0,
            cooldown_minutes=0,
        )
        self.manager.add_rule(var_rule)
        alert = self.manager.evaluate_variance("feat1", 3.0, 100.0)
        assert alert is not None
        assert alert.drift_type == DriftType.VARIANCE_ANOMALY

    def test_evaluate_contribution(self):
        contrib_rule = AlertRule(
            rule_id="test_contrib",
            name="Test Contrib",
            drift_type=DriftType.CONTRIBUTION_DRIFT,
            severity=DriftSeverity.WARNING,
            metric="importance_change_pct",
            threshold=20.0,
            cooldown_minutes=0,
        )
        self.manager.add_rule(contrib_rule)
        alert = self.manager.evaluate_contribution("feat1", 30.0)
        assert alert is not None
        assert alert.drift_type == DriftType.CONTRIBUTION_DRIFT

    def test_get_alerts_with_filters(self):
        self.manager.evaluate_psi("f1", 0.15)
        alerts = self.manager.get_alerts(severity=DriftSeverity.WARNING)
        assert len(alerts) >= 1
        info_alerts = self.manager.get_alerts(severity=DriftSeverity.INFO)
        assert len(info_alerts) == 0

    def test_get_alerts_unacknowledged(self):
        self.manager.evaluate_psi("f1", 0.15)
        unacked = self.manager.get_alerts(unacknowledged_only=True)
        assert all(not a.acknowledged for a in unacked)

    def test_acknowledge_alert(self):
        alert = self.manager.evaluate_psi("f1", 0.15)
        ok = self.manager.acknowledge_alert(alert.alert_id)
        assert ok
        alerts = self.manager.get_alerts(unacknowledged_only=True)
        assert alert.alert_id not in [a.alert_id for a in alerts]

    def test_acknowledge_nonexistent(self):
        assert not self.manager.acknowledge_alert("nope")

    def test_acknowledge_all(self):
        self.manager.evaluate_psi("f1", 0.15)
        self.manager.evaluate_psi("f2", 0.20)
        count = self.manager.acknowledge_all()
        assert count == 2
        assert self.manager.get_unacknowledged_count() == 0

    def test_acknowledge_all_by_feature(self):
        self.manager.evaluate_psi("f1", 0.15)
        self.manager.evaluate_psi("f2", 0.20)
        count = self.manager.acknowledge_all(feature_name="f1")
        assert count == 1

    def test_get_alert_summary(self):
        self.manager.evaluate_psi("f1", 0.15)
        summary = self.manager.get_alert_summary()
        assert summary["total_alerts"] == 1
        assert "by_severity" in summary
        assert "by_type" in summary

    def test_get_rules_by_type(self):
        rules = self.manager.get_rules(drift_type=DriftType.DISTRIBUTION_SHIFT)
        assert len(rules) == 1
        rules = self.manager.get_rules(drift_type=DriftType.VARIANCE_ANOMALY)
        assert len(rules) == 0


class TestBaselineManager:

    def setup_method(self):
        self.manager = BaselineManager(analytics_db=None)

    def test_store_and_get_baseline(self):
        self.manager.store_baseline("feat1", "general", [1.0, 2.0, 3.0, 4.0, 5.0])
        entry = self.manager.get_baseline("feat1")
        assert entry is not None
        assert entry["mean"] == 3.0
        assert entry["variance"] == 2.0

    def test_get_baseline_nonexistent(self):
        assert self.manager.get_baseline("nope") is None

    def test_get_baseline_values(self):
        self.manager.store_baseline("feat1", "general", [1.0, 2.0, 3.0])
        values = self.manager.get_baseline_values("feat1")
        assert values is not None
        np.testing.assert_array_equal(values, np.array([1.0, 2.0, 3.0]))

    def test_get_baseline_values_nonexistent(self):
        assert self.manager.get_baseline_values("nope") is None

    def test_store_with_label(self):
        self.manager.store_baseline("feat1", "general", [1.0, 2.0], label="v1")
        entry = self.manager.get_baseline("feat1", label="v1")
        assert entry is not None
        assert entry["label"] == "v1"

    def test_list_baselines(self):
        self.manager.store_baseline("f1", "g1", [1.0, 2.0])
        self.manager.store_baseline("f2", "g1", [3.0, 4.0])
        self.manager.store_baseline("f3", "g2", [5.0, 6.0])
        baselines = self.manager.list_baselines()
        assert len(baselines) == 3
        g1 = self.manager.list_baselines(group_name="g1")
        assert len(g1) == 2

    def test_remove_baseline(self):
        self.manager.store_baseline("f1", "g1", [1.0, 2.0])
        assert self.manager.get_baseline("f1", "g1") is not None
        self.manager.remove_baseline("f1", "g1")
        assert self.manager.get_baseline("f1", "g1") is None

    def test_remove_baseline_nonexistent(self):
        ok = self.manager.remove_baseline("nope")
        assert not ok


class TestDriftDetectionService:

    def setup_method(self):
        self.service = DriftDetectionService()

    def test_service_initialization(self):
        assert self.service.shift_analyzer is not None
        assert self.service.variance_tracker is not None
        assert self.service.contribution_analyzer is not None
        assert self.service.alert_manager is not None
        assert self.service.baseline_manager is not None

    def test_default_alert_rules(self):
        rules = self.service.alert_manager.get_rules()
        assert len(rules) == 4

    def test_initialize_baselines(self):
        baseline_data = {
            "feat1": [1.0, 2.0, 3.0, 4.0, 5.0],
        }
        self.service.initialize_baselines(baseline_data, group_name="g1")
        baselines = self.service.baseline_manager.list_baselines("g1")
        assert len(baselines) >= 1

    def test_get_service_status(self):
        status = self.service.get_service_status()
        assert "baseline_features" in status
        assert "tracked_features" in status
        assert "alert_rules" in status
        assert status["alert_rules"] == 4

    def test_analyze_feature_shift(self):
        baseline = np.array([10.0, 11.0, 10.5, 11.5, 10.0])
        current = np.array([15.0, 16.0, 14.5, 15.5, 16.0])
        result = self.service.analyze_feature_shift("feat1", baseline, current)
        assert result.feature_name == "feat1"

    def test_analyze_batch_shift(self):
        data = {
            "f1": {"baseline": np.array([1.0, 2.0, 3.0]), "current": np.array([4.0, 5.0, 6.0])},
            "f2": {"baseline": np.array([1.0, 2.0, 3.0]), "current": np.array([1.0, 2.0, 3.0])},
        }
        results = self.service.analyze_batch_shift(data)
        assert len(results) == 2

    def test_track_feature_variance(self):
        values = np.random.randn(20) * 0.1 + 10.0
        snapshot = self.service.track_feature_variance("feat1", values)
        assert snapshot is not None

    def test_track_feature_variance_insufficient(self):
        snapshot = self.service.track_feature_variance("feat1", np.array([1.0]))
        assert snapshot is None

    def test_track_batch_variance(self):
        report = self.service.track_batch_variance({
            "f1": np.random.randn(20) * 0.1 + 10.0,
            "f2": np.random.randn(20) * 0.1 + 20.0,
        })
        assert report.total_features == 2

    def test_analyze_prediction_contribution_first_call(self):
        report = self.service.analyze_prediction_contribution({"f1": 0.5, "f2": 0.3})
        assert "Baseline established" in report.summary

    def test_analyze_prediction_contribution(self):
        self.service.analyze_prediction_contribution({"f1": 0.5, "f2": 0.3})
        report = self.service.analyze_prediction_contribution({"f1": 0.6, "f2": 0.2})
        assert report.total_features == 2

    def test_run_full_pipeline(self):
        baseline = {"f1": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}
        current = {"f1": np.array([1.5, 2.5, 3.5, 4.5, 5.5])}
        importance = {"f1": 0.8, "f2": 0.2}
        results = self.service.run_full_pipeline(current, baseline, importance)
        assert "shift_results" in results
        assert "variance_report" in results
        assert "contribution_report" in results
        assert "alerts" in results

    def test_run_full_pipeline_no_baseline(self):
        current = {"f1": np.array([1.0, 2.0, 3.0, 4.0, 5.0])}
        results = self.service.run_full_pipeline(current, baseline_data={"f1": np.array([1.0, 2.0, 3.0])})
        assert results["variance_report"] is not None
