from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.stock import Stock, StockStatus, ExitReason
from core.logging import logger

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/")
async def get_stocks(db: Session = Depends(get_db)):
    stocks = db.query(Stock).order_by(Stock.created_at.desc()).all()
    return {
        "stocks": [stock.to_dict() for stock in stocks],
        "total": len(stocks),
    }


@router.get("/{symbol}")
async def get_stock(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    return stock.to_dict()


@router.get("/status/{status}")
async def get_stocks_by_status(status: str, db: Session = Depends(get_db)):
    try:
        stock_status = StockStatus(status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")

    stocks = db.query(Stock).filter(Stock.status == stock_status).all()
    return {
        "stocks": [stock.to_dict() for stock in stocks],
        "total": len(stocks),
    }


@router.get("/analysis/pending")
async def get_pending_analysis(db: Session = Depends(get_db)):
    stocks = db.query(Stock).filter(Stock.status == StockStatus.PENDING).all()
    return {
        "stocks": [stock.to_dict() for stock in stocks],
        "total": len(stocks),
    }


@router.post("/{symbol}/exit")
async def exit_stock(symbol: str, reason: str = "MANUAL", db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(
        Stock.symbol == symbol,
        Stock.status == StockStatus.ENTERED
    ).first()

    if not stock:
        raise HTTPException(status_code=404, detail="No open position found")

    try:
        exit_reason = ExitReason(reason)
    except ValueError:
        exit_reason = ExitReason.MANUAL

    stock.status = StockStatus.EXITED
    stock.exit_date = datetime.utcnow()
    stock.exit_reason = exit_reason
    db.commit()

    return {"message": f"Exited {symbol}", "stock": stock.to_dict()}


@router.get("/summary/portfolio")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    total_stocks = db.query(Stock).count()
    entered = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).count()
    exited = db.query(Stock).filter(Stock.status == StockStatus.EXITED).count()

    exited_stocks = db.query(Stock).filter(Stock.status == StockStatus.EXITED).all()
    total_pnl = sum(s.pnl for s in exited_stocks)
    total_pnl_pct = sum(s.pnl_percentage for s in exited_stocks) / len(exited_stocks) if exited_stocks else 0

    winning_trades = len([s for s in exited_stocks if s.pnl > 0])
    win_rate = (winning_trades / len(exited_stocks) * 100) if exited_stocks else 0

    return {
        "total_trades": total_stocks,
        "open_positions": entered,
        "closed_positions": exited,
        "total_pnl": total_pnl,
        "avg_pnl_percentage": total_pnl_pct,
        "win_rate": win_rate,
    }
