from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class Position:
    symbol: str
    entry_price: float
    entry_date: datetime
    quantity: int
    stop_loss: float
    target: float
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    is_open: bool = True

    def check_exit(self, current_price: float, current_date: datetime) -> bool:
        if not self.is_open:
            return False

        if current_price <= self.stop_loss:
            self.exit_price = current_price
            self.exit_date = current_date
            self.exit_reason = "STOP_LOSS"
            self._calculate_pnl()
            self.is_open = False
            return True

        if current_price >= self.target:
            self.exit_price = current_price
            self.exit_date = current_date
            self.exit_reason = "TARGET"
            self._calculate_pnl()
            self.is_open = False
            return True

        return False

    def close(self, price: float, date: datetime, reason: str = "MANUAL"):
        self.exit_price = price
        self.exit_date = date
        self.exit_reason = reason
        self._calculate_pnl()
        self.is_open = False

    def _calculate_pnl(self):
        if self.exit_price is None:
            return
        self.pnl = (self.exit_price - self.entry_price) * self.quantity
        self.pnl_pct = (self.exit_price - self.entry_price) / self.entry_price


class PositionManager:
    def __init__(
        self,
        max_positions: int = 3,
        stop_loss_pct: float = 0.03,
        target_pct: float = 0.20,
    ):
        self.max_positions = max_positions
        self.stop_loss_pct = stop_loss_pct
        self.target_pct = target_pct
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []

    def can_enter(self) -> bool:
        open_count = sum(1 for p in self.positions if p.is_open)
        return open_count < self.max_positions

    def enter_position(
        self,
        symbol: str,
        entry_price: float,
        entry_date: datetime,
        quantity: int,
    ) -> Optional[Position]:
        if not self.can_enter():
            return None

        stop_loss = entry_price * (1 - self.stop_loss_pct)
        target = entry_price * (1 + self.target_pct)

        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=entry_date,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
        )

        self.positions.append(position)
        logger.info(
            f"ENTER {symbol} @ {entry_price:.2f} | Qty: {quantity} | SL: {stop_loss:.2f} | Target: {target:.2f}"
        )
        return position

    def update_positions(self, symbol: str, current_price: float, current_date: datetime) -> List[Position]:
        exited = []
        for position in self.positions:
            if position.is_open and position.symbol == symbol:
                if position.check_exit(current_price, current_date):
                    exited.append(position)
                    self.closed_positions.append(position)
                    logger.info(
                        f"EXIT {position.symbol} @ {position.exit_price:.2f} | "
                        f"PnL: {position.pnl:.2f} ({position.pnl_pct*100:.2f}%) | "
                        f"Reason: {position.exit_reason}"
                    )
        return exited

    def close_all(self, price_map: dict, date: datetime, reason: str = "END"):
        for position in self.positions:
            if position.is_open:
                exit_price = price_map.get(position.symbol, position.entry_price)
                position.close(exit_price, date, reason)
                self.closed_positions.append(position)

    def get_open_positions(self) -> List[Position]:
        return [p for p in self.positions if p.is_open]

    def get_all_trades(self) -> List[Position]:
        return self.closed_positions
