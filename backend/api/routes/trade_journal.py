from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.logging import logger


class TradeSearchRequest(BaseModel):
    query: str = Field(..., description="Semantic search query")
    ticker: Optional[str] = Field(default=None, description="Filter by ticker symbol")
    outcome: Optional[str] = Field(default=None, description="Filter by outcome (WIN/LOSS/OPEN)")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")


router = APIRouter(prefix="/journal", tags=["trade_journal"])


def _get_journal_service():
    try:
        from ai.journal.journal_service import TradeJournalService
        return TradeJournalService()
    except Exception as e:
        logger.warning(f"TradeJournalService not available: {e}")
        return None


@router.get("/trades")
async def list_journaled_trades(
    limit: int = Query(default=50, ge=1, le=200),
):
    journal = _get_journal_service()
    if journal is None:
        raise HTTPException(503, "Trade journal not available")

    try:
        trades = journal.get_recent_duckdb_trades(limit=limit)
        return {"trades": trades, "count": len(trades)}
    except Exception as e:
        logger.error(f"Failed to list trades: {e}")
        raise HTTPException(500, f"Failed to list trades: {str(e)}")


@router.get("/trades/{trade_id}")
async def get_journaled_trade(trade_id: str):
    journal = _get_journal_service()
    if journal is None:
        raise HTTPException(503, "Trade journal not available")

    try:
        trade = journal.get_trade_by_id(trade_id)
        if trade is None:
            raise HTTPException(404, f"Trade {trade_id} not found")
        return trade
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get trade {trade_id}: {e}")
        raise HTTPException(500, f"Failed to get trade: {str(e)}")


@router.post("/search")
async def search_journaled_trades(request: TradeSearchRequest):
    journal = _get_journal_service()
    if journal is None:
        raise HTTPException(503, "Trade journal not available")

    try:
        results = await journal.search_trades(
            query=request.query,
            ticker=request.ticker,
            outcome=request.outcome,
            limit=request.limit,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Trade search failed: {e}")
        raise HTTPException(500, f"Trade search failed: {str(e)}")


@router.get("/stats")
async def journal_stats():
    journal = _get_journal_service()
    if journal is None:
        raise HTTPException(503, "Trade journal not available")

    try:
        stats = await journal.get_journal_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get journal stats: {e}")
        raise HTTPException(500, f"Failed to get journal stats: {str(e)}")


@router.get("/search/text")
async def text_search_trades(
    q: str = Query(..., description="Search text"),
    ticker: Optional[str] = Query(default=None),
    outcome: Optional[str] = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    journal = _get_journal_service()
    if journal is None:
        raise HTTPException(503, "Trade journal not available")

    try:
        results = await journal.search_trades(
            query=q,
            ticker=ticker,
            outcome=outcome,
            limit=limit,
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(500, f"Text search failed: {str(e)}")
