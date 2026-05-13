from datetime import datetime, timezone
from typing import Any, Optional
from loguru import logger

from intelligence.research_assistant.drift_analyzer import DriftAnalyzer, DriftReport
from intelligence.research_assistant.strategy_compare import StrategyComparator, StrategyComparisonResult
from intelligence.research_assistant.experiment_summarizer import ExperimentSummarizer, ExperimentSummary, ExperimentRun
from intelligence.research_assistant.hypothesis_generator import HypothesisGenerator, HypothesisReport
from intelligence.research_assistant.regime_degradation import RegimeDegradationAnalyzer, RegimeDegradationReport


class QuantResearchAssistant:
    def __init__(
        self,
        drift_analyzer: Optional[DriftAnalyzer] = None,
        strategy_comparator: Optional[StrategyComparator] = None,
        experiment_summarizer: Optional[ExperimentSummarizer] = None,
        hypothesis_generator: Optional[HypothesisGenerator] = None,
        regime_degradation: Optional[RegimeDegradationAnalyzer] = None,
        inference_service=None,
        analytics_db=None,
    ):
        self.drift_analyzer = drift_analyzer or DriftAnalyzer()
        self.strategy_comparator = strategy_comparator or StrategyComparator(analytics_db)
        self.experiment_summarizer = experiment_summarizer or ExperimentSummarizer(analytics_db)
        self.hypothesis_generator = hypothesis_generator or HypothesisGenerator(inference_service)
        self.regime_degradation = regime_degradation or RegimeDegradationAnalyzer(analytics_db=analytics_db)
        self._inference = inference_service
        self._analytics_db = analytics_db
        self._enabled = True
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        self.drift_analyzer.initialize()
        self._initialized = True
        logger.info("QuantResearchAssistant initialized")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool):
        self._enabled = enabled
        logger.info(f"QuantResearchAssistant enabled={enabled}")

    async def research_query(
        self,
        question: str,
        context: Optional[dict] = None,
        use_llm: bool = True,
    ) -> dict:
        if not self._enabled:
            return {"status": "disabled", "message": "Research assistant is disabled"}

        query_type = self._classify_query(question)
        result: dict[str, Any] = {
            "question": question,
            "query_type": query_type,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "status": "ok",
        }

        try:
            if query_type == "feature_drift":
                group = context.get("group_name") if context else None
                drift_report = await self.drift_analyzer.analyze_feature_drift(group_name=group)
                result["drift_report"] = drift_report.model_dump()
                result["answer"] = drift_report.summary

            elif query_type == "strategy_comparison":
                strategies = context.get("strategies", []) if context else []
                trades = context.get("trades") if context else None
                metric = context.get("metric", "win_rate") if context else "win_rate"
                comparison = await self.strategy_comparator.compare_strategies(
                    strategies=strategies, trades=trades, metric=metric,
                )
                result["comparison"] = comparison.model_dump()
                result["answer"] = comparison.summary

            elif query_type == "experiment_summary":
                experiment_name = context.get("experiment_name", "default") if context else "default"
                runs_data = context.get("runs") if context else None
                primary_metric = context.get("primary_metric", "sharpe_ratio") if context else "sharpe_ratio"
                runs = None
                if runs_data:
                    runs = [ExperimentRun(**r) if isinstance(r, dict) else r for r in runs_data]
                summary = await self.experiment_summarizer.summarize_experiment(
                    experiment_name=experiment_name, runs=runs, primary_metric=primary_metric,
                )
                result["experiment_summary"] = summary.model_dump()
                result["answer"] = summary.summary

            elif query_type == "regime_degradation":
                trades = context.get("trades") if context else None
                deg_report = await self.regime_degradation.analyze_regime_degradation(trades=trades)
                result["regime_degradation"] = deg_report.model_dump()
                result["answer"] = deg_report.summary

            elif query_type == "hypothesis_generation":
                drift_dict = context.get("drift_report") if context else None
                degradation_dict = context.get("degradation_report") if context else None
                regime_dict = context.get("regime_report") if context else None
                comparison_dict = context.get("comparison_result") if context else None
                hypotheses = await self.hypothesis_generator.generate_hypotheses(
                    drift_report=drift_dict,
                    degradation_report=degradation_dict,
                    regime_report=regime_dict,
                    comparison_result=comparison_dict,
                    use_llm=use_llm,
                )
                result["hypotheses"] = hypotheses.model_dump()
                result["answer"] = hypotheses.summary

            elif query_type == "general":
                result["answer"] = await self._general_research_answer(question, context, use_llm)

            else:
                result["answer"] = f"Research query type '{query_type}' not recognized"
                result["status"] = "error"

        except Exception as e:
            logger.error(f"Research query failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)
            result["answer"] = f"Research query failed: {e}"

        return result

    def _classify_query(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["hypothes", "what if", "why does", "maybe", "theory"]):
            return "hypothesis_generation"
        if any(w in q for w in ["drift", "unstable", "feature stability", "psi"]):
            return "feature_drift"
        if any(w in q for w in ["compare", "vs ", "versus", "better", "best strategy"]):
            return "strategy_comparison"
        if any(w in q for w in ["experiment", "backtest result", "run summary"]):
            return "experiment_summary"
        if any(w in q for w in ["degrad", "volatile", "degrade"]):
            if any(w in q for w in ["regime", "environment", "market condition"]):
                return "regime_degradation"
        return "general"

    async def _general_research_answer(
        self,
        question: str,
        context: Optional[dict] = None,
        use_llm: bool = True,
    ) -> str:
        if use_llm and self._inference is not None:
            try:
                context_str = ""
                if context:
                    context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
                prompt = (
                    f"Research Question: {question}\n\n"
                    f"Available Context:\n{context_str if context_str else 'No additional context'}\n\n"
                    "Provide a concise research-oriented answer with supporting evidence."
                )
                return await self._inference.generate(prompt, config_key="analysis")
            except Exception as e:
                logger.warning(f"LLM general query failed: {e}")
        return f"Research query received: {question}. Enable LLM backend for detailed analysis."

    async def analyze_drift(self, group_name: Optional[str] = None) -> DriftReport:
        return await self.drift_analyzer.analyze_feature_drift(group_name=group_name)

    async def compare_strategies(
        self,
        strategies: list[str],
        trades: Optional[list[dict]] = None,
        metric: str = "win_rate",
    ) -> StrategyComparisonResult:
        return await self.strategy_comparator.compare_strategies(
            strategies=strategies, trades=trades, metric=metric,
        )

    async def summarize_experiment(
        self,
        experiment_name: str,
        runs: Optional[list[ExperimentRun]] = None,
        primary_metric: str = "sharpe_ratio",
    ) -> ExperimentSummary:
        return await self.experiment_summarizer.summarize_experiment(
            experiment_name=experiment_name, runs=runs, primary_metric=primary_metric,
        )

    async def generate_hypotheses(
        self,
        drift_report: Optional[dict] = None,
        degradation_report: Optional[dict] = None,
        regime_report: Optional[dict] = None,
        comparison_result: Optional[dict] = None,
        use_llm: bool = True,
    ) -> HypothesisReport:
        return await self.hypothesis_generator.generate_hypotheses(
            drift_report=drift_report,
            degradation_report=degradation_report,
            regime_report=regime_report,
            comparison_result=comparison_result,
            use_llm=use_llm,
        )

    async def analyze_regime_degradation(
        self,
        trades: Optional[list[dict]] = None,
    ) -> RegimeDegradationReport:
        return await self.regime_degradation.analyze_regime_degradation(trades=trades)

    async def check_health(self) -> dict:
        return {
            "enabled": self._enabled,
            "initialized": self._initialized,
            "drift_analyzer_ready": self.drift_analyzer.is_ready,
        }
