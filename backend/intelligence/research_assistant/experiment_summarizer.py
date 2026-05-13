from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class ExperimentRun(BaseModel):
    run_id: str
    experiment_name: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metrics: dict[str, float] = Field(default_factory=dict)
    parameters: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None


class ExperimentSummary(BaseModel):
    experiment_name: str
    total_runs: int = 0
    best_run: Optional[ExperimentRun] = None
    worst_run: Optional[ExperimentRun] = None
    metric_trends: dict[str, dict] = Field(default_factory=dict)
    parameter_sensitivity: dict[str, Any] = Field(default_factory=dict)
    key_findings: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class ExperimentSummarizer:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db

    def _get_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    async def summarize_experiment(
        self,
        experiment_name: str,
        runs: Optional[list[ExperimentRun]] = None,
        primary_metric: str = "sharpe_ratio",
    ) -> ExperimentSummary:
        if runs is not None:
            experiment_runs = runs
        else:
            experiment_runs = await self._load_runs(experiment_name)

        if not experiment_runs:
            return ExperimentSummary(
                experiment_name=experiment_name,
                summary="No experiment runs found",
            )

        valid = [r for r in experiment_runs if r.metrics]
        if not valid:
            return ExperimentSummary(
                experiment_name=experiment_name,
                total_runs=len(experiment_runs),
                summary="No runs with metrics data",
            )

        sorted_runs = sorted(
            valid,
            key=lambda r: r.metrics.get(primary_metric, 0),
            reverse=True,
        )
        best_run = sorted_runs[0] if sorted_runs else None
        worst_run = sorted_runs[-1] if len(sorted_runs) > 1 else None

        metric_trends = self._compute_trends(valid)
        param_sensitivity = self._analyze_parameter_sensitivity(valid, primary_metric)
        findings = self._generate_findings(
            experiment_name, valid, best_run, worst_run, primary_metric, metric_trends,
        )

        summary = (
            f"Experiment '{experiment_name}': {len(valid)} valid runs | "
            f"Best {primary_metric}={best_run.metrics.get(primary_metric, 'N/A') if best_run else 'N/A'} | "
            f"{len(findings)} key findings"
        )

        return ExperimentSummary(
            experiment_name=experiment_name,
            total_runs=len(experiment_runs),
            best_run=best_run,
            worst_run=worst_run,
            metric_trends=metric_trends,
            parameter_sensitivity=param_sensitivity,
            key_findings=findings,
            summary=summary,
        )

    async def _load_runs(self, experiment_name: str) -> list[ExperimentRun]:
        db = self._get_db()
        if db is None:
            return []
        try:
            rows = db.fetch_all(
                "SELECT * FROM experiment_runs WHERE experiment_name = ? ORDER BY created_at DESC",
                [experiment_name],
            )
            results = []
            for r in rows:
                d = dict(zip([col[0] for col in (db.description or [])], r))
                results.append(ExperimentRun(
                    run_id=str(d.get("run_id", "")),
                    experiment_name=d.get("experiment_name", experiment_name),
                    timestamp=str(d.get("created_at", datetime.now(timezone.utc).isoformat())),
                    metrics=d.get("metrics", {}) if isinstance(d.get("metrics"), dict) else {},
                    parameters=d.get("parameters", {}) if isinstance(d.get("parameters"), dict) else {},
                    notes=d.get("notes"),
                ))
            return results
        except Exception as e:
            logger.debug(f"Failed to load experiment runs: {e}")
            return []

    def _compute_trends(self, runs: list[ExperimentRun]) -> dict[str, dict]:
        trends: dict[str, dict] = {}
        if len(runs) < 2:
            return trends

        sorted_by_time = sorted(runs, key=lambda r: r.timestamp)
        all_metrics = set()
        for r in sorted_by_time:
            all_metrics.update(r.metrics.keys())

        for metric in all_metrics:
            values = [r.metrics.get(metric) for r in sorted_by_time if metric in r.metrics]
            values = [v for v in values if v is not None]
            if len(values) < 2:
                continue

            first_half = values[: len(values) // 2]
            second_half = values[len(values) // 2 :]
            trend_direction = "stable"
            if first_half and second_half:
                avg_first = sum(first_half) / len(first_half)
                avg_second = sum(second_half) / len(second_half)
                change = ((avg_second - avg_first) / abs(avg_first)) * 100 if avg_first != 0 else 0
                if change > 5:
                    trend_direction = "improving"
                elif change < -5:
                    trend_direction = "deteriorating"

            trends[metric] = {
                "values": values,
                "min": min(values),
                "max": max(values),
                "avg": round(sum(values) / len(values), 4),
                "trend": trend_direction,
                "change_pct": round(((values[-1] - values[0]) / abs(values[0])) * 100 if values[0] != 0 else 0, 2),
            }

        return trends

    def _analyze_parameter_sensitivity(
        self, runs: list[ExperimentRun], primary_metric: str,
    ) -> dict[str, Any]:
        sensitivity: dict[str, Any] = {}
        param_values: dict[str, list[tuple[Any, float]]] = {}

        for r in runs:
            metric_val = r.metrics.get(primary_metric, 0)
            for param, value in r.parameters.items():
                if param not in param_values:
                    param_values[param] = []
                param_values[param].append((value, metric_val))

        for param, pairs in param_values.items():
            values_set = set(str(p[0]) for p in pairs)
            if len(values_set) < 2:
                continue

            grouped: dict[str, list[float]] = {}
            for val, metric in pairs:
                key = str(val)
                if key not in grouped:
                    grouped[key] = []
                grouped[key].append(metric)

            avg_by_value = {k: sum(v) / len(v) for k, v in grouped.items()}
            max_val = max(avg_by_value.values())
            min_val = min(avg_by_value.values())

            best_value = max(avg_by_value, key=avg_by_value.get)
            worst_value = min(avg_by_value, key=avg_by_value.get)

            sensitivity[param] = {
                "best_value": best_value,
                "worst_value": worst_value,
                "impact_range": round(max_val - min_val, 4),
                "impact_pct": round(((max_val - min_val) / abs(min_val)) * 100 if min_val != 0 else 0, 2),
            }

        return sensitivity

    def _generate_findings(
        self,
        name: str,
        runs: list[ExperimentRun],
        best: Optional[ExperimentRun],
        worst: Optional[ExperimentRun],
        primary_metric: str,
        trends: dict[str, dict],
    ) -> list[str]:
        findings = []
        if best and worst and best.run_id != worst.run_id:
            findings.append(
                f"Best run ({best.run_id}) has {primary_metric}={best.metrics.get(primary_metric, 'N/A'):.4f} "
                f"vs worst ({worst.run_id})={worst.metrics.get(primary_metric, 'N/A'):.4f}"
            )

        for metric, trend in trends.items():
            if trend.get("trend") == "improving":
                findings.append(f"{metric} is improving ({trend.get('change_pct', 0):.1f}% change)")
            elif trend.get("trend") == "deteriorating":
                findings.append(f"{metric} is deteriorating ({trend.get('change_pct', 0):.1f}% change)")

        return findings
