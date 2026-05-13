import asyncio
import time
from loguru import logger
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from ai.prompts.registry import registry as prompt_registry
from core.governance import get_governance_manager

if TYPE_CHECKING:
    from ai.inference.service import InferenceService


@dataclass
class WorkflowStep:
    name: str
    prompt_name: str
    config_key: str = "default"
    template_kwargs: dict = field(default_factory=dict)
    output_key: str = ""
    depends_on: list[str] = field(default_factory=list)
    fallback: Optional[str] = None


@dataclass
class WorkflowResult:
    step_results: dict[str, str] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    total_latency: float = 0.0
    success: bool = True


class OrchestrationEngine:
    def __init__(self, inference: Optional["InferenceService"] = None):
        from ai.inference.service import InferenceService
        self.inference = inference or InferenceService()
        self._workflows: dict[str, list[WorkflowStep]] = {}
        self._governance = get_governance_manager()

    def register_workflow(self, name: str, steps: list[WorkflowStep]):
        self._workflows[name] = steps
        logger.info(f"Registered workflow '{name}' with {len(steps)} steps")

    async def run_workflow(
        self,
        name: str,
        initial_kwargs: Optional[dict] = None,
    ) -> WorkflowResult:
        steps = self._workflows.get(name)
        if steps is None:
            raise KeyError(f"Workflow not found: {name}")

        result = WorkflowResult()
        context = dict(initial_kwargs or {})
        start = time.monotonic()

        for step in steps:
            missing_deps = [d for d in step.depends_on if d not in result.step_results]
            if missing_deps:
                err = f"Missing dependencies: {missing_deps}"
                result.errors[step.name] = err
                logger.error(f"Workflow '{name}' step '{step.name}': {err}")
                continue

            render_kwargs = {**context, **step.template_kwargs}
            try:
                output = await self.inference.render_and_generate(
                    prompt_name=step.prompt_name,
                    config_key=step.config_key,
                    **render_kwargs,
                )
                key = step.output_key or step.name
                result.step_results[key] = output
                context[key] = output
                logger.debug(f"Workflow '{name}' step '{step.name}' completed")
            except Exception as e:
                err = str(e)
                result.errors[step.name] = err
                logger.error(f"Workflow '{name}' step '{step.name}' failed: {e}")
                if step.fallback:
                    result.step_results[step.output_key or step.name] = step.fallback
                    context[step.output_key or step.name] = step.fallback
                    result.errors[step.name] += " (fallback used)"

        result.total_latency = time.monotonic() - start
        result.success = len(result.errors) == 0

        self._governance.log_ai_output(
            action="workflow_completed",
            component=f"orchestration.{name}",
            details={
                "workflow": name,
                "steps_completed": len(result.step_results),
                "steps_failed": len(result.errors),
                "step_names": list(result.step_results.keys()),
            },
            status="success" if result.success else "partial",
        )

        return result

    async def analyze_market_regime(
        self,
        trend_status: str,
        volatility: str,
        volume_trend: str,
        breadth: str,
        vix_level: str,
        sector_rotation: str,
    ) -> str:
        start = time.monotonic()
        try:
            result = await self.inference.render_and_generate(
                "market_regime",
                config_key="analysis",
                trend_status=trend_status,
                volatility=volatility,
                volume_trend=volume_trend,
                breadth=breadth,
                vix_level=vix_level,
                sector_rotation=sector_rotation,
            )
            self._governance.log_ai_output(
                action="analyze_market_regime",
                component="orchestration",
                details={
                    "trend_status": trend_status,
                    "volatility": volatility,
                    "volume_trend": volume_trend,
                },
                start_time=start,
            )
            return result
        except Exception as e:
            self._governance.log_ai_output(
                action="analyze_market_regime",
                component="orchestration",
                details={
                    "trend_status": trend_status,
                    "volatility": volatility,
                },
                start_time=start,
                status="error",
                error=str(e),
            )
            raise

    async def explain_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        direction: str,
        confidence: float,
        regime: str,
        top_features: str,
        feature_values: str,
        outcome: str,
        pnl: float,
    ) -> str:
        return await self.inference.render_and_generate(
            "trade_explanation",
            config_key="analysis",
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            direction=direction,
            confidence=confidence,
            regime=regime,
            top_features=top_features,
            feature_values=feature_values,
            outcome=outcome,
            pnl=pnl,
        )

    async def analyze_portfolio(self, portfolio_data: str, **kwargs) -> str:
        return await self.inference.render_and_generate(
            "portfolio_risk",
            config_key="analysis",
            portfolio_data=portfolio_data,
            **kwargs,
        )

    async def generate_post_trade_reflection(
        self,
        symbol: str,
        trade_id: str,
        entry_price: Optional[float] = None,
        exit_price: Optional[float] = None,
        direction: str = "BUY",
        confidence: Optional[float] = None,
        regime: str = "",
        outcome: str = "",
        pnl: float = 0,
        pnl_pct: float = 0,
        exit_reason: str = "",
        feature_snapshot: str = "{}",
        portfolio_state: str = "{}",
    ) -> str:
        return await self.inference.render_and_generate(
            "post_trade_reflection",
            config_key="reflection",
            symbol=symbol,
            trade_id=trade_id,
            entry_price=entry_price or 0,
            exit_price=exit_price or 0,
            direction=direction,
            confidence=confidence or 0,
            regime=regime,
            outcome=outcome,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=exit_reason,
            feature_snapshot=feature_snapshot,
            portfolio_state=portfolio_state,
        )

    async def generate_reflection(
        self,
        period: str,
        total_trades: int,
        win_rate: float,
        profit_factor: float,
        avg_win: float,
        avg_loss: float,
        max_drawdown: float,
        regime_breakdown: str,
        feature_stability: str,
        failure_patterns: str,
    ) -> str:
        return await self.inference.render_and_generate(
            "reflection",
            config_key="reflection",
            period=period,
            total_trades=total_trades,
            win_rate=win_rate,
            profit_factor=profit_factor,
            avg_win=avg_win,
            avg_loss=avg_loss,
            max_drawdown=max_drawdown,
            regime_breakdown=regime_breakdown,
            feature_stability=feature_stability,
            failure_patterns=failure_patterns,
        )

    async def research_query(self, question: str, context_data: str) -> str:
        return await self.inference.render_and_generate(
            "research_query",
            config_key="analysis",
            question=question,
            context_data=context_data,
        )

    async def analyze_feature_drift(
        self,
        total_features: str,
        drifted_count: str,
        warning_count: str,
        drift_ratio: str,
        drifted_features: str,
        regime_context: str = "",
    ) -> str:
        return await self.inference.render_and_generate(
            "feature_drift_analysis",
            config_key="analysis",
            total_features=total_features,
            drifted_count=drifted_count,
            warning_count=warning_count,
            drift_ratio=drift_ratio,
            drifted_features=drifted_features,
            regime_context=regime_context,
        )

    async def deep_compare_strategies(
        self,
        strategies: str,
        performance_data: str,
        gap_analysis: str,
        regime_context: str = "",
    ) -> str:
        return await self.inference.render_and_generate(
            "strategy_deep_compare",
            config_key="analysis",
            strategies=strategies,
            performance_data=performance_data,
            gap_analysis=gap_analysis,
            regime_context=regime_context,
        )

    async def analyze_experiment(
        self,
        experiment_name: str,
        total_runs: str,
        metric_trends: str,
        parameter_sensitivity: str,
        best_params: str = "",
        worst_params: str = "",
    ) -> str:
        return await self.inference.render_and_generate(
            "experiment_analysis",
            config_key="analysis",
            experiment_name=experiment_name,
            total_runs=total_runs,
            metric_trends=metric_trends,
            parameter_sensitivity=parameter_sensitivity,
            best_params=best_params,
            worst_params=worst_params,
        )

    async def process_query(self, question: str) -> str:
        start = time.monotonic()
        search_prompt = prompt_registry.render(
            "semantic_search",
            question=question,
        )
        search_result = await self.inference.generate(
            search_prompt,
            config_key="precise",
        )

        import json as _json
        try:
            parsed = _json.loads(search_result)
            query_text = parsed.get("search_query", question)
            memory_types = parsed.get("memory_types", ["trade_memory"])
        except Exception:
            query_text = question
            memory_types = ["trade_memory"]

        similar = await self.inference.semantic_search(
            collection="trade_memory",
            query=query_text,
            n_results=5,
        )

        context = _json.dumps(similar, indent=2) if similar else "No relevant memories found."

        result = await self.inference.render_and_generate(
            "research_query",
            config_key="analysis",
            question=question,
            context_data=context,
        )

        exec_ok, exec_reason = self._governance.execution.check_output(
            result, source="process_query"
        )
        if not exec_ok:
            self._governance.log_ai_output(
                action="process_query_blocked",
                component="orchestration",
                details={
                    "question": question[:200],
                    "reason": exec_reason,
                    "output_preview": result[:200],
                },
                start_time=start,
                status="blocked",
                error=exec_reason,
            )
            raise RuntimeError(
                f"AI output contained execution intent and was blocked: {exec_reason}"
            )

        self._governance.log_ai_output(
            action="process_query",
            component="orchestration",
            details={
                "question": question[:200],
                "memory_types": memory_types,
                "response_length": len(result),
            },
            start_time=start,
        )

        return result
