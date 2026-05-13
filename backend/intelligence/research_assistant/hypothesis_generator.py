from datetime import datetime, timezone
from typing import Any, Optional
from pydantic import BaseModel, Field
from loguru import logger


class Hypothesis(BaseModel):
    title: str
    description: str
    supporting_evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    test_suggestion: Optional[str] = None
    expected_outcome: Optional[str] = None
    category: str = "general"


class HypothesisReport(BaseModel):
    hypotheses: list[Hypothesis] = Field(default_factory=list)
    total_hypotheses: int = 0
    high_confidence_count: int = 0
    categories: list[str] = Field(default_factory=list)
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    summary: str = ""


class HypothesisGenerator:
    def __init__(self, inference_service=None):
        self._inference = inference_service

    async def generate_hypotheses(
        self,
        context: Optional[dict] = None,
        drift_report: Optional[dict] = None,
        degradation_report: Optional[dict] = None,
        regime_report: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
        use_llm: bool = True,
    ) -> HypothesisReport:
        template_hypotheses = self._generate_template_hypotheses(
            drift_report, degradation_report, regime_report, comparison_result,
        )

        if use_llm and self._inference is not None:
            try:
                llm_hypotheses = await self._generate_llm_hypotheses(
                    drift_report, degradation_report, regime_report, comparison_result,
                )
                all_hypotheses = template_hypotheses + llm_hypotheses
            except Exception as e:
                logger.warning(f"LLM hypothesis generation failed: {e}")
                all_hypotheses = template_hypotheses
        else:
            all_hypotheses = template_hypotheses

        seen_titles = set()
        unique_hypotheses = []
        for h in all_hypotheses:
            if h.title.lower() not in seen_titles:
                seen_titles.add(h.title.lower())
                unique_hypotheses.append(h)

        high_conf = sum(1 for h in unique_hypotheses if h.confidence >= 0.7)
        categories = list(set(h.category for h in unique_hypotheses))
        summary = f"Generated {len(unique_hypotheses)} hypotheses ({high_conf} high confidence) in {len(categories)} categories"

        return HypothesisReport(
            hypotheses=unique_hypotheses,
            total_hypotheses=len(unique_hypotheses),
            high_confidence_count=high_conf,
            categories=categories,
            summary=summary,
        )

    def _generate_template_hypotheses(
        self,
        drift_report: Optional[dict] = None,
        degradation_report: Optional[dict] = None,
        regime_report: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
    ) -> list[Hypothesis]:
        hypotheses = []

        if drift_report:
            drifted = drift_report.get("drifted_features", [])
            if drifted:
                top_drifted = drifted[0]["feature_name"] if drifted else "unknown"
                hypotheses.append(Hypothesis(
                    title=f"Feature drift in {top_drifted} degrades model performance",
                    description=f"Feature '{top_drifted}' shows distribution drift (PSI={drifted[0].get('psi', 0):.3f}). "
                                "This may cause the model to make less accurate predictions in current regime.",
                    supporting_evidence=[
                        f"PSI={drifted[0].get('psi', 0):.3f} exceeded DRIFT threshold",
                        f"{len(drifted)} features showing drift in total",
                        f"Most unstable group: {drift_report.get('most_unstable_group')}",
                    ],
                    confidence=0.7 if len(drifted) > 2 else 0.5,
                    test_suggestion="Retrain model excluding drifted features and compare performance",
                    expected_outcome="Model without drifted features should show improved stability",
                    category="feature_drift",
                ))

        if degradation_report:
            score = degradation_report.get("degradation_score", 0)
            if score > 0.3:
                hypotheses.append(Hypothesis(
                    title="Strategy degradation is regime-dependent",
                    description=f"Strategy degradation score ({score:.2f}) exceeds threshold. "
                                "Performance may be declining due to regime shift rather than strategy flaw.",
                    supporting_evidence=[
                        f"Degradation score: {score:.2f}",
                        f"Severity: {degradation_report.get('severity', 'unknown')}",
                    ],
                    confidence=0.65 if score > 0.5 else 0.45,
                    test_suggestion="Split backtest by regime and compare strategy performance per regime",
                    expected_outcome="Strategy performance should be non-uniform across regimes",
                    category="degradation",
                ))

        if regime_report:
            regime_name = regime_report.get("regime", "unknown")
            hypotheses.append(Hypothesis(
                title=f"Current regime ({regime_name}) favors specific feature groups",
                description=f"The market is in {regime_name} regime. Certain feature groups "
                            "may be more predictive in this environment than others.",
                supporting_evidence=[
                    f"Current regime: {regime_name}",
                    f"Confidence: {regime_report.get('confidence', 0):.2f}",
                ],
                confidence=0.6,
                test_suggestion="Compute feature importance stratified by regime",
                expected_outcome="Feature importance ranks differ across regimes",
                category="regime",
            ))

        if comparison_result:
            best = comparison_result.get("best_strategy")
            worst = comparison_result.get("worst_strategy")
            if best and worst:
                hypotheses.append(Hypothesis(
                    title=f"Strategy '{best}' outperforms '{worst}' due to feature alignment",
                    description=f"'{best}' strategy shows better metrics than '{worst}'. "
                                "The gap may be explained by feature-regime alignment.",
                    supporting_evidence=[
                        f"Best: {best}",
                        f"Worst: {worst}",
                        f"Rank by: {comparison_result.get('rank_by', 'win_rate')}",
                    ],
                    confidence=0.55,
                    test_suggestion="Analyze feature distributions for each strategy's trades",
                    expected_outcome="Best strategy's features are better aligned with prevailing regime",
                    category="strategy_comparison",
                ))

        if not hypotheses:
            hypotheses.append(Hypothesis(
                title="Insufficient data for hypothesis generation",
                description="Not enough data available to generate meaningful hypotheses.",
                supporting_evidence=[],
                confidence=0.0,
                test_suggestion="Collect more trade data and retry",
                expected_outcome="N/A",
                category="insufficient_data",
            ))

        return hypotheses

    async def _generate_llm_hypotheses(
        self,
        drift_report: Optional[dict] = None,
        degradation_report: Optional[dict] = None,
        regime_report: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
    ) -> list[Hypothesis]:
        if self._inference is None:
            return []

        context_parts = []
        if drift_report:
            context_parts.append(f"Feature Drift: {drift_report.get('summary', '')}")
        if degradation_report:
            context_parts.append(f"Degradation: score={degradation_report.get('degradation_score')}, severity={degradation_report.get('severity')}")
        if regime_report:
            context_parts.append(f"Regime: {regime_report.get('regime')} (confidence={regime_report.get('confidence')})")
        if comparison_result:
            context_parts.append(f"Strategy Comparison: best={comparison_result.get('best_strategy')}, worst={comparison_result.get('worst_strategy')}")

        context_str = "\n".join(context_parts) if context_parts else "No specific context data available."

        prompt = (
            "You are a quant research analyst. Based on the following market and strategy context, "
            "generate 2-3 testable research hypotheses. Each hypothesis should include: title, "
            "description, supporting evidence, confidence (0-1), test suggestion, and expected outcome.\n\n"
            f"Context:\n{context_str}\n\n"
            "Return ONLY a JSON array of hypothesis objects with fields: title, description, "
            "supporting_evidence (list of strings), confidence (float 0-1), test_suggestion, "
            "expected_outcome, category."
        )

        llm_response = await self._inference.generate(prompt, config_key="analysis")
        parsed = self._try_parse_llm_response(llm_response)
        return parsed

    def _try_parse_llm_response(self, response: str) -> list[Hypothesis]:
        import json as _json
        try:
            data = _json.loads(response)
            if isinstance(data, list):
                return [Hypothesis(**item) for item in data]
            if isinstance(data, dict) and "hypotheses" in data:
                return [Hypothesis(**item) for item in data["hypotheses"]]
        except Exception:
            import re
            match = re.search(r'\[.*?\]', response, re.DOTALL)
            if match:
                try:
                    data = _json.loads(match.group())
                    if isinstance(data, list):
                        return [Hypothesis(**item) for item in data]
                except Exception:
                    pass
        return []
