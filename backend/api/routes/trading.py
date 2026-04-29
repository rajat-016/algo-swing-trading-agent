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


@router.post("/stop")
async def stop_trading():
    if not _trading_loop_instance:
        raise HTTPException(status_code=503, detail="Trading loop not initialized")

    _trading_loop_instance.stop()
    return {"message": "Trading stopped"}
