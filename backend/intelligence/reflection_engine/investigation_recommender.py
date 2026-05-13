from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field
from loguru import logger


class InvestigationRecommendation(BaseModel):
    priority: int = Field(description="Priority ranking (1=highest)")
    area: str = Field(description="Area requiring investigation")
    title: str = Field(description="Short recommendation title")
    description: str = Field(description="Detailed recommendation")
    rationale: str = Field(description="Why this is important")
    suggested_action: str = Field(description="Suggested next action")
    source_signals: list[str] = Field(default_factory=list, description="Source signals that triggered this")
    urgency: str = Field(description="immediate/short_term/medium_term/long_term")


class InvestigationReport(BaseModel):
    recommendations: list[InvestigationRecommendation] = Field(default_factory=list)
    total_recommendations: int = Field(default=0)
    immediate_actions: int = Field(default=0)
    critical_areas: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class InvestigationRecommender:
    def __init__(self):
        pass

    def generate(
        self,
        pattern_report: Any = None,
        degradation_report: Any = None,
        mismatch_report: Any = None,
        instability_report: Any = None,
    ) -> InvestigationReport:
        recommendations: list[InvestigationRecommendation] = []

        if pattern_report:
            recommendations.extend(self._recommend_from_patterns(pattern_report))

        if degradation_report:
            recommendations.extend(self._recommend_from_degradation(degradation_report))

        if mismatch_report:
            recommendations.extend(self._recommend_from_mismatches(mismatch_report))

        if instability_report:
            recommendations.extend(self._recommend_from_instability(instability_report))

        if not recommendations:
            recommendations.append(InvestigationRecommendation(
                priority=1,
                area="system_health",
                title="No issues detected",
                description="No significant issues found across all reflection analyses",
                rationale="Routine check shows normal system operation",
                suggested_action="Continue monitoring; no action required",
                source_signals=["routine_check"],
                urgency="long_term",
            ))

        recommendations.sort(key=lambda r: r.priority)
        for i, rec in enumerate(recommendations, 1):
            rec.priority = i

        immediate = sum(1 for r in recommendations if r.urgency == "immediate")
        critical_areas = list(set(
            r.area for r in recommendations if r.urgency in ("immediate", "short_term")
        ))

        return InvestigationReport(
            recommendations=recommendations,
            total_recommendations=len(recommendations),
            immediate_actions=immediate,
            critical_areas=critical_areas,
        )

    def _recommend_from_patterns(self, report) -> list[InvestigationRecommendation]:
        recs = []
        for p in getattr(report, "critical_patterns", []):
            recs.append(InvestigationRecommendation(
                priority=1,
                area="recurring_pattern",
                title=f"Critical pattern: {p.label}",
                description=p.description,
                rationale=f"Detected {p.count} occurrences ({p.frequency:.0%} frequency) with {p.severity} severity. Trend is {p.trend_direction}.",
                suggested_action=f"Investigate {p.category} patterns. Review stop-loss placement, regime filters, or entry criteria for this pattern type.",
                source_signals=[f"pattern_{p.category}", f"frequency_{p.frequency}", f"trend_{p.trend_direction}"],
                urgency="immediate" if p.severity in ("critical", "high") else "short_term",
            ))
        return recs

    def _recommend_from_degradation(self, report) -> list[InvestigationRecommendation]:
        recs = []
        if getattr(report, "investigation_needed", False):
            signals_summary = "; ".join(
                f"{s.metric}: {s.direction} ({s.change_pct:+.0%})"
                for s in getattr(report, "signals", [])
            )
            recs.append(InvestigationRecommendation(
                priority=2,
                area="strategy_degradation",
                title=f"Strategy degradation detected ({report.severity})",
                description=f"Composite degradation score: {report.degradation_score:.2f}",
                rationale=f"Recent trades ({report.recent_trades_count}) show declining performance vs baseline ({report.baseline_trades_count}). Signals: {signals_summary}",
                suggested_action="Review recent trade log for regime changes, slippage issues, or model drift. Consider retraining model or adjusting position sizing.",
                source_signals=[f"degradation_score_{report.degradation_score}", f"severity_{report.severity}"] + [s.metric for s in getattr(report, "signals", [])],
                urgency="immediate" if report.severity in ("critical", "high") else "short_term",
            ))
        return recs

    def _recommend_from_mismatches(self, report) -> list[InvestigationRecommendation]:
        recs = []
        for regime in getattr(report, "regimes_with_elevated_risk", []):
            entries = [m for m in getattr(report, "mismatches", []) if m.regime == regime]
            if entries:
                e = entries[0]
                recs.append(InvestigationRecommendation(
                    priority=3,
                    area="regime_mismatch",
                    title=f"Elevated risk in {regime} regime",
                    description=f"Failure rate: {e.mismatch_rate:.0%} vs overall {e.overall_failure_rate:.0%} (relative risk: {e.relative_risk:.1f}x)",
                    rationale=f"Trades in {regime} regime fail {e.relative_risk:.1f}x more often than average. {e.total_trades} trades analyzed.",
                    suggested_action=e.recommendation or f"Review filter criteria for {regime} regime trades. Consider adding regime-based confidence modifiers.",
                    source_signals=[f"regime_{regime}", f"relative_risk_{e.relative_risk}"],
                    urgency="short_term" if e.relative_risk > 2.0 else "medium_term",
                ))
        return recs

    def _recommend_from_instability(self, report) -> list[InvestigationRecommendation]:
        recs = []
        if getattr(report, "severity", "stable") in ("high", "critical"):
            alert_descriptions = "; ".join(f.description for f in getattr(report, "critical_factors", []))
            recs.append(InvestigationRecommendation(
                priority=4,
                area="system_instability",
                title=f"System instability: {report.severity}",
                description=f"Composite instability score: {report.composite_score:.2f}",
                rationale=f"Multiple instability signals detected: {alert_descriptions}",
                suggested_action="Comprehensive review needed. Check regime stability, portfolio concentration, recent failure rates, and feature drift.",
                source_signals=[f"instability_score_{report.composite_score}", f"instability_severity_{report.severity}"] + [f.factor for f in getattr(report, "critical_factors", [])],
                urgency="immediate" if report.severity == "critical" else "short_term",
            ))
        return recs
