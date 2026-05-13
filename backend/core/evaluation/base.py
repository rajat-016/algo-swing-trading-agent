from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


class MetricType(str, enum.Enum):
    EXPLANATION_QUALITY = "explanation_quality"
    RETRIEVAL_PRECISION = "retrieval_precision"
    REFLECTION_ACCURACY = "reflection_accuracy"
    HALLUCINATION_SCORE = "hallucination_score"
    LATENCY = "latency"


@dataclass
class EvalMetric:
    name: str
    value: float
    metric_type: MetricType
    threshold: Optional[float] = None
    passed: Optional[bool] = None
    unit: str = ""
    details: Optional[dict[str, Any]] = None

    def __post_init__(self):
        if self.threshold is not None and self.passed is None:
            if self.metric_type in (MetricType.LATENCY, MetricType.HALLUCINATION_SCORE):
                self.passed = self.value <= self.threshold
            else:
                self.passed = self.value >= self.threshold


@dataclass
class EvaluationResult:
    evaluator_name: str
    metrics: list[EvalMetric]
    passed: bool
    total_duration_ms: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    metadata: Optional[dict[str, Any]] = None

    @property
    def summary(self) -> dict[str, Any]:
        return {
            "evaluator": self.evaluator_name,
            "passed": self.passed,
            "total_metrics": len(self.metrics),
            "passed_metrics": sum(1 for m in self.metrics if m.passed),
            "failed_metrics": sum(1 for m in self.metrics if m.passed is False),
            "duration_ms": round(self.total_duration_ms, 2),
            "timestamp": self.timestamp,
            "scores": {m.name: {"value": m.value, "passed": m.passed, "threshold": m.threshold} for m in self.metrics},
        }


@dataclass
class BenchmarkConfig:
    name: str
    description: str = ""
    n_runs: int = 3
    warmup_runs: int = 1
    timeout_seconds: int = 120
    thresholds: Optional[dict[str, float]] = None
    metadata: Optional[dict[str, Any]] = None


class BaseEvaluator:
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        self.config = config or BenchmarkConfig(name=self.__class__.__name__)

    async def evaluate(self) -> EvaluationResult:
        start = time.monotonic()
        metrics = await self._run_evaluation()
        duration = (time.monotonic() - start) * 1000
        passed = all(m.passed is not False for m in metrics)
        return EvaluationResult(
            evaluator_name=self.__class__.__name__,
            metrics=metrics,
            passed=passed,
            total_duration_ms=duration,
            metadata={"config_name": self.config.name},
        )

    async def _run_evaluation(self) -> list[EvalMetric]:
        raise NotImplementedError
