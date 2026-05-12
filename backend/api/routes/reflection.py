from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from core.database import get_db
from core.logging import logger


class BatchReflectionRequest(BaseModel):
    period_label: str = Field(default="recent", description="Label for this reflection period")
    trade_ids: Optional[list[str]] = Field(default=None, description="Specific trade IDs to reflect on")


router = APIRouter(prefix="/reflection", tags=["reflection"])


def _get_reflection_service():
    try:
        from intelligence.reflection_engine.service import ReflectionService
        return ReflectionService()
    except Exception as e:
        logger.warning(f"ReflectionService not available: {e}")
        return None


@router.post("/trade/{trade_id}")
async def reflect_on_trade(
    trade_id: str,
    db: Session = Depends(get_db),
):
    service = _get_reflection_service()
    if service is None:
        raise HTTPException(503, "Reflection engine not available")

    try:
        from ai.journal.journal_service import TradeJournalService
        journal = TradeJournalService()
        trade = journal.get_trade_by_id(trade_id)
        if trade is None:
            raise HTTPException(404, f"Trade {trade_id} not found in journal")

        reflection = await service.reflect_trade(trade)
        if reflection is None:
            raise HTTPException(500, "Failed to generate reflection")

        return {"status": "ok", "reflection": reflection.model_dump()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade reflection failed: {e}")
        raise HTTPException(500, f"Trade reflection failed: {str(e)}")


@router.post("/batch")
async def batch_reflection(
    request: BatchReflectionRequest,
    db: Session = Depends(get_db),
):
    service = _get_reflection_service()
    if service is None:
        raise HTTPException(503, "Reflection engine not available")

    try:
        from ai.journal.journal_service import TradeJournalService
        journal = TradeJournalService()

        if request.trade_ids:
            trades = []
            for tid in request.trade_ids:
                t = journal.get_trade_by_id(tid)
                if t:
                    trades.append(t)
        else:
            trades = journal.get_recent_duckdb_trades(limit=100)

        if not trades:
            raise HTTPException(404, "No trades found for batch reflection")

        result = await service.batch_reflect(trades, request.period_label)
        if result is None:
            raise HTTPException(500, "Failed to generate batch reflection")

        return {"status": "ok", "reflection": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch reflection failed: {e}")
        raise HTTPException(500, f"Batch reflection failed: {str(e)}")


@router.get("/logs")
async def list_reflection_logs(
    limit: int = Query(default=50, ge=1, le=200),
):
    service = _get_reflection_service()
    if service is None:
        raise HTTPException(503, "Reflection engine not available")

    try:
        logs = await service.get_reflection_logs(limit=limit)
        return {"reflections": logs, "count": len(logs)}
    except Exception as e:
        logger.error(f"Failed to list reflection logs: {e}")
        raise HTTPException(500, f"Failed to list reflection logs: {str(e)}")
