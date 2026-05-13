from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from core.logging import logger


class MemorySearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Semantic search query")
    memory_type: Optional[str] = Field(default=None, description="Filter: trade, market, research")
    ticker: Optional[str] = Field(default=None, description="Filter by ticker symbol")
    outcome: Optional[str] = Field(default=None, description="Filter: WIN, LOSS, OPEN")
    regime: Optional[str] = Field(default=None, description="Filter by regime type")
    event_type: Optional[str] = Field(default=None, description="Filter by event type")
    feature_name: Optional[str] = Field(default=None, description="Filter by feature name")
    strategy: Optional[str] = Field(default=None, description="Filter by strategy name")
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    limit: int = Field(default=10, ge=1, le=100)
    offset: int = Field(default=0, ge=0, le=1000)
    min_relevance: float = Field(default=0.0, ge=0.0, le=1.0)
    use_hybrid: bool = Field(default=False)


class MemoryStoreRequest(BaseModel):
    memory_type: str = Field(..., description="trade, market, or research")
    content: dict = Field(..., description="Memory content matching the schema")
    memory_id: Optional[str] = Field(default=None)


router = APIRouter(prefix="/memory", tags=["memory"])


def _get_semantic_retriever():
    try:
        from memory.retrieval.semantic_retriever import SemanticRetriever
        retriever = SemanticRetriever()
        retriever._initialized = True
        return retriever
    except Exception as e:
        logger.warning(f"SemanticRetriever not available: {e}")
        return None


def _build_memory_filter(params: MemorySearchRequest):
    from memory.schemas.memory_schemas import MemoryFilter, MemoryType

    filter_kwargs = {}
    if params.memory_type:
        type_map = {
            "trade": MemoryType.TRADE,
            "market": MemoryType.MARKET,
            "research": MemoryType.RESEARCH,
        }
        mt = type_map.get(params.memory_type.lower())
        if mt is None:
            raise HTTPException(400, f"Invalid memory_type: {params.memory_type}. Use: trade, market, research")
        filter_kwargs["memory_type"] = mt
    if params.ticker:
        filter_kwargs["ticker"] = params.ticker
    if params.outcome:
        filter_kwargs["outcome"] = params.outcome
    if params.regime:
        filter_kwargs["market_regime"] = params.regime
    if params.event_type:
        filter_kwargs["event_type"] = params.event_type
    if params.feature_name:
        filter_kwargs["feature_name"] = params.feature_name
    if params.strategy:
        filter_kwargs["strategy"] = params.strategy
    if params.min_confidence is not None:
        filter_kwargs["min_confidence"] = params.min_confidence
    if params.limit:
        filter_kwargs["max_results"] = params.limit
    if params.offset:
        filter_kwargs["offset"] = params.offset

    return MemoryFilter(**filter_kwargs)


@router.post("/search")
async def memory_search(request: MemorySearchRequest):
    retriever = _get_semantic_retriever()
    if retriever is None:
        raise HTTPException(503, "Semantic memory system not available")

    try:
        memory_filter = _build_memory_filter(request)
        results = await retriever.advanced_search(
            query=request.query,
            memory_filter=memory_filter,
            n_results=request.limit,
            use_hybrid=request.use_hybrid,
            min_relevance=request.min_relevance,
        )
        return {
            "status": "ok",
            "results": [r.model_dump() for r in results],
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory search failed: {e}")
        raise HTTPException(500, f"Memory search failed: {str(e)}")


@router.post("/search/text")
async def memory_text_search(request: MemorySearchRequest):
    retriever = _get_semantic_retriever()
    if retriever is None:
        raise HTTPException(503, "Semantic memory system not available")

    try:
        memory_filter = _build_memory_filter(request)
        results = await retriever.search_by_text(
            query=request.query,
            memory_filter=memory_filter,
            n_results=request.limit,
        )
        return {
            "status": "ok",
            "results": [r.model_dump() for r in results],
            "count": len(results),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Memory text search failed: {e}")
        raise HTTPException(500, f"Memory text search failed: {str(e)}")


@router.get("/stats")
async def memory_stats():
    retriever = _get_semantic_retriever()
    if retriever is None:
        raise HTTPException(503, "Semantic memory system not available")

    try:
        stats = await retriever.get_memory_stats()
        return {"status": "ok", "stats": stats}
    except Exception as e:
        logger.error(f"Failed to get memory stats: {e}")
        raise HTTPException(500, f"Failed to get memory stats: {str(e)}")


@router.get("/health")
async def memory_health():
    retriever = _get_semantic_retriever()
    if retriever is None:
        return {
            "status": "unavailable",
            "semantic_memory_enabled": False,
        }

    try:
        stats = await retriever.get_memory_stats()
        return {
            "status": "available",
            "semantic_memory_enabled": True,
            "collections": {
                k: v for k, v in stats.items() if k != "embedding_cache" and k != "audit"
            },
            "audit": stats.get("audit"),
        }
    except Exception as e:
        return {
            "status": "degraded",
            "semantic_memory_enabled": True,
            "error": str(e),
        }
