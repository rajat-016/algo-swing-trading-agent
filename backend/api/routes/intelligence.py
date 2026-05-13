from fastapi import APIRouter

from core.logging import logger
from core.governance import get_governance_manager

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/health")
async def intelligence_health():
    checks = {}

    regime_ok = _check_service(
        "regime",
        "intelligence.market_regime.service",
        "RegimeService",
    )
    checks["regime"] = regime_ok

    explainer_ok = _check_service(
        "trade_explainer",
        "intelligence.trade_analysis.trade_explainer",
        "TradeExplainer",
    )
    checks["trade_explainer"] = explainer_ok

    portfolio_ok = _check_service(
        "portfolio",
        "intelligence.portfolio_analysis.service",
        "PortfolioIntelligenceService",
    )
    checks["portfolio"] = portfolio_ok

    research_ok = _check_service(
        "research",
        "intelligence.research_assistant.service",
        "QuantResearchAssistant",
    )
    checks["research"] = research_ok

    reflection_ok = _check_service(
        "reflection",
        "intelligence.reflection_engine.service",
        "ReflectionService",
    )
    checks["reflection"] = reflection_ok

    memory_ok = _check_service(
        "memory",
        "memory.retrieval.semantic_retriever",
        "SemanticRetriever",
    )
    checks["memory"] = memory_ok

    drift_ok = _check_service(
        "drift",
        "intelligence.drift_detection.service",
        "DriftDetectionService",
    )
    checks["drift"] = drift_ok

    governance_ok = _check_governance()
    checks["governance"] = governance_ok

    available_count = sum(1 for c in checks.values() if c.get("available"))
    total = len(checks)
    overall = "healthy" if available_count == total else "degraded" if available_count > 0 else "unavailable"

    return {
        "status": overall,
        "available_modules": available_count,
        "total_modules": total,
        "modules": checks,
    }


def _check_governance() -> dict:
    try:
        gov = get_governance_manager()
        health = gov.check_health()
        return {
            "available": True,
            "audit_enabled": gov.audit.enabled,
            "integrity_enabled": gov.integrity.enabled,
            "confidence_enabled": gov.confidence.enabled,
            "safety_enabled": gov.safety.enabled,
            "execution_guard_enabled": gov.execution.enabled,
            "audit_entries": health["audit"]["stats"].get("total_entries", 0),
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


@router.get("/capabilities")
async def intelligence_capabilities():
    return {
        "status": "ok",
        "version": "1.0.0",
        "phase": 1,
        "capabilities": [
            {
                "name": "Market Regime Engine",
                "endpoint": "/intelligence/regime",
                "description": "Detect and classify market conditions (bull, bear, sideways, volatility, etc.)",
                "endpoints": [
                    "GET /intelligence/regime/current",
                    "POST /intelligence/regime/analyze",
                    "GET /intelligence/regime/history",
                    "GET /intelligence/regime/stats",
                    "GET /intelligence/regime/transitions",
                    "GET /intelligence/regime/distribution",
                    "GET /intelligence/regime/transition",
                    "GET /intelligence/regime/transition/logs",
                    "GET /intelligence/regime/health",
                ],
            },
            {
                "name": "Trade Intelligence Engine",
                "endpoint": "/intelligence/trade",
                "description": "Explain trade decisions, analyze failures, retrieve similar trades",
                "endpoints": [
                    "POST /intelligence/trade/explain",
                    "POST /intelligence/trade/intelligence",
                    "POST /intelligence/trade/intelligence/failure",
                    "POST /intelligence/trade/intelligence/reasoning",
                    "POST /intelligence/trade/intelligence/post-mortem",
                ],
            },
            {
                "name": "Portfolio Intelligence Engine",
                "endpoint": "/intelligence/portfolio",
                "description": "Analyze exposure, correlation, diversification, volatility, directional bias",
                "endpoints": [
                    "GET /intelligence/portfolio/risk",
                    "GET /intelligence/portfolio/exposure",
                    "GET /intelligence/portfolio/correlation",
                    "GET /intelligence/portfolio/history",
                    "GET /intelligence/portfolio/latest",
                    "GET /intelligence/portfolio/health",
                ],
            },
            {
                "name": "Semantic Memory System",
                "endpoint": "/intelligence/memory",
                "description": "Store and retrieve trade, market, and research memory with semantic search",
                "endpoints": [
                    "POST /intelligence/memory/search",
                    "POST /intelligence/memory/search/text",
                    "GET /intelligence/memory/stats",
                    "GET /intelligence/memory/health",
                ],
            },
            {
                "name": "Research Assistant",
                "endpoint": "/intelligence/research",
                "description": "Feature drift analysis, strategy comparison, experiment summarization, hypothesis generation",
                "endpoints": [
                    "POST /intelligence/research/query",
                    "POST /intelligence/research/drift",
                    "POST /intelligence/research/strategies/compare",
                    "POST /intelligence/research/experiment/summarize",
                    "POST /intelligence/research/hypotheses",
                    "POST /intelligence/research/regime/degradation",
                    "GET /intelligence/research/health",
                ],
            },
            {
                "name": "Reflection Engine",
                "endpoint": "/intelligence/reflection",
                "description": "Post-trade reflections, batch analysis, recurring patterns, degradation detection",
                "endpoints": [
                    "POST /intelligence/reflection/trade/{trade_id}",
                    "POST /intelligence/reflection/batch",
                    "POST /intelligence/reflection/system",
                    "GET /intelligence/reflection/patterns",
                    "GET /intelligence/reflection/degradation",
                    "GET /intelligence/reflection/regime-mismatches",
                    "GET /intelligence/reflection/instability",
                    "GET /intelligence/reflection/recommendations",
                    "POST /intelligence/reflection/summaries",
                    "GET /intelligence/reflection/logs",
                ],
            },
            {
                "name": "Correlation Analysis",
                "endpoint": "/intelligence/correlation",
                "description": "Rolling correlations, sector clustering, instability alerts, diversification scoring",
                "endpoints": [
                    "POST /intelligence/correlation/analyze",
                    "GET /intelligence/correlation/rolling",
                    "GET /intelligence/correlation/clusters",
                    "GET /intelligence/correlation/instability",
                    "GET /intelligence/correlation/diversification",
                    "GET /intelligence/correlation/history",
                    "GET /intelligence/correlation/latest",
                    "GET /intelligence/correlation/health",
                ],
            },
            {
                "name": "Feature Drift Detection",
                "endpoint": "/intelligence/drift",
                "description": "Distribution shift analysis, variance tracking, prediction contribution drift, alerting",
                "endpoints": [
                    "POST /intelligence/drift/shift",
                    "POST /intelligence/drift/shift/batch",
                    "POST /intelligence/drift/variance",
                    "POST /intelligence/drift/contribution",
                    "POST /intelligence/drift/pipeline",
                    "GET /intelligence/drift/baselines",
                    "GET /intelligence/drift/alerts",
                    "GET /intelligence/drift/health",
                ],
            },
            {
                "name": "AI Trade Journal",
                "endpoint": "/intelligence/journal",
                "description": "Persistent trade journaling with semantic search, stats, and post-trade summaries",
                "endpoints": [
                    "GET /intelligence/journal/trades",
                    "GET /intelligence/journal/trades/{trade_id}",
                    "POST /intelligence/journal/search",
                    "GET /intelligence/journal/stats",
                    "GET /intelligence/journal/search/text",
                ],
            },
        ],
    }


def _check_service(service_name: str, module_path: str, class_name: str) -> dict:
    try:
        import importlib
        module = importlib.import_module(module_path)
        if hasattr(module, class_name):
            return {"available": True, "module": module_path}
        return {"available": False, "error": f"{class_name} not found in {module_path}"}
    except ImportError as e:
        return {"available": False, "error": str(e)}
    except Exception as e:
        return {"available": False, "error": str(e)}
