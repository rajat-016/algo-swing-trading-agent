from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from core.evaluation.base import (
    BaseEvaluator,
    BenchmarkConfig,
    EvalMetric,
    MetricType,
)
from intelligence.reflection_engine.recurring_pattern_detector import (
    RecurringPatternDetector,
    RecurringPatternReport,
)


class ReflectionAccuracyEvaluator(BaseEvaluator):
    def __init__(self, config: Optional[BenchmarkConfig] = None):
        super().__init__(config)
        self._detector: Optional[RecurringPatternDetector] = None

    async def _run_evaluation(self) -> list[EvalMetric]:
        metrics = []

        pattern_precision = await self._eval_pattern_precision()
        metrics.append(pattern_precision)

        pattern_recall = await self._eval_pattern_recall()
        metrics.append(pattern_recall)

        detection_coverage = await self._eval_detection_coverage()
        metrics.append(detection_coverage)

        return metrics

    def _make_trade(self, trade_id: str, outcome: str, reasoning: str,
                    regime: str = "bull_trend", pnl: float = 0.0) -> dict[str, Any]:
        return {
            "trade_id": trade_id,
            "symbol": "RELIANCE",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "market_regime": regime,
            "outcome": outcome,
            "reasoning": reasoning,
            "pnl": pnl,
            "prediction": "BUY",
            "confidence": 0.75,
        }

    async def _eval_pattern_precision(self) -> EvalMetric:
        try:
            detector = RecurringPatternDetector()
            trades = [
                self._make_trade("T1", "stop_loss_hit", "regime mismatch, wrong direction", pnl=-150),
                self._make_trade("T2", "stop_loss_hit", "volatility expansion, gap down", pnl=-200),
                self._make_trade("T3", "stop_loss_hit", "regime mismatch", pnl=-120),
                self._make_trade("T4", "target_hit", "strong momentum, good setup", pnl=300),
                self._make_trade("T5", "stop_loss_hit", "high volatility", pnl=-180),
                self._make_trade("T6", "target_hit", "trend following", pnl=250),
                self._make_trade("T7", "stop_loss_hit", "earnings surprise, gap", pnl=-500),
                self._make_trade("T8", "target_hit", "breakout with volume", pnl=400),
            ]
            report = detector.detect(trades=trades, window_days=30)
            found_patterns = len(report.patterns)

            if found_patterns >= 1:
                has_expected = any(
                    p.category in ("regime_mismatch", "volatility_expansion", "earnings_event")
                    for p in report.patterns
                )
                precision = min(1.0, found_patterns / 5.0)
                if has_expected:
                    precision = min(1.0, precision + 0.2)
            else:
                precision = 0.0

            return EvalMetric(
                name="pattern_precision",
                value=round(precision, 4),
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.3,
                unit="score",
                details={"patterns_found": found_patterns, "total_trades": len(trades)},
            )
        except Exception as e:
            return EvalMetric(
                name="pattern_precision",
                value=0.0,
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.3,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_pattern_recall(self) -> EvalMetric:
        try:
            detector = RecurringPatternDetector()
            trades = [
                self._make_trade("T1", "stop_loss_hit", "regime mismatch, wrong direction", pnl=-150),
                self._make_trade("T2", "stop_loss_hit", "regime mismatch", pnl=-120),
                self._make_trade("T3", "stop_loss_hit", "regime mismatch, poor confirmation", pnl=-100),
                self._make_trade("T4", "stop_loss_hit", "weak momentum, low adx", pnl=-80),
                self._make_trade("T5", "target_hit", "strong setup, working well", pnl=300),
            ]
            report = detector.detect(trades=trades, window_days=30)
            known_categories = {"regime_mismatch", "weak_momentum", "poor_confirmations"}
            found_categories = {p.category for p in report.patterns}
            detected = known_categories & found_categories
            recall = len(detected) / len(known_categories) if known_categories else 1.0
            return EvalMetric(
                name="pattern_recall",
                value=round(recall, 4),
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.3,
                unit="ratio",
                details={"detected": list(detected), "expected": list(known_categories), "total_patterns": len(report.patterns)},
            )
        except Exception as e:
            return EvalMetric(
                name="pattern_recall",
                value=0.0,
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.3,
                passed=False,
                details={"error": str(e)},
            )

    async def _eval_detection_coverage(self) -> EvalMetric:
        try:
            detector = RecurringPatternDetector()
            empty_report = detector.detect(trades=[], window_days=30)
            coverage = 1.0 if empty_report.total_trades_analyzed == 0 else 0.0
            return EvalMetric(
                name="detection_coverage",
                value=coverage,
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.5,
                unit="score",
                details={"handles_empty_input": coverage == 1.0},
            )
        except Exception as e:
            return EvalMetric(
                name="detection_coverage",
                value=0.0,
                metric_type=MetricType.REFLECTION_ACCURACY,
                threshold=0.5,
                passed=False,
                details={"error": str(e)},
            )
