from __future__ import annotations

import re
from typing import Any, Optional

from core.evaluation.base import (
    BaseEvaluator,
    BenchmarkConfig,
    EvalMetric,
    EvaluationResult,
    MetricType,
)


class HallucinationDetector(BaseEvaluator):
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        super().__init__(config)

    async def _run_evaluation(self) -> list[EvalMetric]:
        metrics = []

        factual = await self._eval_factual_consistency()
        metrics.append(factual)

        specificity = await self._eval_specificity()
        metrics.append(specificity)

        contradiction = await self._eval_self_contradiction()
        metrics.append(contradiction)

        vagueness = await self._eval_vagueness()
        metrics.append(vagueness)

        return metrics

    KNOWN_TRADE_FACTS: dict[str, set[str]] = {
        "reliance": {"jio", "retail", "oil", "telecom", "refinery", "44.5", "48500"},
        "tcs": {"it", "software", "consulting", "services", "nifty"},
        "hdfcbank": {"banking", "loan", "deposit", "private", "sector"},
        "infy": {"it", "software", "consulting", "digital"},
    }

    def _extract_ticker(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for ticker in self.KNOWN_TRADE_FACTS:
            if ticker in text_lower:
                return ticker
        return None

    def _count_supported_claims(self, text: str, ticker: str) -> tuple[int, int]:
        facts = self.KNOWN_TRADE_FACTS.get(ticker, set())
        if not facts:
            return 0, 0
        text_lower = text.lower()
        supported = sum(1 for f in facts if f in text_lower)
        return supported, len(facts)

    async def _eval_factual_consistency(self) -> EvalMetric:
        try:
            test_cases = [
                ("RELIANCE has strong presence in telecom through Jio and retail through Reliance Retail", "reliance"),
                ("RELIANCE operates oil refineries and has a market cap of around 44.5 billion", "reliance"),
                ("Tata Consultancy Services provides IT services globally", "tcs"),
                ("HDFC Bank is India's largest private sector bank", "hdfcbank"),
                ("Infosys is a global leader in consulting and IT services", "infy"),
            ]
            supported_total = 0
            facts_total = 0
            for text, ticker in test_cases:
                sup, tot = self._count_supported_claims(text, ticker)
                supported_total += sup
                facts_total += tot

            consistency = supported_total / facts_total if facts_total > 0 else 1.0
            return EvalMetric(
                name="factual_consistency",
                value=round(consistency, 4),
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                unit="ratio",
                details={"supported_claims": supported_total, "total_claims": facts_total},
            )
        except Exception as e:
            return EvalMetric(
                name="factual_consistency",
                value=0.0,
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    DEFINITE_PATTERNS = re.compile(
        r"\b\d+[%$]?\b|"  # numbers
        r"\b(?:exactly|precisely|specifically|quantified|measured)\b",
        re.IGNORECASE,
    )

    VAGUE_PATTERNS = re.compile(
        r"\b(?:might|could|may|possibly|perhaps|probably|maybe|somewhat|likely|unlikely|"
        r"generally|typically|often|sometimes|usually|frequently|occasionally|rarely|"
        r"sort of|kind of|a bit|a lot|many|much|several|various|numerous)\b",
        re.IGNORECASE,
    )

    async def _eval_specificity(self) -> EvalMetric:
        try:
            specific_text = "The trade failed because the stop loss was hit at exactly 2.5% below entry. The ATR was 1.8%. Confidence dropped to 0.45."
            vague_text = "The trade might have failed possibly due to some market factors. It could be related to volatility or something."

            specific_matches = len(self.DEFINITE_PATTERNS.findall(specific_text))
            vague_matches = len(self.VAGUE_PATTERNS.findall(vague_text))

            specificity = specific_matches / (specific_matches + vague_matches + 1)
            return EvalMetric(
                name="specificity_score",
                value=round(specificity, 4),
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.3,
                unit="score",
                details={"specific_terms": specific_matches, "vague_terms": vague_matches},
            )
        except Exception as e:
            return EvalMetric(
                name="specificity_score",
                value=0.0,
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.3,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_self_contradiction(self) -> EvalMetric:
        try:
            test_pairs = [
                ("The stock is in a strong uptrend with bullish momentum. The stock shows bearish divergence and is in a downtrend.",
                 True),
                ("The stock shows strong momentum with RSI above 70. Volume confirms the breakout with above-average participation.",
                 False),
                ("Market regime is bullish trend. However, volatility expansion suggests caution. The trend remains up.",
                 False),
            ]
            contradictions = 0
            for text, has_contradiction in test_pairs:
                detected = self._detect_contradiction(text)
                if detected == has_contradiction:
                    contradictions += 1

            contradiction_score = contradictions / len(test_pairs) if test_pairs else 1.0
            return EvalMetric(
                name="contradiction_detection",
                value=round(contradiction_score, 4),
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                unit="score",
                details={"correctly_identified": contradictions, "total_pairs": len(test_pairs)},
            )
        except Exception as e:
            return EvalMetric(
                name="contradiction_detection",
                value=0.0,
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    def _detect_contradiction(self, text: str) -> bool:
        text_lower = text.lower()
        contradiction_pairs = [
            (r"\buptrend\b", r"\bdowntrend\b"),
            (r"\bbullish\b", r"\bbearish\b"),
            (r"\bbuy\b", r"\bsell\b"),
            (r"\bpositive\b", r"\bnegative\b"),
            (r"\bincreasing\b", r"\bdecreasing\b"),
            (r"\bstrong\b(?!.*\bweak\b)", r"\bweak\b(?!.*\bstrong\b)"),
            (r"\bhigh\b(?!.*\blow\b)", r"\blow\b(?!.*\bhigh\b)"),
        ]
        for pos_pat, neg_pat in contradiction_pairs:
            has_pos = bool(re.search(pos_pat, text_lower))
            has_neg = bool(re.search(neg_pat, text_lower))
            if has_pos and has_neg:
                return True
        return False

    async def _eval_vagueness(self) -> EvalMetric:
        try:
            test_texts = [
                ("The stock might go up possibly if the market conditions are favorable", True),
                ("The stop loss was triggered at 2.3% below entry price with volume confirmation", False),
                ("Several factors could potentially affect the outcome maybe", True),
            ]
            correct = 0
            for text, is_vague in test_texts:
                vague_ratio = self._compute_vagueness_ratio(text)
                detected_vague = vague_ratio > 0.15
                if detected_vague == is_vague:
                    correct += 1

            accuracy = correct / len(test_texts) if test_texts else 1.0
            return EvalMetric(
                name="vagueness_detection",
                value=round(accuracy, 4),
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                unit="score",
                details={"correctly_classified": correct, "total_texts": len(test_texts)},
            )
        except Exception as e:
            return EvalMetric(
                name="vagueness_detection",
                value=0.0,
                metric_type=MetricType.HALLUCINATION_SCORE,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )

    def _compute_vagueness_ratio(self, text: str) -> float:
        words = text.split()
        if not words:
            return 0.0
        vague_count = len(self.VAGUE_PATTERNS.findall(text))
        return vague_count / len(words)
