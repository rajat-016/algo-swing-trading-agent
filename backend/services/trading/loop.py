import asyncio
from datetime import datetime
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from services.broker.zerodha import ZerodhaBroker
from services.broker.chartink import ChartInkClient
from models.stock import Stock, StockStatus, ExitReason
from core.config import get_settings
from core.database import SessionLocal
from core.logging import logger
from core.enums import OrderSide, OrderType, ProductType


def _broadcast_ws(data: dict):
    try:
        from api.routes.websocket import broadcast_update
        asyncio.create_task(broadcast_update(data))
    except Exception:
        pass


class TradingLoop:
    def __init__(
        self,
        broker: ZerodhaBroker,
        chartink: ChartInkClient,
        interval_seconds: int = 300,
    ):
        self.broker = broker
        self.chartink = chartink
        self.settings = get_settings()
        self.interval = interval_seconds
        self._running = False
        self._analyzer = None

    @property
    def analyzer(self):
        if self._analyzer is None:
            from services.ai.analyzer import StockAnalyzer

            model_path = self.settings.model_path if self.settings.model_path else None
            self._analyzer = StockAnalyzer(self.broker, model_path)
        return self._analyzer

    @property
    def is_paper_mode(self) -> bool:
        return self.settings.is_paper_trading

    @property
    def is_live_mode(self) -> bool:
        return self.settings.is_live_trading

    async def start(self):
        self._running = True
        mode = "PAPER" if self.is_paper_mode else "LIVE"
        logger.info(f"Trading loop started ({mode} mode)")

        await self._run_cycle()

        while self._running:
            try:
                await asyncio.sleep(self.interval)
                if self._running:
                    await self._run_cycle()
            except Exception as e:
                logger.error(f"Trading cycle error: {e}")

    async def start_now(self):
        self._running = True
        mode = "PAPER" if self.is_paper_mode else "LIVE"
        logger.info(f"Trading loop started ({mode} mode)")
        await self._run_cycle()

    def stop(self):
        self._running = False
        logger.info("Trading loop stopped")

    async def _run_cycle(self):
        cycle_time = datetime.now().strftime("%H:%M:%S")
        logger.info(f"[{cycle_time}] === Trading Cycle ({self.settings.trading_mode.upper()}) ===")

        if self.is_live_mode and not self.broker.is_connected():
            logger.warning("Broker not connected - skipping cycle")
            return

        db = SessionLocal()
        try:
            cash = self._get_available_cash(db)
            await self._sync_positions_from_broker(db)
            open_positions = self._get_open_positions(db)

            logger.info(f"Open positions: {list(open_positions.keys())}")

            for symbol, pos_data in open_positions.items():
                await self._check_exit(db, symbol, pos_data)

            await self._process_entries(db, cash, open_positions)

        finally:
            db.close()

        logger.info("=== Cycle Complete ===")

    def _get_available_cash(self, db: Session) -> float:
        if self.is_paper_mode:
            logger.info(f"Paper mode: Using simulated capital ₹{self.settings.paper_trading_capital:,.0f}")
            return self.settings.paper_trading_capital

        try:
            margins = self.broker.get_margins()
            if margins:
                available = float(margins.get("available", {}).get("cash", 0))
                logger.info(f"Live mode: Available cash ₹{available:,.0f}")
                return available
        except Exception as e:
            logger.error(f"Error getting funds: {e}")
        return 0

    def _get_open_positions(self, db: Session) -> Dict:
        positions = {}
        stocks = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).all()
        for stock in stocks:
            positions[stock.symbol] = {
                "entry_price": stock.entry_price,
                "quantity": stock.entry_quantity,
                "target": stock.target_price,
                "sl": stock.stop_loss,
                "stock_id": stock.id,
            }
        return positions

    async def _sync_positions_from_broker(self, db: Session):
        if self.is_paper_mode:
            return

        try:
            broker_positions = self.broker.get_positions()
            for pos in broker_positions:
                symbol = pos.get("tradingsymbol", "")
                qty = pos.get("quantity", 0)
                avg_price = pos.get("average_price", 0)

                if qty > 0 and symbol:
                    existing = db.query(Stock).filter(
                        Stock.symbol == symbol,
                        Stock.status == StockStatus.ENTERED
                    ).first()

                    if not existing:
                        new_stock = Stock(
                            symbol=symbol,
                            status=StockStatus.ENTERED,
                            entry_price=avg_price,
                            entry_quantity=qty,
                            target_price=avg_price * (1 + self.settings.target_profit_pct / 100),
                            stop_loss=avg_price * (1 - self.settings.stop_loss_pct / 100),
                            entry_date=datetime.utcnow(),
                            entry_reason="Synced from broker",
                        )
                        db.add(new_stock)
                        db.commit()
                        logger.info(f"Synced position: {symbol}")

        except Exception as e:
            logger.error(f"Error syncing positions: {e}")

    async def _process_entries(self, db: Session, cash: float, open_positions: Dict):
        logger.info(f"Available cash: ₹{cash:,.0f}")

        if cash < 500:
            logger.warning("Insufficient cash")
            return

        if len(open_positions) >= self.settings.max_positions:
            logger.info("Max positions reached")
            return

        try:
            await self.chartink.fetch_stocks()
        except Exception as e:
            logger.error(f"ChartInk fetch error: {e}")
            return

        chartink_symbols = self.chartink.get_symbols()
        if not chartink_symbols:
            logger.warning("No stocks from ChartInk")
            return

        available_slots = self.settings.max_positions - len(open_positions)
        analysis_results = await self.analyzer.analyze_batch(
            chartink_symbols[:20],
            cash / max(available_slots, 1),
        )

        for analysis in analysis_results[:available_slots]:
            if analysis.symbol in open_positions:
                continue

            if analysis.position_size < 1:
                continue

            await self._place_entry(db, analysis)

    async def _place_entry(self, db: Session, analysis: StockAnalysis):
        symbol = analysis.symbol

        if self.is_live_mode:
            order = self.broker.place_order(
                trading_symbol=symbol,
                side=OrderSide.BUY,
                quantity=analysis.position_size,
                order_type=OrderType.LIMIT,
                price=analysis.entry_price,
                product_type=ProductType.CNC,
            )
            broker_order_id = order.order_id if order else None
        else:
            broker_order_id = f"PAPER_{int(datetime.utcnow().timestamp())}"
            logger.info(f"[PAPER] Simulated BUY order: {symbol} | Qty: {analysis.position_size} | Price: ₹{analysis.entry_price:.2f}")

        stock = Stock(
            symbol=symbol,
            status=StockStatus.ENTERED,
            entry_price=analysis.entry_price,
            target_price=analysis.target_price,
            stop_loss=analysis.stop_loss,
            entry_quantity=analysis.position_size,
            entry_date=datetime.utcnow(),
            entry_reason=analysis.reason,
            ai_confidence=analysis.confidence,
            broker_order_id=broker_order_id,
        )
        db.add(stock)
        db.commit()

        _broadcast_ws({
            "type": "entry",
            "symbol": symbol,
            "price": analysis.entry_price,
            "quantity": analysis.position_size,
            "target": analysis.target_price,
            "sl": analysis.stop_loss,
            "reason": analysis.reason,
        })

        mode_prefix = "[PAPER]" if self.is_paper_mode else "[LIVE]"
        logger.info(f"{mode_prefix} ENTRY: {symbol} | Price: ₹{analysis.entry_price:.2f} | Qty: {analysis.position_size} | Target: ₹{analysis.target_price:.2f} | SL: ₹{analysis.stop_loss:.2f}")

    async def _check_exit(self, db: Session, symbol: str, pos_data: Dict):
        if self.is_paper_mode:
            current_price = pos_data["entry_price"] * 1.05
            pnl_pct = 5.0
        else:
            current_price = self.broker.get_ltp(symbol)
            if not current_price:
                return
            entry_price = pos_data["entry_price"]
            pnl_pct = ((current_price - entry_price) / entry_price) * 100

        target = pos_data["target"]
        sl = pos_data["sl"]
        stock_id = pos_data["stock_id"]

        if current_price >= target:
            mode_prefix = "[PAPER]" if self.is_paper_mode else "[LIVE]"
            logger.info(f"{mode_prefix} TARGET HIT: {symbol} | P&L: +{pnl_pct:.2f}%")
            await self._place_exit(db, stock_id, symbol, pos_data, ExitReason.TARGET, current_price)

        elif current_price <= sl:
            mode_prefix = "[PAPER]" if self.is_paper_mode else "[LIVE]"
            logger.info(f"{mode_prefix} STOP LOSS: {symbol} | P&L: {pnl_pct:.2f}%")
            await self._place_exit(db, stock_id, symbol, pos_data, ExitReason.SL, current_price)

        else:
            logger.info(f"HOLDING: {symbol} | Price: ₹{current_price:.2f} | Target: ₹{target:.2f} | SL: ₹{sl:.2f} | P&L: {pnl_pct:+.2f}%")
            _broadcast_ws({
                "type": "price_update",
                "symbol": symbol,
                "current_price": current_price,
                "pnl_pct": pnl_pct,
            })

    async def _place_exit(
        self,
        db: Session,
        stock_id: int,
        symbol: str,
        pos_data: Dict,
        exit_reason: ExitReason,
        exit_price: float,
    ):
        quantity = pos_data["quantity"]
        entry_price = pos_data["entry_price"]

        if self.is_live_mode:
            order = self.broker.place_order(
                trading_symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=OrderType.LIMIT,
                price=exit_price,
                product_type=ProductType.CNC,
            )
            exit_order_id = order.order_id if order else None
        else:
            exit_order_id = f"PAPER_{int(datetime.utcnow().timestamp())}"
            pnl = (exit_price - entry_price) * quantity
            pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            logger.info(f"[PAPER] Simulated SELL order: {symbol} | Qty: {quantity} | Price: ₹{exit_price:.2f} | P&L: ₹{pnl:.2f} ({pnl_pct:.2f}%)")

        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        pnl = 0.0
        if stock:
            stock.status = StockStatus.EXITED
            stock.exit_date = datetime.utcnow()
            stock.exit_reason = exit_reason
            stock.exit_order_id = exit_order_id
            stock.pnl = (exit_price - entry_price) * quantity
            stock.pnl_percentage = ((exit_price - entry_price) / entry_price) * 100
            pnl = stock.pnl
            db.commit()

        _broadcast_ws({
            "type": "exit",
            "symbol": symbol,
            "reason": exit_reason.value,
            "exit_price": exit_price,
            "pnl": pnl,
            "pnl_pct": ((exit_price - entry_price) / entry_price) * 100,
        })

        mode_prefix = "[PAPER]" if self.is_paper_mode else "[LIVE]"
        logger.info(f"{mode_prefix} EXIT: {symbol} | Reason: {exit_reason.value} | P&L: ₹{pnl:.2f}")

    def switch_mode(self, mode: str):
        old_mode = self.settings.trading_mode
        self.settings.trading_mode = mode.lower()
        logger.info(f"Trading mode switched: {old_mode.upper()} -> {mode.upper()}")

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "mode": self.settings.trading_mode,
            "is_paper": self.is_paper_mode,
            "is_live": self.is_live_mode,
            "target_profit_pct": self.settings.target_profit_pct,
            "stop_loss_pct": self.settings.stop_loss_pct,
            "max_positions": self.settings.max_positions,
        }