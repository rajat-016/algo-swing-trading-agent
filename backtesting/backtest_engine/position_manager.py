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
    entry_bar: int = 0
    entry_confidence: float = 0.0  # NEW: confidence score when entered
    exit_price: Optional[float] = None
    exit_date: Optional[datetime] = None
    exit_reason: Optional[str] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    is_open: bool = True

    def check_exit(self, current_price: float, current_date: datetime, current_bar: int = 0, max_holding_bars: int = 7) -> bool:
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

        # NEW: Time-based exit
        if max_holding_bars > 0 and (current_bar - self.entry_bar) >= max_holding_bars:
            self.exit_price = current_price
            self.exit_date = current_date
            self.exit_reason = "TIME_EXIT"
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
        use_atr_sl: bool = True,
        atr_sl_multiplier: float = 2.0,
        atr_target_multiplier: float = 4.0,
        cooldown_bars: int = 3,
        max_holding_bars: int = 7,
    ):
        self.max_positions = max_positions
        self.stop_loss_pct = stop_loss_pct
        self.target_pct = target_pct
        self.use_atr_sl = use_atr_sl
        self.atr_sl_multiplier = atr_sl_multiplier
        self.atr_target_multiplier = atr_target_multiplier
        self.cooldown_bars = cooldown_bars
        self.max_holding_bars = max_holding_bars
        self.positions: List[Position] = []
        self.closed_positions: List[Position] = []
        self._last_exit_bar: int = -999

    def can_enter(self, current_bar: int = 0) -> bool:
        open_count = sum(1 for p in self.positions if p.is_open)
        if open_count >= self.max_positions:
            return False
        if current_bar - self._last_exit_bar < self.cooldown_bars:
            return False
        return True

    def _calculate_sl_target(self, entry_price: float, atr_value: float = None):
        if self.use_atr_sl and atr_value is not None and atr_value > 0:
            stop_loss = entry_price - (atr_value * self.atr_sl_multiplier)
            target = entry_price + (atr_value * self.atr_target_multiplier)
        else:
            stop_loss = entry_price * (1 - self.stop_loss_pct)
            target = entry_price * (1 + self.target_pct)
        return stop_loss, target

    def enter_position(
        self,
        symbol: str,
        entry_price: float,
        entry_date: datetime,
        quantity: int,
        atr_value: float = None,
        entry_bar: int = 0,
        entry_confidence: float = 0.0,  # NEW
    ) -> Optional[Position]:
        if not self.can_enter():
            return None

        stop_loss, target = self._calculate_sl_target(entry_price, atr_value)

        position = Position(
            symbol=symbol,
            entry_price=entry_price,
            entry_date=entry_date,
            quantity=quantity,
            stop_loss=stop_loss,
            target=target,
            entry_bar=entry_bar,
            entry_confidence=entry_confidence,  # NEW
        )

        self.positions.append(position)
        logger.info(
            f"ENTER {symbol} @ {entry_price:.2f} | Qty: {quantity} | SL: {stop_loss:.2f} ({(stop_loss/entry_price-1)*100:.1f}%) | Target: {target:.2f} ({(target/entry_price-1)*100:.1f}%)"
        )
        return position

    def update_positions(self, symbol: str, current_price: float, current_date: datetime, current_bar: int = 0) -> List[Position]:
        exited = []
        for position in self.positions:
            if position.is_open and position.symbol == symbol:
                if position.check_exit(current_price, current_date, current_bar, self.max_holding_bars):
                    exited.append(position)
                    self.closed_positions.append(position)
                    self._last_exit_bar = current_bar
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

    def exit_position(self, symbol: str, exit_price: float, exit_date: datetime, reason: str = "SIGNAL", exit_bar: int = 0) -> Optional[Position]:
        for position in self.positions:
            if position.is_open and position.symbol == symbol:
                position.close(exit_price, exit_date, reason)
                self.closed_positions.append(position)
                self._last_exit_bar = exit_bar
                logger.info(
                    f"EXIT {position.symbol} @ {position.exit_price:.2f} | "
                    f"PnL: {position.pnl:.2f} ({position.pnl_pct*100:.2f}%) | "
                    f"Reason: {position.exit_reason}"
                )
                return position
        return None

    def get_all_trades(self) -> List[Position]:
        return self.closed_positions
