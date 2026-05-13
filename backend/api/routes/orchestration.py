import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.orchestration import (
    OrchestrationEngine, OutputStandardizer, StandardIntelligenceOutput,
)
from ai.inference.service import InferenceService
from core.governance import get_governance_manager
from core.logging import logger

router = APIRouter(prefix="/orchestration", tags=["orchestration"])

_engine: OrchestrationEngine = None


def _get_engine() -> OrchestrationEngine:
    global _engine
    if _engine is None:
        inf = InferenceService()
        _engine = OrchestrationEngine(inference=inf)
    return _engine


class PipelineRequest(BaseModel):
    pipeline: str = Field(..., description="Pipeline name: trade_explanation, portfolio_risk, market_analysis, research_workflow, reflection")
    symbol: str = Field(default="", description="Symbol for trade-specific pipelines")
    query: str = Field(default="", description="Query for research pipelines")


class RetrieveRequest(BaseModel):
    sources: list[str] = Field(..., description="Data sources to retrieve: regime, portfolio, explanation, similar_trades, journal, drift, reflection, memory, exposure, correlation")
    symbol: str = Field(default="")
    query: str = Field(default="")


class EnrichedLLMRequest(BaseModel):
    prompt_type: str = Field(..., description="Prompt type: market_regime, trade_explanation, portfolio_risk, research_query, reflection, post_trade_reflection")
    symbol: str = Field(default="")
    query: str = Field(default="")
    kwargs: dict = Field(default_factory=dict)


class ContextRequest(BaseModel):
    symbol: str = Field(default="")
    query: str = Field(default="")


@router.post("/pipeline")
async def run_pipeline(req: PipelineRequest):
    start = time.monotonic()
    try:
        engine = _get_engine()
        result = await engine.run_pipeline(req.pipeline, symbol=req.symbol, query=req.query)
        latency_ms = (time.monotonic() - start) * 1000
        std = StandardIntelligenceOutput(
            module=f"pipeline.{req.pipeline}",
            latency_ms=latency_ms,
            data=result,
        )
        get_governance_manager().log_ai_output(
            action="run_pipeline", component="orchestration",
            details={"pipeline": req.pipeline, "symbol": req.symbol},
            start_time=start,
        )
        return std.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        latency_ms = (time.monotonic() - start) * 1000
        return OutputStandardizer.error("pipeline", str(e), latency_ms).to_dict()


@router.post("/retrieve")
async def retrieve_intelligence(req: RetrieveRequest):
    start = time.monotonic()
    try:
        engine = _get_engine()
        result = await engine.retrieve_intelligence(
            req.sources, symbol=req.symbol, query=req.query,
        )
        latency_ms = (time.monotonic() - start) * 1000
        std = StandardIntelligenceOutput(
            module="retrieval_orchestrator",
            latency_ms=latency_ms,
            data=result,
        )
        return std.to_dict()
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        latency_ms = (time.monotonic() - start) * 1000
        return OutputStandardizer.error("retrieval", str(e), latency_ms).to_dict()


@router.post("/context")
async def get_context(req: ContextRequest):
    start = time.monotonic()
    try:
        engine = _get_engine()
        bundle = await engine.get_context_bundle(symbol=req.symbol, query=req.query)
        latency_ms = (time.monotonic() - start) * 1000
        std = StandardIntelligenceOutput(
            module="context_injector",
            latency_ms=latency_ms,
            data=bundle,
        )
        return std.to_dict()
    except Exception as e:
        logger.error(f"Context bundle failed: {e}")
        latency_ms = (time.monotonic() - start) * 1000
        return OutputStandardizer.error("context", str(e), latency_ms).to_dict()


@router.post("/llm/enriched")
async def enriched_llm_call(req: EnrichedLLMRequest):
    start = time.monotonic()
    try:
        engine = _get_engine()
        result = await engine.enriched_llm_call(
            req.prompt_type, symbol=req.symbol, query=req.query, **req.kwargs,
        )
        latency_ms = (time.monotonic() - start) * 1000
        std = StandardIntelligenceOutput(
            module=f"enriched_llm.{req.prompt_type}",
            latency_ms=latency_ms,
            data={"response": result},
        )
        get_governance_manager().log_ai_output(
            action="enriched_llm_call", component="orchestration",
            details={"prompt_type": req.prompt_type, "symbol": req.symbol},
            start_time=start,
        )
        return std.to_dict()
    except Exception as e:
        logger.error(f"Enriched LLM call failed: {e}")
        latency_ms = (time.monotonic() - start) * 1000
        return OutputStandardizer.error(f"enriched_llm.{req.prompt_type}", str(e), latency_ms).to_dict()


@router.get("/pipelines")
async def list_pipelines():
    return {
        "pipelines": {
            "trade_explanation": "Regime context -> Trade explain -> Similar trades -> Journal -> LLM explanation",
            "portfolio_risk": "Portfolio analysis -> Regime context -> LLM risk analysis",
            "market_analysis": "Regime classification -> Transitions -> Features -> LLM market report",
            "research_workflow": "Semantic search -> Drift analysis -> Regime context -> LLM research answer",
            "reflection": "Recent trades -> Drift analysis -> Regime context -> LLM reflection",
        },
        "retrieval_sources": [
            "regime", "portfolio", "exposure", "correlation",
            "explanation", "similar_trades", "journal",
            "drift", "reflection", "memory",
        ],
        "prompt_types": [
            "market_regime", "trade_explanation", "portfolio_risk",
            "research_query", "reflection", "post_trade_reflection",
            "feature_drift_analysis", "strategy_deep_compare", "experiment_analysis",
        ],
    }


@router.get("/health")
async def orchestration_health():
    try:
        engine = _get_engine()
        ctx = engine.get_context_injector()
        retrieval = engine.get_retrieval_orchestrator()
        pipeline = engine.get_pipeline()
        return {
            "status": "healthy",
            "context_injector": ctx is not None,
            "retrieval_orchestrator": retrieval is not None,
            "pipelines": pipeline is not None,
            "workflows_registered": list(engine._workflows.keys()),
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
