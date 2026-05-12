from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from core.database import get_db
from core.logging import logger
from core.config import get_settings


class TradeExplainRequest(BaseModel):
    symbol: str = Field(..., description="Stock symbol (e.g. RELIANCE)")
    prediction_id: Optional[int] = Field(default=None, description="Specific prediction log ID")
    trade_id: Optional[str] = Field(default=None, description="Trade identifier")


router = APIRouter(prefix="/trade", tags=["trade_intelligence"])


def _get_trade_explainer():
    try:
        from intelligence.trade_analysis.trade_explainer import TradeExplainer
        return TradeExplainer()
    except Exception as e:
        logger.warning(f"TradeExplainer not available: {e}")
        return None


@router.post("/explain")
async def explain_trade(
    request: TradeExplainRequest,
    db: Session = Depends(get_db),
):
    explainer = _get_trade_explainer()
    if explainer is None:
        raise HTTPException(503, "Trade explainer not available")

    try:
        explanation = explainer.explain(
            db=db,
            symbol=request.symbol.upper().strip(),
            prediction_id=request.prediction_id,
            trade_id=request.trade_id,
        )

        if explanation.status == "not_found":
            raise HTTPException(404, explanation.message or "No data found for this trade")

        return explanation.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Trade explanation failed: {e}")
        raise HTTPException(500, f"Trade explanation failed: {str(e)}")
