from typing import Any, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter(prefix="/research", tags=["research"])


class ResearchQueryRequest(BaseModel):
    question: str = Field(description="Research question")
    context: Optional[dict] = Field(default=None, description="Optional context data")
    use_llm: bool = Field(default=True, description="Whether to use LLM for analysis")


class DriftAnalysisRequest(BaseModel):
    group_name: Optional[str] = Field(default=None, description="Filter by feature group")


class StrategyCompareRequest(BaseModel):
    strategies: list[str] = Field(description="Strategy names to compare")
    metric: str = Field(default="win_rate", description="Metric for ranking")


class ExperimentSummaryRequest(BaseModel):
    experiment_name: str = Field(description="Name of experiment")
    primary_metric: str = Field(default="sharpe_ratio", description="Primary metric")


class HypothesisRequest(BaseModel):
    drift_report: Optional[dict] = Field(default=None)
    degradation_report: Optional[dict] = Field(default=None)
    regime_report: Optional[dict] = Field(default=None)
    comparison_result: Optional[dict] = Field(default=None)
    use_llm: bool = Field(default=True)


class RegimeDegradationRequest(BaseModel):
    trades: Optional[list[dict]] = Field(default=None)


def _get_research_service():
    try:
        from intelligence.research_assistant.service import QuantResearchAssistant
        return QuantResearchAssistant()
    except Exception as e:
        logger.error(f"Failed to get research service: {e}")
        return None


@router.post("/query")
async def research_query(request: ResearchQueryRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    if not service.enabled:
        raise HTTPException(status_code=503, detail="Research assistant is disabled")
    result = await service.research_query(
        question=request.question,
        context=request.context,
        use_llm=request.use_llm,
    )
    if result.get("status") == "error":
        raise HTTPException(status_code=500, detail=result.get("answer", "Research query failed"))
    return result


@router.post("/drift")
async def analyze_drift(request: DriftAnalysisRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    report = await service.analyze_drift(group_name=request.group_name)
    return {"status": "ok", "drift_report": report.model_dump()}


@router.post("/strategies/compare")
async def compare_strategies(request: StrategyCompareRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    result = await service.compare_strategies(
        strategies=request.strategies,
        metric=request.metric,
    )
    return {"status": "ok", "comparison": result.model_dump()}


@router.post("/experiment/summarize")
async def summarize_experiment(request: ExperimentSummaryRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    result = await service.summarize_experiment(
        experiment_name=request.experiment_name,
        primary_metric=request.primary_metric,
    )
    return {"status": "ok", "experiment_summary": result.model_dump()}


@router.post("/hypotheses")
async def generate_hypotheses(request: HypothesisRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    result = await service.generate_hypotheses(
        drift_report=request.drift_report,
        degradation_report=request.degradation_report,
        regime_report=request.regime_report,
        comparison_result=request.comparison_result,
        use_llm=request.use_llm,
    )
    return {"status": "ok", "hypotheses": result.model_dump()}


@router.post("/regime/degradation")
async def analyze_regime_degradation(request: RegimeDegradationRequest):
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    result = await service.analyze_regime_degradation(trades=request.trades)
    return {"status": "ok", "regime_degradation": result.model_dump()}


@router.get("/health")
async def research_health():
    service = _get_research_service()
    if service is None:
        raise HTTPException(status_code=503, detail="Research assistant unavailable")
    health = await service.check_health()
    return {"status": "ok", "health": health}
