from datetime import datetime
from typing import Optional, Dict, Any
from core.logging import logger


class TradeExecutor:
    def __init__(self, broker, is_live_mode: bool = False):
        self.broker = broker
        self.is_live_mode = is_live_mode

    def place_entry(
        self,
        symbol: str,
        entry_price: float,
        quantity: int,
        stop_loss: float,
        target: float,
    ) -> Dict[str, Any]:
        if self.is_live_mode:
            order = self.broker.place_limit_buy(
                symbol=symbol,
                quantity=quantity,
                price=entry_price,
            )
            order_id = order.order_id if order else None
            logger.info(f"[LIVE] Entry order placed: {symbol} qty={quantity} @ {entry_price}")
        else:
            order_id = f"PAPER_{int(datetime.utcnow().timestamp())}"
            logger.info(f"[PAPER] Entry simulated: {symbol} qty={quantity} @ {entry_price}")

        return {
            "order_id": order_id,
            "symbol": symbol,
            "entry_price": entry_price,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "target": target,
        }

    def place_exit(
        self,
        symbol: str,
        quantity: int,
        exit_price: float,
    ) -> Dict[str, Any]:
        if self.is_live_mode:
            order = self.broker.place_limit_sell(
                symbol=symbol,
                quantity=quantity,
                price=exit_price,
            )
            order_id = order.order_id if order else None
            logger.info(f"[LIVE] Exit order placed: {symbol} qty={quantity} @ {exit_price}")
        else:
            order_id = f"PAPER_{int(datetime.utcnow().timestamp())}"
            logger.info(f"[PAPER] Exit simulated: {symbol} qty={quantity} @ {exit_price}")

        return {
            "order_id": order_id,
            "symbol": symbol,
            "exit_price": exit_price,
            "quantity": quantity,
        }
