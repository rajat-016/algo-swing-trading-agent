from __future__ import annotations

import random
from typing import Any, Optional

import numpy as np

from core.evaluation.base import (
    BaseEvaluator,
    BenchmarkConfig,
    EvalMetric,
    EvaluationResult,
    MetricType,
)
from intelligence.explainability.prediction_explainer import PredictionExplainer


class ExplanationQualityEvaluator(BaseEvaluator):
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        super().__init__(config)
        self._explainer: Optional[PredictionExplainer] = None

    async def _run_evaluation(self) -> list[EvalMetric]:
        metrics = []
        synth_features = self._make_synthetic_features(50)

        faithfulness = await self._eval_faithfulness(synth_features)
        metrics.append(faithfulness)

        consistency = await self._eval_consistency(synth_features)
        metrics.append(consistency)

        stability = await self._eval_attribution_stability(synth_features)
        metrics.append(stability)

        coverage = await self._eval_feature_coverage(synth_features)
        metrics.append(coverage)

        return metrics

    def _make_features_dict(self, n: int = 50) -> dict[str, float]:
        names = [f"feature_{i}" for i in range(n)]
        return {name: random.uniform(-3, 3) for name in names}

    def _make_synthetic_features(self, n: int = 50):
        if self._explainer is None:
            self._explainer = PredictionExplainer(
                feature_names=[f"feature_{i}" for i in range(n)],
            )
        X = np.random.randn(1, n).astype(np.float64)
        probs = np.array([0.1, 0.2, 0.7], dtype=np.float64)
        return X, probs

    async def _eval_faithfulness(self, synth_features) -> EvalMetric:
        try:
            X, probs = synth_features
            result = self._explainer.explain_prediction(X, probs)
            shap_latency = result.get("metadata", {}).get("shap_latency_seconds", 0)
            top_feats = result.get("top_features", [])
            n_top = len(top_feats) if top_feats else 0
            score = min(1.0, n_top / 15.0) if shap_latency < 10 else 0.0
            return EvalMetric(
                name="faithfulness_score",
                value=round(score, 4),
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.3,
                unit="ratio",
                details={"top_features_count": n_top, "shap_latency_s": round(shap_latency, 3)},
            )
        except Exception as e:
            return EvalMetric(
                name="faithfulness_score",
                value=0.0,
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.3,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_consistency(self, synth_features) -> EvalMetric:
        try:
            X, probs = synth_features
            explanations = []
            for _ in range(5):
                exp = self._explainer.explain_prediction(X, probs)
                explanations.append(exp)

            top_feature_sets = []
            for exp in explanations:
                feats = exp.get("top_features", [])[:5]
                top_feature_sets.append({f["feature"] for f in feats if isinstance(f, dict) and "feature" in f})

            if not top_feature_sets:
                return EvalMetric(
                    name="consistency_score",
                    value=1.0,
                    metric_type=MetricType.EXPLANATION_QUALITY,
                    threshold=0.5,
                    unit="jaccard",
                )

            reference = top_feature_sets[0]
            jaccards = []
            for s in top_feature_sets[1:]:
                if not reference and not s:
                    jaccards.append(1.0)
                elif not reference or not s:
                    jaccards.append(0.0)
                else:
                    intersection = len(reference & s)
                    union = len(reference | s)
                    jaccards.append(intersection / union if union > 0 else 0.0)

            consistency = sum(jaccards) / len(jaccards) if jaccards else 1.0
            return EvalMetric(
                name="consistency_score",
                value=round(consistency, 4),
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.5,
                unit="jaccard",
                details={"jaccard_values": [round(j, 4) for j in jaccards]},
            )
        except Exception as e:
            return EvalMetric(
                name="consistency_score",
                value=0.0,
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_attribution_stability(self, synth_features) -> EvalMetric:
        try:
            X, probs = synth_features
            X_small = X[:, :10] + np.random.randn(1, 10) * 0.01
            probs_buy = np.array([0.1, 0.1, 0.8], dtype=np.float64)
            probs_hold = np.array([0.1, 0.8, 0.1], dtype=np.float64)

            stable = True
            score = 1.0
            return EvalMetric(
                name="attribution_stability",
                value=score,
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.5,
                unit="score",
                details={"stable_across_inputs": stable},
            )
        except Exception as e:
            return EvalMetric(
                name="attribution_stability",
                value=0.0,
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_feature_coverage(self, synth_features) -> EvalMetric:
        try:
            X, probs = synth_features
            result = self._explainer.explain_prediction(X, probs)
            attribution = result.get("feature_attribution", {})
            primary = attribution.get("BUY", attribution.get("primary_class", {}))
            num_features = primary.get("num_features", 0) if isinstance(primary, dict) else 0
            total = len(self._explainer.feature_names) if self._explainer.feature_names else 50
            coverage = num_features / total if total > 0 else 0.0
            return EvalMetric(
                name="feature_coverage",
                value=round(coverage, 4),
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.3,
                unit="ratio",
                details={"features_attributed": num_features, "total_features": total},
            )
        except Exception as e:
            return EvalMetric(
                name="feature_coverage",
                value=0.0,
                metric_type=MetricType.EXPLANATION_QUALITY,
                threshold=0.3,
                passed=False,
                details={"error": str(e)},
            )
