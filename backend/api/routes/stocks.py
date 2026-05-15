from typing import List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from core.database import get_db
from models.stock import Stock, StockStatus, ExitReason, ExitLog
from core.logging import logger
from services.broker.kite import get_broker

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


@router.get("/{symbol}/exit-logs")
async def get_stock_exit_logs(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")
    logs = db.query(ExitLog).filter(ExitLog.stock_id == stock.id).order_by(ExitLog.tier).all()
    return {
        "symbol": symbol,
        "exit_logs": [log.to_dict() for log in logs],
        "total": len(logs),
    }


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


@router.put("/{symbol}")
async def update_stock(symbol: str, status: Optional[str] = None, db: Session = Depends(get_db)):
    stock = db.query(Stock).filter(Stock.symbol == symbol).first()
    if not stock:
        raise HTTPException(status_code=404, detail="Stock not found")

    if status:
        try:
            stock.status = StockStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    db.commit()

    return {"message": f"Updated {symbol}", "stock": stock.to_dict()}


@router.get("/summary/portfolio")
async def get_portfolio_summary(db: Session = Depends(get_db)):
    total_stocks = db.query(Stock).count()
    entered = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).count()
    exited = db.query(Stock).filter(Stock.status == StockStatus.EXITED).count()

    exited_stocks = db.query(Stock).filter(Stock.status == StockStatus.EXITED).all()
    
    total_pnl = sum(s.pnl for s in exited_stocks)
    
    total_invested = sum((s.entry_quantity or 0) * (s.entry_price or s.average_price or 0) for s in exited_stocks)
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

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


@router.get("/summary/analytics")
async def get_analytics_summary(db: Session = Depends(get_db)):
    all_stocks = db.query(Stock).order_by(Stock.exit_date.asc()).all()

    exited_stocks = [s for s in all_stocks if s.status == StockStatus.EXITED and s.exit_date and s.pnl is not None]

    equity_curve = []
    cumulative_pnl = 0
    daily_pnl_map = defaultdict(lambda: {"pnl": 0, "count": 0, "wins": 0, "losses": 0})

    for stock in exited_stocks:
        if stock.exit_date:
            date_key = stock.exit_date.date().isoformat()
            cumulative_pnl += stock.pnl or 0
            equity_curve.append({
                "date": date_key,
                "cumulative_pnl": round(cumulative_pnl, 2),
            })
            daily_pnl_map[date_key]["pnl"] += stock.pnl or 0
            daily_pnl_map[date_key]["count"] += 1
            if stock.pnl > 0:
                daily_pnl_map[date_key]["wins"] += 1
            else:
                daily_pnl_map[date_key]["losses"] += 1

    daily_pnl = [
        {
            "date": date,
            "pnl": round(data["pnl"], 2),
            "trades_count": data["count"],
            "wins": data["wins"],
            "losses": data["losses"],
        }
        for date, data in sorted(daily_pnl_map.items())
    ]

    pending = db.query(Stock).filter(Stock.status == StockStatus.PENDING).count()
    open_pos = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).count()
    closed = db.query(Stock).filter(Stock.status == StockStatus.EXITED).count()

    status_distribution = [
        {"name": "Open Positions", "value": open_pos, "color": "#00d4aa"},
        {"name": "Closed", "value": closed, "color": "#6366f1"},
        {"name": "Pending", "value": pending, "color": "#f59e0b"},
    ]

    if exited_stocks:
        pnls = [s.pnl for s in exited_stocks if s.pnl is not None]
        pnls_sorted = sorted(pnls)
        total = sum(pnls)
        winning_trades = len([p for p in pnls if p > 0])
        losing_trades = len([p for p in pnls if p < 0])
        win_rate = (winning_trades / len(pnls) * 100) if pnls else 0
        avg_return = (total / len(pnls)) if pnls else 0

        running_max = 0
        max_drawdown = 0
        peak = 0
        for pnl in pnls_sorted:
            peak += pnl
            if peak > running_max:
                running_max = peak
            drawdown = running_max - peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    else:
        win_rate = 0
        avg_return = 0
        max_drawdown = 0
        winning_trades = 0
        losing_trades = 0

    metrics = {
        "total_trades": len(exited_stocks),
        "win_rate": round(win_rate, 2),
        "avg_return": round(avg_return, 2),
        "max_drawdown": round(max_drawdown, 2),
        "profitable_trades": winning_trades,
        "losing_trades": losing_trades,
    }

    return {
        "equity_curve": equity_curve,
        "daily_pnl": daily_pnl,
        "status_distribution": status_distribution,
        "metrics": metrics,
    }


@router.get("/broker/holdings")
async def get_broker_holdings():
    broker = get_broker()
    if not broker.is_connected():
        raise HTTPException(status_code=503, detail="Broker not connected")

    holdings = broker.get_holdings()
    return {"holdings": holdings, "total": len(holdings)}
