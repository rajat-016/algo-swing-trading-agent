import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Optional
from backtest_engine.position_manager import PositionManager, Position
import logging

logger = logging.getLogger(__name__)


class TradeSimulator:
    def __init__(
        self,
        initial_capital: float = 100000,
        position_size_pct: float = 0.10,
        max_positions: int = 3,
        stop_loss_pct: float = 0.03,
        target_pct: float = 0.20,
        slippage_pct: float = 0.001,
    ):
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct
        self.slippage_pct = slippage_pct

        self.position_manager = PositionManager(
            max_positions=max_positions,
            stop_loss_pct=stop_loss_pct,
            target_pct=target_pct,
        )

        self.capital = initial_capital
        self.equity_curve: List[float] = []
        self.trade_log: List[Dict] = []
        self.dates: List[datetime] = []

    def run(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        datetime_col: str = "datetime",
    ) -> Dict:
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.sort_values(datetime_col).reset_index(drop=True)

        if len(predictions) != len(df):
            raise ValueError(
                f"Predictions length ({len(predictions)}) must match DataFrame length ({len(df)})"
            )

        logger.info(f"Starting trade simulation: {len(df)} bars, initial capital: {self.capital:.2f}")

        for i in range(len(df)):
            row = df.iloc[i]
            current_date = row[datetime_col]
            current_price = row["close"]
            symbol = row.get("symbol", "UNKNOWN")

            for exited_pos in self.position_manager.update_positions(
                symbol, current_price, current_date
            ):
                self.capital += exited_pos.pnl + (exited_pos.entry_price * exited_pos.quantity)
                self.trade_log.append({
                    "symbol": exited_pos.symbol,
                    "entry_date": exited_pos.entry_date,
                    "exit_date": exited_pos.exit_date,
                    "entry_price": exited_pos.entry_price,
                    "exit_price": exited_pos.exit_price,
                    "quantity": exited_pos.quantity,
                    "pnl": exited_pos.pnl,
                    "pnl_pct": exited_pos.pnl_pct,
                    "exit_reason": exited_pos.exit_reason,
                })

            prediction = int(predictions[i]) if i < len(predictions) else 0

            if prediction == 1 and self.position_manager.can_enter():
                alloc_amount = self.capital * self.position_size_pct
                entry_price = current_price * (1 + self.slippage_pct)
                quantity = int(alloc_amount / entry_price)

                if quantity > 0:
                    position = self.position_manager.enter_position(
                        symbol=symbol,
                        entry_price=entry_price,
                        entry_date=current_date,
                        quantity=quantity,
                    )
                    if position:
                        self.capital -= entry_price * quantity

            open_positions = self.position_manager.get_open_positions()
            open_value = sum(
                p.quantity * current_price for p in open_positions if p.symbol == symbol
            )
            total_equity = self.capital + open_value
            self.equity_curve.append(total_equity)
            self.dates.append(current_date)

        self.position_manager.close_all(
            price_map={row.get("symbol", "UNKNOWN"): row["close"]},
            date=df.iloc[-1][datetime_col],
            reason="END_OF_DATA",
        )

        for exited_pos in self.position_manager.get_all_trades():
            if exited_pos not in self.trade_log:
                self.capital += exited_pos.pnl + (exited_pos.entry_price * exited_pos.quantity)
                self.trade_log.append({
                    "symbol": exited_pos.symbol,
                    "entry_date": exited_pos.entry_date,
                    "exit_date": exited_pos.exit_date,
                    "entry_price": exited_pos.entry_price,
                    "exit_price": exited_pos.exit_price,
                    "quantity": exited_pos.quantity,
                    "pnl": exited_pos.pnl,
                    "pnl_pct": exited_pos.pnl_pct,
                    "exit_reason": exited_pos.exit_reason,
                })

        final_equity = self.capital
        total_return = (final_equity - self.initial_capital) / self.initial_capital

        logger.info(f"Simulation complete: {len(self.trade_log)} trades, "
                     f"Final capital: {final_equity:.2f}, Return: {total_return*100:.2f}%")

        return {
            "initial_capital": self.initial_capital,
            "final_capital": final_equity,
            "total_return": total_return,
            "total_trades": len(self.trade_log),
            "trade_log": self.trade_log,
            "equity_curve": self.equity_curve,
            "dates": [d.isoformat() for d in self.dates],
        }

    def get_results(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_trades": len(self.trade_log),
            "trade_log": self.trade_log,
            "equity_curve": self.equity_curve,
        }
