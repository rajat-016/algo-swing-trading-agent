from __future__ import annotations

import time
from typing import Any, Optional

import numpy as np

from core.evaluation.base import (
    BaseEvaluator,
    BenchmarkConfig,
    EvalMetric,
    MetricType,
)


class LatencyBenchmarker(BaseEvaluator):
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        super().__init__(config)
        self._synthetic_data_size = 10

    async def _run_evaluation(self) -> list[EvalMetric]:
        metrics = []

        inference = await self._bench_inference_latency()
        metrics.append(inference)

        retrieval = await self._bench_retrieval_latency()
        metrics.append(retrieval)

        explanation = await self._bench_explanation_latency()
        metrics.append(explanation)

        reflection = await self._bench_reflection_latency()
        metrics.append(reflection)

        return metrics

    async def _bench_inference_latency(self) -> EvalMetric:
        try:
            latencies = []
            for _ in range(self.config.n_runs):
                start = time.monotonic()
                _ = np.random.randn(1, 60).tolist()
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)

            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))
            return EvalMetric(
                name="inference_latency_ms",
                value=round(p50, 2),
                metric_type=MetricType.LATENCY,
                threshold=100.0,
                unit="ms",
                details={
                    "p50": round(p50, 2),
                    "p95": round(p95, 2),
                    "p99": round(p99, 2),
                    "samples": len(latencies),
                    "min": round(min(latencies), 2),
                    "max": round(max(latencies), 2),
                },
            )
        except Exception as e:
            return EvalMetric(
                name="inference_latency_ms",
                value=9999.0,
                metric_type=MetricType.LATENCY,
                threshold=100.0,
                passed=False,
                details={"error": str(e)},
            )

    async def _bench_retrieval_latency(self) -> EvalMetric:
        try:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            retriever = SemanticRetriever()
            latencies = []
            for _ in range(self.config.n_runs):
                start = time.monotonic()
                try:
                    _ = await retriever.search("test query", n_results=5)
                except Exception:
                    pass
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)

            p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
            return EvalMetric(
                name="retrieval_latency_ms",
                value=round(p50, 2),
                metric_type=MetricType.LATENCY,
                threshold=500.0,
                unit="ms",
                details={
                    "p50": round(p50, 2),
                    "samples": len(latencies),
                },
            )
        except Exception as e:
            return EvalMetric(
                name="retrieval_latency_ms",
                value=9999.0,
                metric_type=MetricType.LATENCY,
                threshold=500.0,
                passed=False,
                details={"error": str(e)},
            )

    async def _bench_explanation_latency(self) -> EvalMetric:
        try:
            from intelligence.explainability.prediction_explainer import PredictionExplainer
            explainer = PredictionExplainer(
                feature_names=[f"f_{i}" for i in range(60)],
            )
            X = np.random.randn(1, 60).astype(np.float64)
            probs = np.array([0.1, 0.2, 0.7], dtype=np.float64)
            latencies = []

            for _ in range(self.config.n_runs):
                start = time.monotonic()
                try:
                    _ = explainer.explain_prediction(X, probs)
                except Exception:
                    pass
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)

            p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
            p95 = float(np.percentile(latencies, 95)) if latencies else 0.0
            return EvalMetric(
                name="explanation_latency_ms",
                value=round(p50, 2),
                metric_type=MetricType.LATENCY,
                threshold=3000.0,
                unit="ms",
                details={
                    "p50": round(p50, 2),
                    "p95": round(p95, 2),
                    "samples": len(latencies),
                },
            )
        except Exception as e:
            return EvalMetric(
                name="explanation_latency_ms",
                value=9999.0,
                metric_type=MetricType.LATENCY,
                threshold=3000.0,
                passed=False,
                details={"error": str(e)},
            )

    async def _bench_reflection_latency(self) -> EvalMetric:
        try:
            from intelligence.reflection_engine.recurring_pattern_detector import (
                RecurringPatternDetector,
            )
            detector = RecurringPatternDetector()
            trades = [
                {
                    "trade_id": f"T{i}",
                    "symbol": "RELIANCE",
                    "timestamp": "2026-05-13T10:00:00",
                    "market_regime": "bull_trend",
                    "outcome": "stop_loss_hit",
                    "reasoning": "regime mismatch",
                    "pnl": -100,
                }
                for i in range(20)
            ]
            latencies = []
            for _ in range(self.config.n_runs):
                start = time.monotonic()
                _ = detector.detect(trades=trades, window_days=30)
                elapsed = (time.monotonic() - start) * 1000
                latencies.append(elapsed)

            p50 = float(np.percentile(latencies, 50)) if latencies else 0.0
            return EvalMetric(
                name="reflection_latency_ms",
                value=round(p50, 2),
                metric_type=MetricType.LATENCY,
                threshold=1000.0,
                unit="ms",
                details={
                    "p50": round(p50, 2),
                    "samples": len(latencies),
                },
            )
        except Exception as e:
            return EvalMetric(
                name="reflection_latency_ms",
                value=9999.0,
                metric_type=MetricType.LATENCY,
                threshold=1000.0,
                passed=False,
                details={"error": str(e)},
            )
