from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.evaluation.benchmark_suite import BenchmarkSuite
from core.evaluation.metrics_store import EvalMetricsStore
from core.evaluation.regression_detector import RegressionDetector
from core.evaluation.base import MetricType

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


class RunBenchmarkRequest(BaseModel):
    evaluators: Optional[list[str]] = Field(
        default=None,
        description="List of evaluators to run. If None, runs all.",
    )
    warmup: bool = Field(default=True, description="Run warmup before benchmarks")


class RegressionCheckRequest(BaseModel):
    zscore_threshold: float = Field(default=2.0, ge=0.5, le=5.0)
    min_samples: int = Field(default=5, ge=3)


@router.post("/run")
async def run_benchmark(req: RunBenchmarkRequest) -> dict[str, Any]:
    suite = BenchmarkSuite()
    if req.evaluators:
        results = await suite.run_partial(req.evaluators)
    else:
        results = await suite.run_full(warmup=req.warmup)
    return {
        "status": "ok",
        "total_benchmarks": len(results),
        "passed": sum(1 for r in results if r.passed),
        "failed": sum(1 for r in results if not r.passed),
        "results": [r.summary for r in results],
    }


@router.get("/metrics")
async def get_metrics(
    evaluator: Optional[str] = None,
    limit: int = 20,
) -> dict[str, Any]:
    store = EvalMetricsStore()
    if evaluator:
        latest = store.get_latest_by_evaluator(evaluator)
        if latest is None:
            raise HTTPException(status_code=404, detail=f"No results for evaluator: {evaluator}")
        return {
            "status": "ok",
            "evaluator": evaluator,
            "result": latest.summary,
        }
    runs = store.get_recent_runs(limit=limit)
    return {"status": "ok", "runs": runs}


@router.get("/regression")
async def check_regression(
    zscore_threshold: float = 2.0,
    min_samples: int = 5,
) -> dict[str, Any]:
    detector = RegressionDetector()
    health = detector.get_health_score()
    return {
        "status": "ok",
        "health_score": health["health_score"],
        "total_metrics_monitored": health["total_metrics"],
        "healthy_metrics": health["healthy_metrics"],
        "regression_count": health["regression_count"],
        "regressions": health["regressions"],
    }


@router.post("/regression/check")
async def check_specific_regression(req: RegressionCheckRequest) -> dict[str, Any]:
    detector = RegressionDetector()
    results = []
    for mt in MetricType:
        check = detector.check_regression(mt.value, req.zscore_threshold, req.min_samples)
        results.append(check)
    return {
        "status": "ok",
        "zscore_threshold": req.zscore_threshold,
        "results": results,
    }


@router.get("/health")
async def evaluation_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "service": "ai_evaluation_framework",
        "version": "1.0.0",
        "evaluators": [
            "explanation_quality",
            "retrieval_precision",
            "reflection_accuracy",
            "hallucination_detection",
            "latency_benchmark",
        ],
        "metric_types": [mt.value for mt in MetricType],
    }
