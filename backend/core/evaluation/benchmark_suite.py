from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

from loguru import logger

from core.evaluation.base import BaseEvaluator, BenchmarkConfig, EvaluationResult
from core.evaluation.evaluators.explanation_evaluator import ExplanationQualityEvaluator
from core.evaluation.evaluators.retrieval_evaluator import RetrievalPrecisionEvaluator
from core.evaluation.evaluators.reflection_evaluator import ReflectionAccuracyEvaluator
from core.evaluation.evaluators.hallucination_evaluator import HallucinationDetector
from core.evaluation.evaluators.latency_benchmarker import LatencyBenchmarker
from core.evaluation.metrics_store import EvalMetricsStore


class BenchmarkRunner:
    def __init__(self, store: Optional[EvalMetricsStore] = None):
        self._store = store or EvalMetricsStore()
        self._evaluators: dict[str, BaseEvaluator] = {}

    def register(self, name: str, evaluator: BaseEvaluator):
        self._evaluators[name] = evaluator

    def register_defaults(self, config: Optional[BenchmarkConfig] = None):
        base_config = config or BenchmarkConfig(name="default")
        self.register("explanation_quality", ExplanationQualityEvaluator(config=base_config))
        self.register("retrieval_precision", RetrievalPrecisionEvaluator(config=base_config))
        self.register("reflection_accuracy", ReflectionAccuracyEvaluator(config=base_config))
        self.register("hallucination_detection", HallucinationDetector(config=base_config))
        self.register("latency_benchmark", LatencyBenchmarker(config=base_config))

    async def run_all(self, warmup: bool = True) -> list[EvaluationResult]:
        if warmup:
            await self._run_warmup()
        results = []
        for name, evaluator in self._evaluators.items():
            try:
                logger.info(f"Running benchmark: {name}")
                result = await evaluator.evaluate()
                self._store.store_result(result)
                results.append(result)
                logger.info(f"  {name}: passed={result.passed} "
                           f"({result.total_duration_ms:.1f}ms, {len(result.metrics)} metrics)")
            except Exception as e:
                logger.error(f"Benchmark {name} failed: {e}")
        return results

    async def run_selected(self, names: list[str]) -> list[EvaluationResult]:
        results = []
        for name in names:
            evaluator = self._evaluators.get(name)
            if evaluator is None:
                logger.warning(f"Evaluator '{name}' not registered, skipping")
                continue
            try:
                result = await evaluator.evaluate()
                self._store.store_result(result)
                results.append(result)
            except Exception as e:
                logger.error(f"Benchmark {name} failed: {e}")
        return results

    async def _run_warmup(self):
        for evaluator in self._evaluators.values():
            for _ in range(evaluator.config.warmup_runs):
                try:
                    await evaluator.evaluate()
                except Exception:
                    pass

    def get_store(self) -> EvalMetricsStore:
        return self._store


class BenchmarkSuite:
    def __init__(self, runner: Optional[BenchmarkRunner] = None):
        self._runner = runner or BenchmarkRunner()

    async def run_full(
        self,
        store_results: bool = True,
        warmup: bool = True,
    ) -> list[EvaluationResult]:
        self._runner.register_defaults()
        results = await self._runner.run_all(warmup=warmup)
        return results

    async def run_partial(
        self,
        evaluator_names: list[str],
        store_results: bool = True,
    ) -> list[EvaluationResult]:
        self._runner.register_defaults()
        return await self._runner.run_selected(evaluator_names)

    def get_runner(self) -> BenchmarkRunner:
        return self._runner
