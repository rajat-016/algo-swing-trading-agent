from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from loguru import logger

from pydantic import BaseModel, Field


class IntelligenceSummary(BaseModel):
    summary_type: str = Field(description="Type of intelligence summary")
    period: str = Field(description="Analysis period description")
    executive_summary: str = Field(description="2-3 sentence high-level summary")
    key_findings: list[dict] = Field(default_factory=list)
    trends: list[dict] = Field(default_factory=list)
    actionable_insights: list[dict] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    raw_llm_output: Optional[str] = Field(default=None)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IntelligenceSummaryReport(BaseModel):
    summaries: list[IntelligenceSummary] = Field(default_factory=list)
    period_start: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    period_end: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    total_summaries: int = Field(default=0)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class IntelligenceSummaryGenerator:
    def __init__(self, analytics_db=None):
        self._analytics_db = analytics_db
        self._inference_service = None
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running = False

    def _get_analytics_db(self):
        if self._analytics_db is not None:
            return self._analytics_db
        try:
            from core.analytics_db import AnalyticsDB
            self._analytics_db = AnalyticsDB()
            return self._analytics_db
        except Exception:
            return None

    async def _get_inference_service(self):
        if self._inference_service is not None:
            return self._inference_service
        try:
            from ai.inference.service import InferenceService
            self._inference_service = InferenceService()
            await self._inference_service.initialize()
            return self._inference_service
        except Exception as e:
            logger.warning(f"InferenceService not available: {e}")
            return None

    async def generate_periodic_summaries(
        self,
        pattern_report: Any = None,
        degradation_report: Any = None,
        mismatch_report: Any = None,
        instability_report: Any = None,
        recommendation_report: Any = None,
        period_days: int = 30,
    ) -> IntelligenceSummaryReport:
        inference = await self._get_inference_service()
        if inference is None:
            logger.warning("InferenceService unavailable, using template-based summaries")
            return self._generate_template_summaries(
                pattern_report=pattern_report,
                degradation_report=degradation_report,
                mismatch_report=mismatch_report,
                instability_report=instability_report,
                recommendation_report=recommendation_report,
                period_days=period_days,
            )

        period_label = f"last_{period_days}_days"
        now = datetime.now(timezone.utc)
        period_start = (now - timedelta(days=period_days)).isoformat()
        period_end = now.isoformat()

        patterns_text = self._format_pattern_data(pattern_report)
        degradation_text = self._format_degradation_data(degradation_report)
        mismatches_text = self._format_mismatch_data(mismatch_report)
        instability_text = self._format_instability_data(instability_report)
        recommendations_text = self._format_recommendation_data(recommendation_report)

        summary_types = [
            ("strategy_degradation_report", ["strategy_degradation"]),
            ("volatility_failure_report", ["recurring_patterns", "volatility_expansion"]),
            ("regime_instability_summary", ["regime_mismatches", "regime_instability"]),
            ("comprehensive_periodic_summary", ["recurring_patterns", "strategy_degradation", "regime_mismatches", "system_instability", "recommendations"]),
        ]

        summaries = []
        for summary_type, analysis_types in summary_types:
            try:
                result = await inference.render_and_generate(
                    prompt_name="intelligence_summary",
                    config_key="analysis",
                    period=period_label,
                    analysis_types=", ".join(analysis_types),
                    recurring_patterns=patterns_text,
                    strategy_degradation=degradation_text,
                    regime_mismatches=mismatches_text,
                    system_instability=instability_text,
                    investigation_recommendations=recommendations_text,
                )
                parsed = self._parse_llm_output(result, summary_type, period_label)
                summaries.append(parsed)
            except Exception as e:
                logger.error(f"Failed to generate {summary_type} summary: {e}")

        if not summaries:
            logger.warning("All LLM summaries failed, falling back to template-based")
            return self._generate_template_summaries(
                pattern_report=pattern_report,
                degradation_report=degradation_report,
                mismatch_report=mismatch_report,
                instability_report=instability_report,
                recommendation_report=recommendation_report,
                period_days=period_days,
            )

        self._persist_summaries(summaries, period_start, period_end)

        return IntelligenceSummaryReport(
            summaries=summaries,
            period_start=period_start,
            period_end=period_end,
            total_summaries=len(summaries),
        )

    def _parse_llm_output(self, llm_text: str, summary_type: str, period: str) -> IntelligenceSummary:
        try:
            from ai.llm.models import ResponseParser
            data = ResponseParser.extract_json(llm_text)
            if data:
                return IntelligenceSummary(
                    summary_type=data.get("summary_type", summary_type),
                    period=data.get("period", period),
                    executive_summary=data.get("executive_summary", ""),
                    key_findings=data.get("key_findings", []),
                    trends=data.get("trends", []),
                    actionable_insights=data.get("actionable_insights", []),
                    risk_flags=data.get("risk_flags", []),
                    raw_llm_output=llm_text,
                )
        except Exception:
            pass
        return IntelligenceSummary(
            summary_type=summary_type,
            period=period,
            executive_summary="LLM output could not be parsed as structured JSON.",
            raw_llm_output=llm_text,
        )

    def _generate_template_summaries(
        self,
        pattern_report=None,
        degradation_report=None,
        mismatch_report=None,
        instability_report=None,
        recommendation_report=None,
        period_days: int = 30,
    ) -> IntelligenceSummaryReport:
        now = datetime.now(timezone.utc)
        period_start = (now - timedelta(days=period_days)).isoformat()
        period_end = now.isoformat()
        period_label = f"last_{period_days}_days"
        summaries = []

        if degradation_report:
            summaries.append(self._template_degradation_summary(degradation_report, period_label))
        if pattern_report:
            summaries.append(self._template_volatility_summary(pattern_report, period_label))
        if mismatch_report:
            summaries.append(self._template_regime_summary(mismatch_report, period_label))

        self._persist_summaries(summaries, period_start, period_end)

        return IntelligenceSummaryReport(
            summaries=summaries,
            period_start=period_start,
            period_end=period_end,
            total_summaries=len(summaries),
        )

    def _template_degradation_summary(self, report, period: str) -> IntelligenceSummary:
        severity = getattr(report, "severity", "none")
        score = getattr(report, "degradation_score", 0.0)
        signals = getattr(report, "signals", [])
        recent_wr = getattr(report, "recent_win_rate", None)
        baseline_wr = getattr(report, "baseline_win_rate", None)

        findings = []
        if signals:
            for s in signals:
                findings.append({
                    "area": "strategy_degradation",
                    "finding": f"{s.metric}: {s.direction} ({s.change_pct:+.0%})",
                    "severity": severity,
                    "confidence": min(abs(s.change_pct) + 0.3, 0.95),
                })

        return IntelligenceSummary(
            summary_type="strategy_degradation_report",
            period=period,
            executive_summary=f"Strategy degradation severity is '{severity}' with composite score {score:.2f}. "
                             f"{'Investigation recommended.' if severity in ('high', 'critical') else 'No immediate action needed.'}",
            key_findings=findings,
            risk_flags=[f"Strategy degradation: {severity}"] if severity in ("high", "critical") else [],
        )

    def _template_volatility_summary(self, report, period: str) -> IntelligenceSummary:
        patterns = getattr(report, "patterns", [])
        vol_patterns = [p for p in patterns if p.category == "volatility_expansion"]
        total = getattr(report, "total_patterns_found", 0)

        findings = []
        for p in patterns:
            if p.category in ("volatility_expansion", "stop_loss_hunting"):
                findings.append({
                    "area": "volatility_failure",
                    "finding": f"{p.label}: {p.count} occurrences ({p.frequency:.0%} freq), trend {p.trend_direction}",
                    "severity": p.severity,
                    "confidence": min(p.frequency + 0.2, 0.95),
                })

        return IntelligenceSummary(
            summary_type="volatility_failure_report",
            period=period,
            executive_summary=f"Detected {total} pattern categories. "
                             f"{f'{len(vol_patterns)} volatility-related patterns identified.' if vol_patterns else 'No significant volatility patterns.'}",
            key_findings=findings,
            risk_flags=[f"Volatility pattern: {p.label}" for p in patterns if p.severity == "critical"],
        )

    def _template_regime_summary(self, report, period: str) -> IntelligenceSummary:
        mismatches = getattr(report, "mismatches", [])
        elevated = getattr(report, "regimes_with_elevated_risk", [])
        overall = getattr(report, "overall_failure_rate", 0.0)

        findings = []
        for m in mismatches:
            if m.relative_risk > 1.0:
                findings.append({
                    "area": "regime_mismatch",
                    "finding": f"{m.regime}: {m.mismatch_rate:.0%} failure rate vs {m.overall_failure_rate:.0%} overall (risk: {m.relative_risk:.1f}x)",
                    "severity": "high" if m.relative_risk > 1.5 else "medium",
                    "confidence": min(m.relative_risk * 0.3, 0.9),
                })

        return IntelligenceSummary(
            summary_type="regime_instability_summary",
            period=period,
            executive_summary=f"Overall failure rate: {overall:.0%}. "
                             f"{f'Elevated risk in {len(elevated)} regimes: {elevated}' if elevated else 'No regimes with elevated risk.'}",
            key_findings=findings,
            risk_flags=[f"Elevated risk in {r}" for r in elevated],
        )

    def _persist_summaries(self, summaries: list[IntelligenceSummary], period_start: str, period_end: str):
        db = self._get_analytics_db()
        if db is None:
            logger.warning("Cannot persist summaries: AnalyticsDB unavailable")
            return
        try:
            for summary in summaries:
                content = summary.model_dump_json(indent=2)
                db.execute(
                    """INSERT INTO reflection_log (period_start, period_end, reflection_type, content, metrics_snapshot)
                       VALUES (?, ?, ?, ?, ?)""",
                    [
                        period_start[:10],
                        period_end[:10],
                        f"intelligence_summary_{summary.summary_type}",
                        content,
                        json.dumps({"summary_type": summary.summary_type, "findings_count": len(summary.key_findings)}),
                    ],
                )
        except Exception as e:
            logger.warning(f"Failed to persist intelligence summaries: {e}")

    def _format_pattern_data(self, report) -> str:
        if report is None:
            return "No pattern data available"
        try:
            d = report if isinstance(report, dict) else report.model_dump()
            if isinstance(d, dict):
                return json.dumps({k: d.get(k) for k in ("patterns", "total_patterns_found", "dominant_category", "critical_patterns") if k in d}, indent=2)
        except Exception:
            pass
        return str(report)[:2000]

    def _format_degradation_data(self, report) -> str:
        if report is None:
            return "No degradation data available"
        try:
            d = report if isinstance(report, dict) else report.model_dump()
            if isinstance(d, dict):
                return json.dumps({k: d.get(k) for k in ("degradation_score", "severity", "signals", "investigation_needed") if k in d}, indent=2)
        except Exception:
            pass
        return str(report)[:2000]

    def _format_mismatch_data(self, report) -> str:
        if report is None:
            return "No mismatch data available"
        try:
            d = report if isinstance(report, dict) else report.model_dump()
            if isinstance(d, dict):
                return json.dumps({k: d.get(k) for k in ("mismatches", "regimes_with_elevated_risk", "overall_failure_rate") if k in d}, indent=2)
        except Exception:
            pass
        return str(report)[:2000]

    def _format_instability_data(self, report) -> str:
        if report is None:
            return "No instability data available"
        try:
            d = report if isinstance(report, dict) else report.model_dump()
            if isinstance(d, dict):
                return json.dumps({k: d.get(k) for k in ("composite_score", "severity", "factors", "alert_count") if k in d}, indent=2)
        except Exception:
            pass
        return str(report)[:2000]

    def _format_recommendation_data(self, report) -> str:
        if report is None:
            return "No recommendation data available"
        try:
            d = report if isinstance(report, dict) else report.model_dump()
            if isinstance(d, dict):
                return json.dumps({k: d.get(k) for k in ("recommendations", "immediate_actions", "critical_areas") if k in d}, indent=2)
        except Exception:
            pass
        return str(report)[:2000]

    async def start_auto_generation(self, interval_hours: int = 24):
        if self._running:
            logger.warning("Auto-generation already running")
            return
        self._running = True
        self._scheduler_task = asyncio.create_task(self._auto_generate_loop(interval_hours))
        logger.info(f"Started auto intelligence summary generation every {interval_hours}h")

    async def stop_auto_generation(self):
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            self._scheduler_task = None
        logger.info("Stopped auto intelligence summary generation")

    async def _auto_generate_loop(self, interval_hours: int):
        while self._running:
            try:
                await self.generate_periodic_summaries(period_days=30)
                logger.debug("Auto-generated periodic intelligence summaries")
            except Exception as e:
                logger.error(f"Auto-generation failed: {e}")
            await asyncio.sleep(interval_hours * 3600)
