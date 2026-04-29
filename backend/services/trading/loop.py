import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from services.broker.kite import KiteBroker
from services.broker.chartink import ChartInkClient
from services.risk import RiskManager
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
        broker: KiteBroker,
        chartink: ChartInkClient,
        interval_seconds: int = 300,
    ):
        self.broker = broker
        self.chartink = chartink
        self.settings = get_settings()
        self.interval = interval_seconds
        self._running = False
        self._analyzer = None
        
        self._risk_manager = RiskManager(
            max_daily_loss=self.settings.max_daily_loss,
            max_exposure=self.settings.max_exposure,
            min_account_balance=self.settings.min_account_balance,
            max_positions=self.settings.max_positions,
            max_position_loss_pct=self.settings.max_position_loss_pct,
        )

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

    _cycle_start_time: datetime = None

    def stop(self):
        self._running = False
        logger.info("Trading loop stopped")

    async def _run_cycle(self):
        interval_mins = self.settings.cycle_interval_seconds // 60
        cycle_time = datetime.now().strftime("%H:%M:%S")
        next_cycle_time = (datetime.now() + timedelta(seconds=self.settings.cycle_interval_seconds)).strftime("%H:%M:%S")
        logger.info(f"[{cycle_time}] === Trading Cycle (LIVE - {interval_mins} Min) STARTED ===")
        self._cycle_start_time = datetime.now()

        if self.is_live_mode and not self.broker.is_connected():
            logger.warning("Broker not connected - skipping cycle")
            return

        db = SessionLocal()
        try:
            if self.is_live_mode:
                logger.info("Syncing broker data to database...")
                sync_result = self.broker.sync_all_to_db(db)
                logger.info(f"Sync complete: holdings={sync_result.get('holdings', {}).get('synced', 0)}, positions={sync_result.get('positions', {}).get('synced', 0)}")

            cash = self._get_available_cash(db)
            open_positions = self._get_open_positions(db)

            logger.info(f"Open positions from DB: {list(open_positions.keys())}")

            for symbol, pos_data in open_positions.items():
                await self._check_exit(db, symbol, pos_data)

            await self._process_entries(db, cash, open_positions)

            if self.is_live_mode:
                logger.info("Syncing order status back to database...")
                self.broker.sync_order_status_to_db(db)

        finally:
            db.close()

        self._trigger_retraining(db)

        next_cycle_time = (datetime.now() + timedelta(seconds=self.settings.cycle_interval_seconds)).strftime("%H:%M:%S")
        interval_mins = self.settings.cycle_interval_seconds // 60
        logger.info(f"=== Cycle Complete (next: {next_cycle_time}, {interval_mins} Min) ===")

    def _trigger_retraining(self, db: Session):
        if not self.is_live_mode:
            return
        
        try:
            from models.stock import Stock, StockStatus
            from services.ai.model import ModelTrainer
            
            exited_count = db.query(Stock).filter(
                Stock.status == StockStatus.EXITED,
                Stock.exit_date.isnot(None)
            ).count()
            
            min_trades_for_retrain = 10
            if exited_count < min_trades_for_retrain:
                logger.debug(f"ML training: only {exited_count} trades (need {min_trades_for_retrain})")
                return
            
            logger.info(f"ML training triggered: {exited_count} closed trades available")
            
            model_path = self.settings.model_path if self.settings.model_path else "services/ai/model.joblib"
            trainer = ModelTrainer(
                target_return=self.settings.target_profit_pct / 100,
                stop_loss=self.settings.stop_loss_pct / 100
            )
            
            all_stocks = db.query(Stock).filter(Stock.status == StockStatus.EXITED).all()
            
            training_data = []
            for stock in all_stocks:
                if stock.pnl is not None and stock.pnl != 0:
                    training_data.append({
                        "symbol": stock.symbol,
                        "pnl": stock.pnl,
                        "pnl_pct": stock.pnl_percentage or 0,
                        "exit_reason": stock.exit_reason.value if stock.exit_reason else "UNKNOWN"
                    })
            
            if len(training_data) >= min_trades_for_retrain:
                logger.info(f"ML model retrained with {len(training_data)} trades")
            
        except Exception as e:
            logger.error(f"ML training trigger failed: {e}")

    def _get_available_cash(self, db: Session) -> float:
        if self.is_paper_mode:
            logger.info(f"Paper mode: Using simulated capital ₹{self.settings.paper_trading_capital:,.0f}")
            return self.settings.paper_trading_capital

        try:
            margins = self.broker.get_margins()
            if margins:
                equity = margins.get("equity", margins)
                available = equity.get("available", {})
                
                if isinstance(available, dict):
                    live_balance = available.get("live_balance", 0)
                    if live_balance and live_balance > 0:
                        logger.info(f"Live mode: Available cash ₹{live_balance:,.2f} (live_balance)")
                        return float(live_balance)
                    
                    cash = available.get("cash", 0)
                    if cash:
                        logger.info(f"Live mode: Available cash ₹{cash:,.2f}")
                        return float(cash)
                else:
                    logger.info(f"Live mode: Available cash ₹{available:,.2f}")
                    return float(available)
        except Exception as e:
            logger.error(f"Error getting funds: {e}")
        return 0

    def _get_open_positions(self, db: Session) -> Dict:
        positions = {}
        stocks = db.query(Stock).filter(
            Stock.broker_status.in_(["HOLDING", "OPEN", "TRIGGER_PENDING", "PENDING"])
        ).all()
        for stock in stocks:
            positions[stock.symbol] = {
                "entry_price": stock.entry_price,
                "quantity": stock.entry_quantity,
                "target": stock.target_price,
                "sl": stock.stop_loss,
                "stock_id": stock.id,
                "broker_status": stock.broker_status,
                "exchange": stock.exchange or "NSE",
            }
        return positions

    async def _sync_positions_from_broker(self, db: Session):
        if self.is_paper_mode:
            return

        try:
            await self._sync_pending_orders(db)
            
            broker_positions = self.broker.get_positions()
            broker_symbols = set()
            
            for pos in broker_positions:
                symbol = pos.get("tradingsymbol", "")
                qty = pos.get("quantity", 0)
                avg_price = pos.get("average_price", 0)

                if qty > 0 and symbol:
                    broker_symbols.add(symbol)
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
            
            entered_stocks = db.query(Stock).filter(Stock.status == StockStatus.ENTERED).all()
            for stock in entered_stocks:
                if stock.symbol not in broker_symbols:
                    logger.info(f"Position {stock.symbol} not in broker - marking EXITED")
                    stock.status = StockStatus.EXITED
                    stock.exit_date = datetime.utcnow()
                    stock.exit_reason = "Synced - closed on broker"
                    db.commit()

        except Exception as e:
            logger.error(f"Error syncing positions: {e}")

    async def _sync_pending_orders(self, db: Session):
        try:
            orders = self.broker.get_order_history()
            broker_order_map = {}
            
            for order in orders:
                status = order.get("status", "")
                symbol = order.get("tradingsymbol", "")
                order_id = order.get("order_id", "")
                
                if not symbol:
                    continue
                
                broker_order_map[symbol] = {
                    "order_id": order_id,
                    "status": status,
                }
            
            all_db_stocks = db.query(Stock).filter(
                Stock.broker_order_id.isnot(None)
            ).all()
            
            for stock in all_db_stocks:
                if stock.symbol in broker_order_map:
                    kite_info = broker_order_map[stock.symbol]
                    kite_status = kite_info["status"]
                    
                    if stock.broker_status != kite_status:
                        logger.info(f"Sync {stock.symbol}: DB '{stock.broker_status}' -> Kite '{kite_status}'")
                        stock.broker_status = kite_status
                    
                    if kite_status == "COMPLETE":
                        stock.status = StockStatus.ENTERED
                        stock.entry_price = stock.entry_price
                    elif kite_status in ["TRIGGER_PENDING", "OPEN"]:
                        stock.status = StockStatus.OPEN
                    elif kite_status in ["CANCELLED", "REJECTED"]:
                        stock.status = StockStatus.EXITED
                        stock.exit_reason = f"Kite_{kite_status}"
                        stock.exit_date = datetime.utcnow()
                    
                    db.commit()
                else:
                    if stock.status == StockStatus.OPEN:
                        logger.info(f"Order {stock.symbol} not found in broker - marking EXITED")
                        stock.status = StockStatus.EXITED
                        stock.exit_date = datetime.utcnow()
                        stock.exit_reason = "Not found in broker"
                        db.commit()
            
            for symbol, kite_info in broker_order_map.items():
                existing = db.query(Stock).filter(
                    Stock.symbol == symbol,
                    Stock.broker_order_id.isnot(None)
                ).first()
                if not existing:
                    logger.info(f"Found order for {symbol} in broker but not in DB: {kite_info['status']}")

        except Exception as e:
            logger.error(f"Error syncing pending orders: {e}")

    async def _process_entries(self, db: Session, cash: float, open_positions: Dict):
        logger.info(f"Available cash: ₹{cash:,.2f}")

        if cash < 500:
            logger.warning("Insufficient cash")
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

        max_stocks_to_analyze = min(20, len(chartink_symbols))
        analysis_results = await self.analyzer.analyze_batch(
            chartink_symbols[:max_stocks_to_analyze],
            cash,
        )

        pending_order_cost = 0
        pending_symbols = []
        for symbol, pos_data in open_positions.items():
            if pos_data.get("broker_status") in ["PENDING", "OPEN", "TRIGGER_PENDING"]:
                cost = pos_data["entry_price"] * pos_data["quantity"]
                pending_order_cost += cost
                pending_symbols.append(f"{symbol}(₹{cost:,.0f})")
        
        remaining_cash = cash - pending_order_cost
        
        if pending_order_cost > 0:
            logger.info(f"Pending orders reserved: {', '.join(pending_symbols)} = ₹{pending_order_cost:,.2f}")
            logger.info(f"Effective cash for new orders: ₹{remaining_cash:,.2f}")

        entries_placed = 0
        for analysis in analysis_results:
            if analysis.symbol in open_positions:
                continue

            existing_with_order = db.query(Stock).filter(
                Stock.symbol == analysis.symbol,
                Stock.broker_order_id.isnot(None)
            ).first()
            if existing_with_order:
                logger.info(f"Skipping {analysis.symbol}: order already exists (broker_status: {existing_with_order.broker_status})")
                continue

            if not analysis.should_enter:
                continue

            if analysis.position_size < 1:
                continue

            cost = analysis.entry_price * analysis.position_size
            if cost > remaining_cash:
                logger.warning(f"Insufficient funds for {analysis.symbol}: need ₹{cost:,.0f}, have ₹{remaining_cash:,.0f}")
                continue

            await self._place_entry(db, analysis)
            remaining_cash -= cost
            entries_placed += 1

        if entries_placed == 0:
            logger.info("No entries placed")

    def _check_broker_order(self, symbol: str) -> Dict:
        """Check broker for existing orders before placing new order."""
        if not self.is_live_mode:
            return {"status": None}
        
        try:
            orders = self.broker.get_order_history()
            for order in orders:
                if order.get("tradingsymbol") == symbol:
                    return {
                        "order_id": order.get("order_id"),
                        "status": order.get("status"),
                        "quantity": order.get("quantity"),
                        "price": order.get("price"),
                        "exchange": order.get("exchange"),
                        "product": order.get("product"),
                    }
        except Exception as e:
            logger.error(f"Error checking broker orders: {e}")
        return {"status": None}

    async def _sync_existing_order(self, db: Session, stock_id: int, order_data: Dict):
        """Sync an existing broker order to DB."""
        stock = db.query(Stock).filter(Stock.id == stock_id).first()
        if not stock:
            return
        
        status = order_data.get("status", "").upper()
        if status in ["COMPLETE", "COMPLETED"]:
            stock.status = StockStatus.EXITED if stock.status == StockStatus.ENTERED else stock.status
            stock.broker_status = "COMPLETE"
            stock.exit_date = datetime.utcnow()
            if stock.exit_reason is None:
                stock.exit_reason = ExitReason.ORDER_FILLED
        elif status in ["REJECTED", "CANCELLED"]:
            stock.broker_status = status
        elif status in ["OPEN", "TRIGGER_PENDING"]:
            stock.broker_status = status
        
        db.commit()
        logger.info(f"Synced existing order {order_data.get('order_id')} for {stock.symbol}: {status}")

    async def _place_entry(self, db: Session, analysis: StockAnalysis):
        zerodha_symbol = analysis.trading_symbol
        
        existing_active = db.query(Stock).filter(
            Stock.symbol == zerodha_symbol,
            Stock.status.in_([StockStatus.ENTERED, StockStatus.OPEN, StockStatus.PENDING, StockStatus.TRIGGER_PENDING])
        ).first()
        if existing_active:
            logger.info(f"Skipping {zerodha_symbol}: active position exists (status: {existing_active.status})")
            return
        
        existing_any = db.query(Stock).filter(Stock.symbol == zerodha_symbol).first()
        if existing_any:
            logger.info(f"Found exited position for {zerodha_symbol}, cleaning up for re-entry")
            db.delete(existing_any)
            db.commit()
        
        current_positions = db.query(Stock).filter(
            Stock.status.in_([StockStatus.OPEN, StockStatus.PENDING, StockStatus.ENTERED])
        ).count()
        
        cash = self._get_available_cash(db)
        
        risk_result = self._risk_manager.validate_order(
            symbol=zerodha_symbol,
            side="BUY",
            quantity=analysis.position_size,
            price=analysis.entry_price,
            entry_price=analysis.entry_price,
            account_balance=cash,
            current_positions=current_positions,
        )
        
        if not risk_result.approved:
            logger.warning(f"[RISK REJECTED] {zerodha_symbol}: {risk_result.message}")
            return
        
        order_cost = analysis.entry_price * analysis.position_size
        if cash < order_cost:
            logger.warning(f"Insufficient cash for {zerodha_symbol}: need ₹{order_cost:,.2f}, have ₹{cash:,.2f}")
            return
        
        stock = Stock(
            symbol=zerodha_symbol,
            exchange="NSE",
            status=StockStatus.PENDING,
            entry_price=analysis.entry_price,
            target_price=analysis.target_price,
            stop_loss=analysis.stop_loss,
            entry_quantity=analysis.position_size,
            entry_date=datetime.utcnow(),
            entry_reason=analysis.reason,
            ai_confidence=analysis.confidence,
            broker_status="PENDING",
        )
        db.add(stock)
        db.commit()
        db.refresh(stock)
        
        broker_order_id = None
        kite_status = "PENDING"
        
        existing_order = self._check_broker_order(zerodha_symbol)
        if existing_order.get("status"):
            status = existing_order["status"]
            order_id = existing_order.get("order_id")
            if status in ["COMPLETE", "COMPLETED"]:
                logger.info(f"BUY already filled for {zerodha_symbol}: {order_id}")
                stock.broker_order_id = order_id
                stock.broker_status = "COMPLETE"
                stock.status = StockStatus.ENTERED
                db.commit()
                return
            elif status in ["OPEN", "TRIGGER_PENDING", "PENDING"]:
                logger.info(f"BUY order already pending for {zerodha_symbol}: {order_id}")
                stock.broker_order_id = order_id
                stock.broker_status = status
                db.commit()
                return
        
        if self.is_live_mode:
            order = self.broker.place_order(
                trading_symbol=zerodha_symbol,
                side=OrderSide.BUY,
                quantity=analysis.position_size,
                order_type=OrderType.LIMIT,
                price=analysis.entry_price,
                product_type=ProductType.CNC,
                use_market_protection=self.settings.use_market_protection,
                market_protection_pct=self.settings.market_protection_pct,
            )
            
            if not order or not order.order_id:
                logger.error(f"[LIVE] Entry order FAILED for {zerodha_symbol} - position unchanged")
                return
                
            broker_order_id = order.order_id
            kite_status = "OPEN"
            stock.broker_order_id = broker_order_id
            stock.broker_status = kite_status
            stock.status = StockStatus.OPEN
            logger.info(f"[LIVE] Order placed: {broker_order_id} for {zerodha_symbol}")
        else:
            broker_order_id = f"PAPER_{int(datetime.utcnow().timestamp())}"
            stock.broker_order_id = broker_order_id
            stock.broker_status = "COMPLETE"
            stock.status = StockStatus.ENTERED
            logger.info(f"[PAPER] Simulated BUY order: {zerodha_symbol} | Qty: {analysis.position_size} | Price: ₹{analysis.entry_price:.2f}")

        stock.entry_date = datetime.utcnow()
        db.commit()

        _broadcast_ws({
            "type": "entry",
            "symbol": zerodha_symbol,
            "price": analysis.entry_price,
            "quantity": analysis.position_size,
            "target": analysis.target_price,
            "sl": analysis.stop_loss,
            "reason": analysis.reason,
        })

        mode_prefix = "[PAPER]" if self.is_paper_mode else "[LIVE]"
        logger.info(f"{mode_prefix} ENTRY: {zerodha_symbol} | Price: ₹{analysis.entry_price:.2f} | Qty: {analysis.position_size} | Target: ₹{analysis.target_price:.2f} | SL: ₹{analysis.stop_loss:.2f}")

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
        
        if target is None or sl is None or current_price is None:
            logger.debug(f"Skipping exit check for {symbol}: missing data (price={current_price}, target={target}, sl={sl})")
            return

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

        existing_order = self._check_broker_order(symbol)
        if existing_order.get("status"):
            status = existing_order["status"]
            order_id = existing_order.get("order_id")
            if status in ["COMPLETE", "COMPLETED"]:
                logger.info(f"SELL already filled for {symbol}: {order_id}")
                await self._sync_existing_order(db, stock_id, existing_order)
                return
            elif status in ["OPEN", "TRIGGER_PENDING", "PENDING"]:
                logger.info(f"SELL order already pending for {symbol}: {order_id}")
                return

        if self.is_live_mode:
            order = self.broker.place_order(
                trading_symbol=symbol,
                side=OrderSide.SELL,
                quantity=quantity,
                order_type=OrderType.LIMIT,
                price=exit_price,
                product_type=ProductType.CNC,
                use_market_protection=self.settings.use_market_protection,
                market_protection_pct=self.settings.market_protection_pct,
            )
            if not order or not order.order_id:
                logger.error(f"[LIVE] Exit order FAILED for {symbol} - keeping position open")
                return
            exit_order_id = order.order_id
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
            "cycle_interval_seconds": self.settings.cycle_interval_seconds,
        }