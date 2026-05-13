import time
from typing import Optional, Any
from dataclasses import dataclass, field

from ai.orchestration.standardizer import (
    StandardIntelligenceOutput, OutputStandardizer,
    StandardTradeExplanation, StandardPortfolioAnalysis,
    StandardRegimeAnalysis, StandardResearchFinding, StandardReflectionReport,
)


@dataclass
class PipelineStep:
    name: str
    module: str
    latency_ms: float = 0.0
    error: Optional[str] = None
    output: Any = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "module": self.module,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "success": self.error is None,
        }


@dataclass
class PipelineResult:
    pipeline_name: str
    steps: list[PipelineStep] = field(default_factory=list)
    final_output: Any = None
    total_latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "pipeline": self.pipeline_name,
            "success": self.success,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "steps": [s.to_dict() for s in self.steps],
            "error": self.error,
            "has_output": self.final_output is not None,
        }


class IntelligencePipeline:
    def __init__(self, context=None, retrieval=None,
                 regime_service=None, portfolio_service=None,
                 trade_explainer=None, journal_service=None,
                 retriever=None, drift_service=None,
                 reflection_service=None, research_assistant=None,
                 inference=None):
        self._context = context
        self._retrieval = retrieval
        self._regime = regime_service
        self._portfolio = portfolio_service
        self._explainer = trade_explainer
        self._journal = journal_service
        self._retriever = retriever
        self._drift = drift_service
        self._reflection = reflection_service
        self._research = research_assistant
        self._inference = inference

    async def trade_explanation_pipeline(self, symbol: str) -> PipelineResult:
        result = PipelineResult(pipeline_name="trade_explanation")
        pipeline_start = time.monotonic()

        step1 = PipelineStep(name="regime_context", module="market_regime")
        try:
            step1.output = await self._regime.get_current_regime() if self._regime else {}
            step1.latency_ms = 0
        except Exception as e:
            step1.error = str(e)
        result.steps.append(step1)

        step2 = PipelineStep(name="trade_explain", module="trade_analysis")
        try:
            s2_start = time.monotonic()
            explanation = await self._explainer.explain_trade(symbol=symbol) if self._explainer else {}
            step2.latency_ms = (time.monotonic() - s2_start) * 1000
            step2.output = explanation
        except Exception as e:
            step2.error = str(e)
        result.steps.append(step2)

        step3 = PipelineStep(name="similar_trades", module="semantic_memory")
        try:
            s3_start = time.monotonic()
            similar = await self._retriever.search(query=symbol, limit=5) if self._retriever else []
            step3.latency_ms = (time.monotonic() - s3_start) * 1000
            step3.output = similar
        except Exception as e:
            step3.error = str(e)
        result.steps.append(step3)

        step4 = PipelineStep(name="journal_context", module="trade_journal")
        try:
            s4_start = time.monotonic()
            journal = await self._journal.get_recent_trades(limit=5) if self._journal else []
            step4.latency_ms = (time.monotonic() - s4_start) * 1000
            step4.output = journal
        except Exception as e:
            step4.error = str(e)
        result.steps.append(step4)

        if self._inference and not any(s.error for s in result.steps):
            step5 = PipelineStep(name="llm_explanation", module="ai_inference")
            try:
                s5_start = time.monotonic()
                regime_str = _safe_str(step1.output)
                explain_str = _safe_str(step2.output)
                similar_str = _safe_str(step3.output)
                prompt = (
                    f"Explain the trade for {symbol}.\n\n"
                    f"Regime Context: {regime_str[:500]}\n"
                    f"Trade Explanation Data: {explain_str[:500]}\n"
                    f"Similar Trades: {similar_str[:500]}\n"
                    f"Journal Context: {_safe_str(step4.output)[:500]}\n\n"
                    f"Provide: 1) Key factors driving this trade 2) Regime alignment "
                    f"3) Confidence assessment 4) Risk considerations."
                )
                step5.output = await self._inference.generate(prompt, config_key="analysis")
                step5.latency_ms = (time.monotonic() - s5_start) * 1000
            except Exception as e:
                step5.error = str(e)
            result.steps.append(step5)

        result.total_latency_ms = (time.monotonic() - pipeline_start) * 1000
        result.success = all(s.error is None for s in result.steps)
        result.final_output = _build_final_output(result)
        return result

    async def portfolio_risk_pipeline(self) -> PipelineResult:
        result = PipelineResult(pipeline_name="portfolio_risk")
        pipeline_start = time.monotonic()

        step1 = PipelineStep(name="portfolio_analysis", module="portfolio_analysis")
        try:
            s1_start = time.monotonic()
            step1.output = await self._portfolio.analyze() if self._portfolio else {}
            step1.latency_ms = (time.monotonic() - s1_start) * 1000
        except Exception as e:
            step1.error = str(e)
        result.steps.append(step1)

        step2 = PipelineStep(name="regime_context", module="market_regime")
        try:
            s2_start = time.monotonic()
            step2.output = await self._regime.get_current_regime() if self._regime else {}
            step2.latency_ms = (time.monotonic() - s2_start) * 1000
        except Exception as e:
            step2.error = str(e)
        result.steps.append(step2)

        if self._inference and not any(s.error for s in result.steps):
            step3 = PipelineStep(name="llm_risk_analysis", module="ai_inference")
            try:
                s3_start = time.monotonic()
                portfolio_str = _safe_str(step1.output)
                regime_str = _safe_str(step2.output)
                prompt = (
                    f"Analyze portfolio risk.\n\n"
                    f"Portfolio Data: {portfolio_str[:1000]}\n"
                    f"Regime Context: {regime_str[:500]}\n\n"
                    f"Identify: 1) Biggest risks 2) Overexposure issues "
                    f"3) Correlated positions 4) Recommendations."
                )
                step3.output = await self._inference.generate(prompt, config_key="analysis")
                step3.latency_ms = (time.monotonic() - s3_start) * 1000
            except Exception as e:
                step3.error = str(e)
            result.steps.append(step3)

        result.total_latency_ms = (time.monotonic() - pipeline_start) * 1000
        result.success = all(s.error is None for s in result.steps)
        result.final_output = _build_final_output(result)
        return result

    async def market_analysis_pipeline(self) -> PipelineResult:
        result = PipelineResult(pipeline_name="market_analysis")
        pipeline_start = time.monotonic()

        step1 = PipelineStep(name="regime_classification", module="market_regime")
        try:
            s1_start = time.monotonic()
            step1.output = await self._regime.get_current_regime() if self._regime else {}
            step1.latency_ms = (time.monotonic() - s1_start) * 1000
        except Exception as e:
            step1.error = str(e)
        result.steps.append(step1)

        step2 = PipelineStep(name="regime_transitions", module="market_regime")
        try:
            s2_start = time.monotonic()
            if hasattr(self._regime, "get_transition_data"):
                step2.output = await self._regime.get_transition_data()
            elif hasattr(self._regime, "get_transition_stats"):
                step2.output = await self._regime.get_transition_stats()
            step2.latency_ms = (time.monotonic() - s2_start) * 1000
        except Exception as e:
            step2.error = str(e)
        result.steps.append(step2)

        step3 = PipelineStep(name="regime_features", module="market_regime")
        try:
            s3_start = time.monotonic()
            if hasattr(self._regime, "get_feature_snapshot"):
                step3.output = self._regime.get_feature_snapshot()
            step3.latency_ms = (time.monotonic() - s3_start) * 1000
        except Exception as e:
            step3.error = str(e)
        result.steps.append(step3)

        if self._inference and not any(s.error for s in result.steps):
            step4 = PipelineStep(name="llm_market_report", module="ai_inference")
            try:
                s4_start = time.monotonic()
                regime_str = _safe_str(step1.output)
                transition_str = _safe_str(step2.output)
                features_str = _safe_str(step3.output)
                prompt = (
                    f"Generate market intelligence report.\n\n"
                    f"Current Regime: {regime_str[:500]}\n"
                    f"Transitions: {transition_str[:500]}\n"
                    f"Regime Features: {features_str[:500]}\n\n"
                    f"Provide: 1) Market overview 2) Regime assessment "
                    f"3) Key risk factors 4) Trading implications."
                )
                step4.output = await self._inference.generate(prompt, config_key="analysis")
                step4.latency_ms = (time.monotonic() - s4_start) * 1000
            except Exception as e:
                step4.error = str(e)
            result.steps.append(step4)

        result.total_latency_ms = (time.monotonic() - pipeline_start) * 1000
        result.success = all(s.error is None for s in result.steps)
        result.final_output = _build_final_output(result)
        return result

    async def research_workflow_pipeline(self, query: str) -> PipelineResult:
        result = PipelineResult(pipeline_name="research_workflow")
        pipeline_start = time.monotonic()

        step1 = PipelineStep(name="semantic_search", module="semantic_memory")
        try:
            s1_start = time.monotonic()
            step1.output = await self._retriever.search(query=query, limit=10) if self._retriever else []
            step1.latency_ms = (time.monotonic() - s1_start) * 1000
        except Exception as e:
            step1.error = str(e)
        result.steps.append(step1)

        step2 = PipelineStep(name="drift_analysis", module="drift_detection")
        try:
            s2_start = time.monotonic()
            step2.output = self._drift.run_full_pipeline() if self._drift else {}
            step2.latency_ms = (time.monotonic() - s2_start) * 1000
        except Exception as e:
            step2.error = str(e)
        result.steps.append(step2)

        step3 = PipelineStep(name="regime_context", module="market_regime")
        try:
            s3_start = time.monotonic()
            step3.output = await self._regime.get_current_regime() if self._regime else {}
            step3.latency_ms = (time.monotonic() - s3_start) * 1000
        except Exception as e:
            step3.error = str(e)
        result.steps.append(step3)

        if self._inference and not any(s.error for s in result.steps):
            step4 = PipelineStep(name="llm_research_answer", module="ai_inference")
            try:
                s4_start = time.monotonic()
                memory_str = _safe_str(step1.output)
                drift_str = _safe_str(step2.output)
                regime_str = _safe_str(step3.output)
                prompt = (
                    f"Research Query: {query}\n\n"
                    f"Semantic Memory: {memory_str[:500]}\n"
                    f"Drift Analysis: {drift_str[:500]}\n"
                    f"Regime Context: {regime_str[:500]}\n\n"
                    f"Answer the research question with supporting evidence "
                    f"from the available data."
                )
                step4.output = await self._inference.generate(prompt, config_key="analysis")
                step4.latency_ms = (time.monotonic() - s4_start) * 1000
            except Exception as e:
                step4.error = str(e)
            result.steps.append(step4)

        result.total_latency_ms = (time.monotonic() - pipeline_start) * 1000
        result.success = all(s.error is None for s in result.steps)
        result.final_output = _build_final_output(result)
        return result

    async def reflection_pipeline(self) -> PipelineResult:
        result = PipelineResult(pipeline_name="reflection")
        pipeline_start = time.monotonic()

        step1 = PipelineStep(name="recent_trades", module="trade_journal")
        try:
            s1_start = time.monotonic()
            step1.output = await self._journal.get_recent_trades(limit=20) if self._journal else []
            step1.latency_ms = (time.monotonic() - s1_start) * 1000
        except Exception as e:
            step1.error = str(e)
        result.steps.append(step1)

        step2 = PipelineStep(name="drift_analysis", module="drift_detection")
        try:
            s2_start = time.monotonic()
            step2.output = self._drift.run_full_pipeline() if self._drift else {}
            step2.latency_ms = (time.monotonic() - s2_start) * 1000
        except Exception as e:
            step2.error = str(e)
        result.steps.append(step2)

        step3 = PipelineStep(name="regime_context", module="market_regime")
        try:
            s3_start = time.monotonic()
            step3.output = await self._regime.get_current_regime() if self._regime else {}
            step3.latency_ms = (time.monotonic() - s3_start) * 1000
        except Exception as e:
            step3.error = str(e)
        result.steps.append(step3)

        if self._inference and not any(s.error for s in result.steps):
            step4 = PipelineStep(name="llm_reflection", module="ai_inference")
            try:
                s4_start = time.monotonic()
                trades_str = _safe_str(step1.output)
                drift_str = _safe_str(step2.output)
                regime_str = _safe_str(step3.output)
                prompt = (
                    f"Generate trading reflection.\n\n"
                    f"Recent Trades: {trades_str[:500]}\n"
                    f"Drift Analysis: {drift_str[:500]}\n"
                    f"Regime Context: {regime_str[:500]}\n\n"
                    f"Identify: 1) Recurring patterns 2) Degradation signals "
                    f"3) Regime mismatches 4) Recommendations for improvement."
                )
                step4.output = await self._inference.generate(prompt, config_key="reflection")
                step4.latency_ms = (time.monotonic() - s4_start) * 1000
            except Exception as e:
                step4.error = str(e)
            result.steps.append(step4)

        result.total_latency_ms = (time.monotonic() - pipeline_start) * 1000
        result.success = all(s.error is None for s in result.steps)
        result.final_output = _build_final_output(result)
        return result


def _safe_str(data: Any, max_len: int = 2000) -> str:
    try:
        import json as _json
        if isinstance(data, (dict, list)):
            s = _json.dumps(data, indent=2, default=str)
        elif hasattr(data, "to_dict"):
            s = _json.dumps(data.to_dict(), indent=2, default=str)
        else:
            s = str(data)
        return s[:max_len]
    except Exception:
        return str(data)[:max_len]


def _build_final_output(result: PipelineResult) -> dict:
    output = {
        "pipeline": result.pipeline_name,
        "total_latency_ms": round(result.total_latency_ms, 2),
        "steps_completed": len([s for s in result.steps if s.error is None]),
        "steps_total": len(result.steps),
        "step_details": [s.to_dict() for s in result.steps],
    }
    llm_steps = [s for s in result.steps if s.name.startswith("llm_") and s.error is None]
    if llm_steps:
        output["llm_analysis"] = llm_steps[-1].output
    return output
