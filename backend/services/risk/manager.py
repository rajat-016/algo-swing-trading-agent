from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from enum import Enum

from core.logging import logger


class RiskRejection(Enum):
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"
    INSUFFICIENT_BALANCE = "INSUFFICIENT_BALANCE"
    MAX_POSITIONS = "MAX_POSITIONS"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    RISK_LIMIT = "RISK_LIMIT"
    INSUFFICIENT_MARGIN = "INSUFFICIENT_MARGIN"
    STOP_LOSS_INVALID = "STOP_LOSS_INVALID"
    STOP_LOSS_TOO_WIDE = "STOP_LOSS_TOO_WIDE"


@dataclass
class RiskCheckResult:
    approved: bool
    message: str
    rejection: Optional[RiskRejection] = None
    risk_metrics: dict = field(default_factory=dict)


@dataclass
class RiskMetrics:
    risk_amount: float
    position_value: float
    exposure_pct: float
    risk_per_share: float
    daily_pnl: float
    daily_loss_pct: float
    max_positions: int
    current_positions: int


class RiskManager:
    """
    Risk Manager for trading.
    
    Enforces:
    - Circuit breaker (emergency stop)
    - Daily loss limit
    - Exposure limit per position
    - Stop loss validation
    - Margin check
    """

    def __init__(
        self,
        max_daily_loss: float = 5.0,
        max_exposure: float = 100.0,
        min_account_balance: float = 5000.0,
        max_positions: int = 3,
        max_position_loss_pct: float = 3.0,
    ):
        self.max_daily_loss = max_daily_loss
        self.max_exposure = max_exposure
        self.min_account_balance = min_account_balance
        self.max_positions = max_positions
        self.max_position_loss_pct = max_position_loss_pct

        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._last_reset = datetime.now()
        self._circuit_breaker_triggered = False
        self._available_margin = 0.0
        self._total_exposure = 0.0

        logger.info(f"RiskManager initialized: max_daily_loss={max_daily_loss}%")

    def set_available_margin(self, margin: float) -> None:
        self._available_margin = margin

    def validate_order(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        entry_price: Optional[float] = None,
        account_balance: Optional[float] = None,
        current_positions: int = 0,
        daily_pnl: Optional[float] = None,
    ) -> RiskCheckResult:
        """
        Comprehensive order validation against all risk rules.
        """
        self._check_daily_reset()

        if daily_pnl is not None:
            self._daily_pnl = daily_pnl

        if self._circuit_breaker_triggered:
            return RiskCheckResult(
                approved=False,
                message="Circuit breaker triggered - all trading stopped",
                rejection=RiskRejection.CIRCUIT_BREAKER,
            )

        position_value = quantity * price
        
        risk_metrics = {
            "position_value": position_value,
            "quantity": quantity,
            "price": price,
            "current_positions": current_positions,
            "daily_pnl": self._daily_pnl,
        }

        if account_balance is not None:
            if account_balance < self.min_account_balance:
                return RiskCheckResult(
                    approved=False,
                    message=f"Account balance too low: Rs.{account_balance:,.2f}",
                    rejection=RiskRejection.INSUFFICIENT_BALANCE,
                    risk_metrics=risk_metrics,
                )

            loss_threshold = account_balance * (self.max_daily_loss / 100)
            if self._daily_pnl < -loss_threshold:
                logger.warning(
                    f"Daily loss limit exceeded: PnL=Rs.{self._daily_pnl:,.2f}, "
                    f"limit=Rs.{loss_threshold:,.2f}"
                )
                return RiskCheckResult(
                    approved=False,
                    message=f"Daily loss limit exceeded: Rs.{self._daily_pnl:,.2f}",
                    rejection=RiskRejection.DAILY_LOSS_LIMIT,
                    risk_metrics=risk_metrics,
                )

            single_exposure = position_value / account_balance * 100
            if single_exposure > self.max_exposure:
                return RiskCheckResult(
                    approved=False,
                    message=f"Single position exposure too high: {single_exposure:.1f}% (max: {self.max_exposure}%)",
                    rejection=RiskRejection.EXPOSURE_LIMIT,
                    risk_metrics=risk_metrics,
                )

            if self._total_exposure > 0:
                total_exposure_pct = (self._total_exposure + position_value) / account_balance * 100
                if total_exposure_pct > self.max_exposure * 1.5:
                    return RiskCheckResult(
                        approved=False,
                        message=f"Total exposure too high: {total_exposure_pct:.1f}%",
                        rejection=RiskRejection.EXPOSURE_LIMIT,
                        risk_metrics=risk_metrics,
                    )

        if self._available_margin > 0 and account_balance is not None:
            required_margin = position_value
            if required_margin > self._available_margin:
                return RiskCheckResult(
                    approved=False,
                    message=f"Insufficient margin: need Rs.{required_margin:,.2f}, have Rs.{self._available_margin:,.2f}",
                    rejection=RiskRejection.INSUFFICIENT_MARGIN,
                    risk_metrics=risk_metrics,
                )

        if entry_price is not None and price > 0:
            risk_per_share = abs(entry_price - price)
            risk_pct = (risk_per_share / entry_price) * 100
            
            if risk_pct > self.max_position_loss_pct:
                logger.warning(
                    f"Risk per share too high: {risk_pct:.2f}% (max: {self.max_position_loss_pct}%)"
                )
                return RiskCheckResult(
                    approved=False,
                    message=f"Risk per share too high: {risk_pct:.2f}%",
                    rejection=RiskRejection.RISK_LIMIT,
                    risk_metrics=risk_metrics,
                )

        risk_metrics.update({
            "exposure_pct": (position_value / (account_balance or 1)) * 100,
            "risk_per_share_pct": (abs(entry_price - price) / entry_price * 100) if entry_price else 0,
        })

        logger.info(
            f"Risk check PASSED: {symbol} {side} {quantity} @ Rs.{price:,.2f} "
            f"(value=Rs.{position_value:,.2f})"
        )

        return RiskCheckResult(
            approved=True,
            message="Order approved",
            risk_metrics=risk_metrics,
        )

    def validate_stop_loss(
        self,
        entry_price: float,
        stop_loss: float,
        side: str = "BUY",
    ) -> tuple[bool, str]:
        """
        Validate stop loss price is reasonable.
        
        Returns:
            (is_valid, message)
        """
        if side.upper() == "BUY":
            if stop_loss >= entry_price:
                return False, f"Stop loss must be below entry for BUY: SL=Rs.{stop_loss}, Entry=Rs.{entry_price}"
            loss_pct = ((entry_price - stop_loss) / entry_price) * 100
        else:
            if stop_loss <= entry_price:
                return False, f"Stop loss must be above entry for SELL: SL=Rs.{stop_loss}, Entry=Rs.{entry_price}"
            loss_pct = ((stop_loss - entry_price) / entry_price) * 100

        risk_metrics = {
            "risk_per_share": abs(entry_price - stop_loss),
            "risk_pct": loss_pct,
        }

        if loss_pct > self.max_position_loss_pct * 2:
            return False, f"Stop loss too wide: {loss_pct:.2f}% (max: {self.max_position_loss_pct * 2:.2f}%)"

        return True, "Stop loss valid"

    

    def update_position_value(self, value: float, is_add: bool = True) -> None:
        if is_add:
            self._total_exposure += value
        else:
            self._total_exposure = max(0, self._total_exposure - value)

    def update_daily_pnl(self, pnl: float) -> None:
        self._daily_pnl += pnl
        self._daily_trades += 1
        
        logger.info(f"Daily PnL updated: Rs.{self._daily_pnl:,.2f} (trades: {self._daily_trades})")

    def get_daily_stats(self) -> dict[str, Any]:
        return {
            "daily_pnl": self._daily_pnl,
            "daily_trades": self._daily_trades,
            "total_exposure": self._total_exposure,
            "max_daily_loss": self.max_daily_loss,
            "max_positions": self.max_positions,
            "circuit_breaker": self._circuit_breaker_triggered,
            "loss_threshold_hit": abs(self._daily_pnl) > self.max_daily_loss,
        }

    def trigger_circuit_breaker(self, reason: str = "") -> None:
        self._circuit_breaker_triggered = True
        logger.critical(f"CIRCUIT BREAKER TRIGGERED: {reason}")

    def reset_circuit_breaker(self) -> None:
        self._circuit_breaker_triggered = False
        logger.info("Circuit breaker reset")

    def reset_daily(self) -> None:
        self._daily_pnl = 0.0
        self._daily_trades = 0
        self._last_reset = datetime.now()
        logger.info("Daily stats reset")

    def _check_daily_reset(self) -> None:
        now = datetime.now()
        if now.date() > self._last_reset.date():
            self.reset_daily()

    def get_risk_metrics(
        self,
        account_balance: float,
        current_positions: int,
    ) -> RiskMetrics:
        return RiskMetrics(
            risk_amount=0,
            position_value=0,
            exposure_pct=(self._total_exposure / account_balance * 100) if account_balance > 0 else 0,
            risk_per_share=0,
            daily_pnl=self._daily_pnl,
            daily_loss_pct=(self._daily_pnl / account_balance * 100) if account_balance > 0 else 0,
            max_positions=self.max_positions,
            current_positions=current_positions,
        )
