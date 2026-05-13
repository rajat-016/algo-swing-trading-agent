from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from intelligence.reflection_engine.post_trade_reflector import PostTradeReflector, PostTradeReflection
from intelligence.reflection_engine.batch_reflector import BatchReflector
from intelligence.reflection_engine.recurring_pattern_detector import (
    RecurringPatternDetector,
    RecurringPatternReport,
)
from intelligence.reflection_engine.strategy_degradation import (
    StrategyDegradationAnalyzer,
    StrategyDegradationReport,
)
from intelligence.reflection_engine.regime_mismatch import (
    RegimeMismatchDetector,
    RegimeMismatchReport,
)
from intelligence.reflection_engine.instability_reporter import (
    InstabilityReporter,
    InstabilityReport,
)
from intelligence.reflection_engine.investigation_recommender import (
    InvestigationRecommender,
    InvestigationReport,
)


class ReflectionService:
    def __init__(self):
        self._post_trade_reflector: Optional[PostTradeReflector] = None
        self._batch_reflector: Optional[BatchReflector] = None
        self._pattern_detector: Optional[RecurringPatternDetector] = None
        self._degradation_analyzer: Optional[StrategyDegradationAnalyzer] = None
        self._mismatch_detector: Optional[RegimeMismatchDetector] = None
        self._instability_reporter: Optional[InstabilityReporter] = None
        self._investigation_recommender: Optional[InvestigationRecommender] = None
        self._settings = None

    @property
    def enabled(self) -> bool:
        if self._settings is None:
            try:
                from core.config import get_settings
                self._settings = get_settings()
            except Exception:
                return False
        return getattr(self._settings, "reflection_engine_enabled", False)

    async def get_post_trade_reflector(self) -> Optional[PostTradeReflector]:
        if self._post_trade_reflector is None:
            self._post_trade_reflector = PostTradeReflector()
        return self._post_trade_reflector

    async def get_batch_reflector(self) -> Optional[BatchReflector]:
        if self._batch_reflector is None:
            self._batch_reflector = BatchReflector()
        return self._batch_reflector

    async def get_pattern_detector(self) -> RecurringPatternDetector:
        if self._pattern_detector is None:
            self._pattern_detector = RecurringPatternDetector()
            self._apply_pattern_config(self._pattern_detector)
        return self._pattern_detector

    async def get_degradation_analyzer(self) -> StrategyDegradationAnalyzer:
        if self._degradation_analyzer is None:
            self._degradation_analyzer = StrategyDegradationAnalyzer()
            self._apply_degradation_config(self._degradation_analyzer)
        return self._degradation_analyzer

    async def get_mismatch_detector(self) -> RegimeMismatchDetector:
        if self._mismatch_detector is None:
            self._mismatch_detector = RegimeMismatchDetector()
        return self._mismatch_detector

    async def get_instability_reporter(self) -> InstabilityReporter:
        if self._instability_reporter is None:
            self._instability_reporter = InstabilityReporter()
        return self._instability_reporter

    async def get_investigation_recommender(self) -> InvestigationRecommender:
        if self._investigation_recommender is None:
            self._investigation_recommender = InvestigationRecommender()
        return self._investigation_recommender

    def _apply_pattern_config(self, detector: RecurringPatternDetector):
        try:
            if self._settings:
                detector.configure(
                    min_trades=getattr(self._settings, "reflection_min_trades_for_pattern", 5),
                    frequency_threshold=getattr(self._settings, "reflection_pattern_frequency_threshold", 0.15),
                )
        except Exception:
            pass

    def _apply_degradation_config(self, analyzer: StrategyDegradationAnalyzer):
        try:
            if self._settings:
                analyzer.configure(
                    baseline_days=getattr(self._settings, "reflection_degradation_baseline_days", 60),
                    recent_days=getattr(self._settings, "reflection_recurring_window_days", 30),
                    min_trades=getattr(self._settings, "reflection_min_trades_for_pattern", 5),
                )
        except Exception:
            pass

    async def reflect_trade(self, trade_data: dict) -> Optional[PostTradeReflection]:
        if not self.enabled:
            return None
        reflector = await self.get_post_trade_reflector()
        if reflector is None:
            return None
        reflection = await reflector.reflect(trade_data)
        if reflection:
            self._store_to_reflection_log(reflection)
        return reflection

    async def batch_reflect(
        self,
        trades: list[dict],
        period_label: str = "recent",
    ) -> Optional[dict[str, Any]]:
        if not self.enabled:
            return None
        reflector = await self.get_batch_reflector()
        if reflector is None:
            return None
        result = await reflector.reflect_on_recent_trades(trades, period_label)
        if result and result.get("content"):
            self._store_batch_reflection_log(result)
        return result

    async def detect_recurring_patterns(
        self,
        trades: Optional[list[dict]] = None,
        window_days: int = 30,
    ) -> RecurringPatternReport:
        detector = await self.get_pattern_detector()
        report = detector.detect(trades=trades, window_days=window_days)
        self._store_reflection_result("recurring_patterns", report.model_dump())
        return report

    async def analyze_degradation(
        self,
        trades: Optional[list[dict]] = None,
    ) -> StrategyDegradationReport:
        analyzer = await self.get_degradation_analyzer()
        report = analyzer.analyze(trades=trades)
        self._store_reflection_result("strategy_degradation", report.model_dump())
        return report

    async def detect_regime_mismatches(
        self,
        trades: Optional[list[dict]] = None,
    ) -> RegimeMismatchReport:
        detector = await self.get_mismatch_detector()
        report = detector.analyze(trades=trades)
        self._store_reflection_result("regime_mismatch", report.model_dump())
        return report

    async def generate_instability_report(
        self,
        trades: Optional[list[dict]] = None,
    ) -> InstabilityReport:
        reporter = await self.get_instability_reporter()
        report = reporter.generate_report(trades=trades)
        self._store_reflection_result("instability", report.model_dump())
        return report

    async def generate_investigation_recommendations(
        self,
        pattern_report: Optional[RecurringPatternReport] = None,
        degradation_report: Optional[StrategyDegradationReport] = None,
        mismatch_report: Optional[RegimeMismatchReport] = None,
        instability_report: Optional[InstabilityReport] = None,
    ) -> InvestigationReport:
        if pattern_report is None:
            pattern_report = await self.detect_recurring_patterns()
        if degradation_report is None:
            degradation_report = await self.analyze_degradation()
        if mismatch_report is None:
            mismatch_report = await self.detect_regime_mismatches()
        if instability_report is None:
            instability_report = await self.generate_instability_report()

        recommender = await self.get_investigation_recommender()
        report = recommender.generate(
            pattern_report=pattern_report,
            degradation_report=degradation_report,
            mismatch_report=mismatch_report,
            instability_report=instability_report,
        )
        self._store_reflection_result("investigation_recommendations", report.model_dump())
        return report

    async def generate_system_reflection(self) -> dict[str, Any]:
        pattern_report = await self.detect_recurring_patterns()
        degradation_report = await self.analyze_degradation()
        mismatch_report = await self.detect_regime_mismatches()
        instability_report = await self.generate_instability_report()
        recommendations = await self.generate_investigation_recommendations(
            pattern_report=pattern_report,
            degradation_report=degradation_report,
            mismatch_report=mismatch_report,
            instability_report=instability_report,
        )
        return {
            "status": "ok",
            "recurring_patterns": pattern_report.model_dump(),
            "strategy_degradation": degradation_report.model_dump(),
            "regime_mismatches": mismatch_report.model_dump(),
            "instability": instability_report.model_dump(),
            "investigation_recommendations": recommendations.model_dump(),
            "generated_at": __import__("datetime").datetime.now(
                __import__("datetime", fromlist=["timezone"]).timezone.utc
            ).isoformat(),
        }

    def _get_db(self):
        from core.analytics_db import AnalyticsDB
        return AnalyticsDB()

    def _store_to_reflection_log(self, reflection: PostTradeReflection):
        try:
            db = self._get_db()
            db.execute(
                """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                [
                    None,
                    None,
                    reflection.reflection_type,
                    reflection.model_dump_json(indent=2),
                    None,
                ],
            )
        except Exception as e:
            logger.debug(f"Failed to store reflection to log: {e}")

    def _store_batch_reflection_log(self, result: dict):
        try:
            content = result.get("content", "")
            metrics = result.get("metrics", {})
            period = result.get("period", "recent")
            now = (
                __import__("datetime", fromlist=["datetime"])
                .datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                .isoformat()[:10]
            )

            db = self._get_db()
            db.execute(
                """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                [now, now, f"batch_{period}", content, str(metrics)],
            )
        except Exception as e:
            logger.debug(f"Failed to store batch reflection log: {e}")

    def _store_reflection_result(self, reflection_type: str, data: dict):
        try:
            import json
            db = self._get_db()
            now = (
                __import__("datetime", fromlist=["datetime"])
                .datetime.now(__import__("datetime", fromlist=["timezone"]).timezone.utc)
                .isoformat()[:10]
            )
            db.execute(
                """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                   VALUES (?, ?, ?, ?, ?)""",
                [now, now, f"system_{reflection_type}", json.dumps(data, indent=2), None],
            )
        except Exception as e:
            logger.debug(f"Failed to store {reflection_type} reflection: {e}")

    async def get_reflection_logs(self, limit: int = 50) -> list[dict]:
        try:
            db = self._get_db()
            rows = db.fetch_all(
                "SELECT * FROM reflection_log ORDER BY created_at DESC LIMIT ?",
                [limit],
            )
            columns = ["id", "period_start", "period_end", "reflection_type", "content", "metrics_snapshot", "created_at"]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.debug(f"Failed to get reflection logs: {e}")
        return []
