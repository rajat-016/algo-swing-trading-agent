from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from core.database import get_db
from models.stock import Stock, StockStatus, ExitReason
from core.logging import logger

router = APIRouter(prefix="/trading", tags=["trading"])


class TradingStatus(BaseModel):
    running: bool
    mode: str
    is_paper: bool
    is_live: bool
    target_profit_pct: float
    stop_loss_pct: float
    max_positions: int
    cycle_interval_seconds: int = 60


class SwitchModeRequest(BaseModel):
    mode: str


_trading_loop_instance = None


def set_trading_loop(loop):
    global _trading_loop_instance
    _trading_loop_instance = loop


@router.get("/status", response_model=TradingStatus)
async def get_trading_status():
    if not _trading_loop_instance:
        raise HTTPException(status_code=503, detail="Trading loop not initialized")
    return _trading_loop_instance.get_status()


@router.post("/mode")
async def switch_mode(request: SwitchModeRequest):
    if not _trading_loop_instance:
        raise HTTPException(status_code=503, detail="Trading loop not initialized")

    mode = request.mode.lower()
    if mode not in ["paper", "live"]:
        raise HTTPException(status_code=400, detail="Mode must be 'paper' or 'live'")

    _trading_loop_instance.switch_mode(mode)
    return {"message": f"Switched to {mode.upper()} mode", "mode": mode}


@router.post("/start")
async def start_trading():
    if not _trading_loop_instance:
        raise HTTPException(status_code=503, detail="Trading loop not initialized")
    if _trading_loop_instance._running:
        raise HTTPException(status_code=400, detail="Trading loop already running")

    import asyncio
    asyncio.create_task(_trading_loop_instance.start())
    return {"message": "Trading started"}


@router.get("/tier-config")
async def get_tier_config():
    from core.config import get_settings
    s = get_settings()
    return {
        "tiers": [
            {"tier": 1, "trigger_pct": s.tier_1_pct, "qty_pct": s.tier_1_qty_pct, "trailing_sl_offset": s.trailing_sl_tier_1},
            {"tier": 2, "trigger_pct": s.tier_2_pct, "qty_pct": s.tier_2_qty_pct, "trailing_sl_offset": s.trailing_sl_tier_2},
            {"tier": 3, "trigger_pct": s.tier_3_pct, "qty_pct": s.tier_3_qty_pct, "trailing_sl_offset": s.trailing_sl_tier_3},
            {"tier": 4, "trigger_pct": s.tier_4_pct, "qty_pct": s.tier_4_qty_pct, "trailing_sl_offset": None},
        ],
        "ml_exit_min_tier": s.ml_exit_min_tier,
    }


@router.post("/stop")
async def stop_trading():
    if not _trading_loop_instance:
        raise HTTPException(status_code=503, detail="Trading loop not initialized")

    _trading_loop_instance.stop()
    return {"message": "Trading stopped"}
