from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from core.database import get_db
from core.logging import logger


class TradeIntelligenceRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g. RELIANCE)")
    prediction_id: Optional[int] = Field(default=None, description="Specific prediction log ID")
    trade_id: Optional[str] = Field(default=None, description="Trade identifier")


router = APIRouter(prefix="/trade", tags=["trade_intelligence"])


def _get_intelligence_service():
    try:
        from intelligence.trade_analysis.service import TradeIntelligenceService
        return TradeIntelligenceService()
    except Exception as e:
        logger.warning(f"TradeIntelligenceService not available: {e}")
        return None


@router.post("/intelligence")
async def trade_intelligence(
    request: TradeIntelligenceRequest,
    db: Session = Depends(get_db),
):
    service = _get_intelligence_service()
    if service is None:
        raise HTTPException(503, "Trade intelligence engine not available")

    try:
        result = service.analyze_trade(
            db=db,
            symbol=request.symbol.upper().strip(),
            prediction_id=request.prediction_id,
            trade_id=request.trade_id,
        )

        if result.get("status") == "not_found":
            raise HTTPException(404, result.get("message", "No data found"))
        if result.get("status") == "error":
            raise HTTPException(503, result.get("message", "Engine error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade intelligence failed: {e}")
        raise HTTPException(500, f"Trade intelligence failed: {str(e)}")


@router.post("/intelligence/failure")
async def trade_failure_analysis(
    request: TradeIntelligenceRequest,
    db: Session = Depends(get_db),
):
    service = _get_intelligence_service()
    if service is None:
        raise HTTPException(503, "Trade intelligence engine not available")

    try:
        result = service.analyze_failure(
            db=db,
            symbol=request.symbol.upper().strip(),
            prediction_id=request.prediction_id,
            trade_id=request.trade_id,
        )

        if result.get("status") == "not_found":
            raise HTTPException(404, result.get("message", "No data found"))
        if result.get("status") == "error":
            raise HTTPException(503, result.get("message", "Engine error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade failure analysis failed: {e}")
        raise HTTPException(500, f"Trade failure analysis failed: {str(e)}")


@router.post("/intelligence/reasoning")
async def trade_reasoning(
    request: TradeIntelligenceRequest,
    db: Session = Depends(get_db),
):
    service = _get_intelligence_service()
    if service is None:
        raise HTTPException(503, "Trade intelligence engine not available")

    try:
        result = service.get_reasoning(
            db=db,
            symbol=request.symbol.upper().strip(),
            prediction_id=request.prediction_id,
            trade_id=request.trade_id,
        )

        if result.get("status") == "not_found":
            raise HTTPException(404, result.get("message", "No data found"))
        if result.get("status") == "error":
            raise HTTPException(503, result.get("message", "Engine error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade reasoning failed: {e}")
        raise HTTPException(500, f"Trade reasoning failed: {str(e)}")
