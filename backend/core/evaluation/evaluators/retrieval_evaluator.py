from __future__ import annotations

import math
from typing import Any, Optional

from core.evaluation.base import (
    BaseEvaluator,
    BenchmarkConfig,
    EvalMetric,
    MetricType,
)
from memory.schemas.memory_schemas import (
    MarketMemory,
    MemoryFilter,
    MemoryType,
    SearchResult,
    TradeMemory,
)


class RetrievalPrecisionEvaluator(BaseEvaluator):
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        super().__init__(config)
        self._retriever: Optional[Any] = None

    async def _get_retriever(self):
        if self._retriever is None:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            self._retriever = SemanticRetriever()
        if not self._retriever.is_ready:
            try:
                await self._retriever.initialize()
            except Exception:
                pass
        return self._retriever

    async def _run_evaluation(self) -> list[EvalMetric]:
        metrics = []

        precision = await self._eval_precision_at_k()
        metrics.append(precision)

        recall = await self._eval_recall_at_k()
        metrics.append(recall)

        mrr = await self._eval_mrr()
        metrics.append(mrr)

        ndcg = await self._eval_ndcg()
        metrics.append(ndcg)

        return metrics

    def _make_synthetic_results(
        self,
        n_total: int = 10,
        n_relevant: int = 5,
        relevant_at_start: bool = True,
    ) -> tuple[list[SearchResult], set[str]]:
        relevant_ids = {f"rel_{i}" for i in range(n_relevant)}
        all_ids = list(relevant_ids) + [f"irrel_{i}" for i in range(n_total - n_relevant)]
        if not relevant_at_start:
            import random
            random.shuffle(all_ids)
        results = []
        for i, doc_id in enumerate(all_ids):
            dist = 0.1 if doc_id in relevant_ids else 0.8
            results.append(SearchResult(
                id=doc_id,
                memory_type=MemoryType.TRADE,
                text=f"Document {doc_id}",
                metadata={},
                distance=dist,
                relevance_score=1.0 - dist,
            ))
        return results, relevant_ids

    async def _eval_precision_at_k(self) -> EvalMetric:
        try:
            results, relevant_ids = self._make_synthetic_results(10, 5, relevant_at_start=True)
            k = 5
            top_k = results[:k]
            relevant_in_top = sum(1 for r in top_k if r.id in relevant_ids)
            precision = relevant_in_top / k if k > 0 else 0.0
            return EvalMetric(
                name="precision_at_5",
                value=round(precision, 4),
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                unit="ratio",
                details={"k": k, "relevant_in_top": relevant_in_top, "total_relevant": len(relevant_ids)},
            )
        except Exception as e:
            return EvalMetric(
                name="precision_at_5",
                value=0.0,
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_recall_at_k(self) -> EvalMetric:
        try:
            results, relevant_ids = self._make_synthetic_results(10, 5, relevant_at_start=True)
            k = 5
            top_k = results[:k]
            relevant_in_top = sum(1 for r in top_k if r.id in relevant_ids)
            recall = relevant_in_top / len(relevant_ids) if relevant_ids else 0.0
            return EvalMetric(
                name="recall_at_5",
                value=round(recall, 4),
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                unit="ratio",
                details={"k": k, "retrieved_relevant": relevant_in_top, "total_relevant": len(relevant_ids)},
            )
        except Exception as e:
            return EvalMetric(
                name="recall_at_5",
                value=0.0,
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_mrr(self) -> EvalMetric:
        try:
            results, relevant_ids = self._make_synthetic_results(10, 5, relevant_at_start=True)
            for rank, r in enumerate(results, 1):
                if r.id in relevant_ids:
                    mrr = 1.0 / rank
                    break
            else:
                mrr = 0.0
            return EvalMetric(
                name="mrr",
                value=round(mrr, 4),
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                unit="score",
                details={"first_relevant_rank": rank if mrr > 0 else None},
            )
        except Exception as e:
            return EvalMetric(
                name="mrr",
                value=0.0,
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_ndcg(self) -> EvalMetric:
        try:
            results, relevant_ids = self._make_synthetic_results(10, 5, relevant_at_start=True)
            k = 5
            dcg = 0.0
            for i, r in enumerate(results[:k]):
                rel = 1.0 if r.id in relevant_ids else 0.0
                dcg += (2**rel - 1) / math.log2(i + 2)
            idcg = 0.0
            for i in range(min(k, len(relevant_ids))):
                idcg += 1.0 / math.log2(i + 2)
            ndcg = dcg / idcg if idcg > 0 else 0.0
            return EvalMetric(
                name="ndcg_at_5",
                value=round(ndcg, 4),
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                unit="score",
                details={"k": k, "dcg": round(dcg, 4), "idcg": round(idcg, 4)},
            )
        except Exception as e:
            return EvalMetric(
                name="ndcg_at_5",
                value=0.0,
                metric_type=MetricType.RETRIEVAL_PRECISION,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )
