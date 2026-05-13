from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class DriftSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class DriftType(str, Enum):
    DISTRIBUTION_SHIFT = "distribution_shift"
    VARIANCE_ANOMALY = "variance_anomaly"
    CONTRIBUTION_DRIFT = "contribution_drift"


class AlertRule(BaseModel):
    rule_id: str = ""
    name: str = ""
    drift_type: DriftType = DriftType.DISTRIBUTION_SHIFT
    severity: DriftSeverity = DriftSeverity.WARNING
    metric: str = "psi"
    operator: str = ">="
    threshold: float = 0.25
    cooldown_minutes: int = 60
    enabled: bool = True
    description: str = ""


class DriftAlert(BaseModel):
    alert_id: str = ""
    rule_id: str = ""
    rule_name: str = ""
    severity: DriftSeverity = DriftSeverity.WARNING
    drift_type: DriftType = DriftType.DISTRIBUTION_SHIFT
    feature_name: str = ""
    group_name: str = "general"
    metric: str = "psi"
    metric_value: float = 0.0
    threshold: float = 0.0
    message: str = ""
    acknowledged: bool = False
    acknowledged_at: Optional[str] = None
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DriftAlertManager:
    def __init__(self):
        self._alerts: list[DriftAlert] = []
        self._rules: list[AlertRule] = []
        self._last_fired: dict[str, datetime] = {}
        self._alert_counter = 0

    def add_rule(self, rule: AlertRule):
        if not rule.rule_id:
            rule.rule_id = f"rule_{len(self._rules)}_{datetime.now(timezone.utc).timestamp()}"
        self._rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        for i, r in enumerate(self._rules):
            if r.rule_id == rule_id:
                self._rules.pop(i)
                return True
        return False

    def get_rules(self, drift_type: Optional[DriftType] = None) -> list[AlertRule]:
        if drift_type:
            return [r for r in self._rules if r.drift_type == drift_type]
        return list(self._rules)

    def evaluate_psi(self, feature_name: str, psi: float, group_name: str = "general") -> Optional[DriftAlert]:
        for rule in self._rules:
            if not rule.enabled or rule.drift_type != DriftType.DISTRIBUTION_SHIFT:
                continue
            if psi >= rule.threshold:
                return self._fire_alert(rule, feature_name, group_name, "psi", psi)
        return None

    def evaluate_variance(self, feature_name: str, z_score: float, variance_change_pct: float, group_name: str = "general") -> Optional[DriftAlert]:
        for rule in self._rules:
            if not rule.enabled or rule.drift_type != DriftType.VARIANCE_ANOMALY:
                continue
            metric_value = z_score if rule.metric == "z_score" else variance_change_pct
            if metric_value >= rule.threshold:
                return self._fire_alert(rule, feature_name, group_name, rule.metric, metric_value)
        return None

    def evaluate_contribution(self, feature_name: str, change_pct: float, group_name: str = "general") -> Optional[DriftAlert]:
        for rule in self._rules:
            if not rule.enabled or rule.drift_type != DriftType.CONTRIBUTION_DRIFT:
                continue
            if abs(change_pct) >= rule.threshold:
                return self._fire_alert(rule, feature_name, group_name, "importance_change_pct", change_pct)
        return None

    def _fire_alert(self, rule: AlertRule, feature_name: str, group_name: str, metric: str, metric_value: float) -> Optional[DriftAlert]:
        now = datetime.now(timezone.utc)
        cooldown_key = f"{rule.rule_id}__{feature_name}"

        if cooldown_key in self._last_fired:
            elapsed = (now - self._last_fired[cooldown_key]).total_seconds() / 60
            if elapsed < rule.cooldown_minutes:
                return None

        self._last_fired[cooldown_key] = now
        self._alert_counter += 1

        alert = DriftAlert(
            alert_id=f"alert_{self._alert_counter}_{int(now.timestamp())}",
            rule_id=rule.rule_id,
            rule_name=rule.name,
            severity=rule.severity,
            drift_type=rule.drift_type,
            feature_name=feature_name,
            group_name=group_name,
            metric=metric,
            metric_value=round(metric_value, 6),
            threshold=rule.threshold,
            message=f"{rule.name}: {feature_name} {metric}={metric_value:.4f} (threshold={rule.threshold})",
        )
        self._alerts.append(alert)
        return alert

    def get_alerts(self, severity: Optional[DriftSeverity] = None, limit: int = 50, unacknowledged_only: bool = False) -> list[DriftAlert]:
        results = list(self._alerts)
        if severity:
            results = [a for a in results if a.severity == severity]
        if unacknowledged_only:
            results = [a for a in results if not a.acknowledged]
        results.sort(key=lambda a: a.generated_at, reverse=True)
        return results[:limit]

    def acknowledge_alert(self, alert_id: str) -> bool:
        for alert in self._alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def acknowledge_all(self, feature_name: Optional[str] = None) -> int:
        count = 0
        for alert in self._alerts:
            if not alert.acknowledged:
                if feature_name is None or alert.feature_name == feature_name:
                    alert.acknowledged = True
                    alert.acknowledged_at = datetime.now(timezone.utc).isoformat()
                    count += 1
        return count

    def get_unacknowledged_count(self) -> int:
        return sum(1 for a in self._alerts if not a.acknowledged)

    def get_alert_summary(self) -> dict[str, Any]:
        total = len(self._alerts)
        by_severity = {}
        by_type = {}
        unacked = self.get_unacknowledged_count()
        for alert in self._alerts:
            by_severity[alert.severity.value] = by_severity.get(alert.severity.value, 0) + 1
            by_type[alert.drift_type.value] = by_type.get(alert.drift_type.value, 0) + 1
        return {
            "total_alerts": total,
            "unacknowledged": unacked,
            "by_severity": by_severity,
            "by_type": by_type,
        }
