import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from backtest_engine.position_manager import PositionManager, Position
from regime.regime_detector import RegimeDetector
import logging

logger = logging.getLogger(__name__)


class TradeSimulator:
    def __init__(
        self,
        initial_capital: float = 100000,
        position_size_pct: float = 0.10,  # Backward compat (not used for sizing)
        max_positions: int = 3,
        stop_loss_pct: float = 0.03,
        target_pct: float = 0.20,
        slippage_pct: float = 0.001,
        brokerage_rate: float = 0.0015,  # 0.15% brokerage
        stt_rate: float = 0.00025,  # 0.025% STT
        use_atr_sl: bool = True,
        atr_sl_multiplier: float = 2.0,
        atr_target_multiplier: float = 4.0,
        cooldown_bars: int = 3,
        max_holding_bars: int = 7,  # Time-based exit: 7 days max
        confidence_high: float = 0.65,
        confidence_medium: float = 0.50,
    ):
        self.initial_capital = initial_capital
        self.position_size_pct = position_size_pct  # Kept for backward compat
        self.slippage_pct = slippage_pct
        self.brokerage_rate = brokerage_rate
        self.stt_rate = stt_rate
        self.confidence_high = confidence_high
        self.confidence_medium = confidence_medium
        self.regime_detector = RegimeDetector()  # NEW
        self.sideways_confidence_boost = 0.05  # Increase threshold in sideways
        self.sideways_size_reduction = 0.5  # Reduce position size in sideways

        self.position_manager = PositionManager(
            max_positions=max_positions,
            stop_loss_pct=stop_loss_pct,
            target_pct=target_pct,
            use_atr_sl=use_atr_sl,
            atr_sl_multiplier=atr_sl_multiplier,
            atr_target_multiplier=atr_target_multiplier,
            cooldown_bars=cooldown_bars,
            max_holding_bars=max_holding_bars,
        )

        self.capital = initial_capital
        self.equity_curve: List[float] = []
        self.trade_log: List[Dict] = []
        self.dates: List[datetime] = []
        self.prediction_log: List[Dict] = []  # Track predictions with confidence

    def run(
        self,
        df: pd.DataFrame,
        predictions: np.ndarray,
        probabilities: np.ndarray = None,  # NEW: shape (n_samples, 3) for SELL/HOLD/BUY
        datetime_col: str = "datetime",
    ) -> Dict:
        df = df.copy()
        df[datetime_col] = pd.to_datetime(df[datetime_col])
        df = df.sort_values(datetime_col).reset_index(drop=True)

        if len(predictions) != len(df):
            raise ValueError(
                f"Predictions length ({len(predictions)}) must match DataFrame length ({len(df)})"
            )
        if probabilities is not None and len(probabilities) != len(df):
            raise ValueError(
                f"Probabilities length ({len(probabilities)}) must match DataFrame length ({len(df)})"
            )

        has_atr = "atr_14" in df.columns

        logger.info(f"Starting trade simulation: {len(df)} bars, initial capital: {self.capital:.2f}")
        if has_atr:
            logger.info("Using ATR-based stop loss/target")

        # Prepare regime detection if features available
        has_regime_features = all(col in df.columns for col in ["ema_50", "ema_200", "atr_14"])

        for i in range(len(df)):
            row = df.iloc[i]
            current_date = row[datetime_col]
            current_price = row["close"]
            symbol = row.get("symbol", "UNKNOWN")
            atr_value = row["atr_14"] if has_atr else None

            # NEW: Detect market regime
            regime = {"trend": "UNKNOWN", "volatility": "NORMAL"}
            if has_regime_features:
                regime = self.regime_detector.detect(df, current_idx=i)

            for exited_pos in self.position_manager.update_positions(
                symbol, current_price, current_date, current_bar=i
            ):
                self._finalize_exit(exited_pos, current_price)

            # NEW: Probability-based decision
            pred_class, confidence = self._get_prediction_with_confidence(
                predictions, probabilities, i
            )

            # NEW: Compute edge score
            edge_score = 0.0
            if pred_class == 2:  # BUY signal
                stop_loss_price = self._calculate_stop_loss(current_price, atr_value)
                target_price = self._calculate_target(current_price, atr_value)
                risk = abs(current_price - stop_loss_price)
                reward = abs(target_price - current_price)
                if risk > 0:
                    edge_score = confidence * (reward / risk)
                else:
                    edge_score = confidence  # Fallback if risk is 0

            # Log prediction for analysis
            self.prediction_log.append({
                "bar": i,
                "symbol": symbol,
                "pred_class": int(pred_class),
                "confidence": float(confidence),
                "edge_score": float(edge_score),
                "price": float(current_price),
                "regime_trend": regime.get("trend", "UNKNOWN"),
                "regime_volatility": regime.get("volatility", "NORMAL"),
            })

            # Entry logic: BUY with confidence gating + regime adjustment
            if pred_class == 2 and self.position_manager.can_enter(current_bar=i):
                # NEW: Regime-based confidence adjustment
                effective_confidence_high = self.confidence_high
                effective_confidence_medium = self.confidence_medium
                
                if regime.get("trend") == "SIDEWAYS":
                    effective_confidence_high += self.sideways_confidence_boost
                    effective_confidence_medium += self.sideways_confidence_boost
                    logger.debug(f"Sideways regime: boosted confidence threshold to {effective_confidence_high:.2f}")

                should_enter = False
                if confidence >= effective_confidence_high:
                    should_enter = True
                elif confidence >= effective_confidence_medium:
                    # Medium confidence fallback (optional)
                    should_enter = True

                if should_enter:
                    entry_price = current_price * (1 + self.slippage_pct)
                    stop_loss_price = self._calculate_stop_loss(entry_price, atr_value)
                    
                    # NEW: Correct position sizing (risk-based)
                    risk_per_trade = self.capital * 0.01  # 1% risk
                    
                    # NEW: Regime-based position size reduction
                    if regime.get("trend") == "SIDEWAYS":
                        risk_per_trade *= self.sideways_size_reduction
                        logger.debug(f"Sideways regime: reduced position size by {self.sideways_size_reduction*100:.0f}%")
                    
                    risk_per_share = abs(entry_price - stop_loss_price)
                    
                    if risk_per_share > 0:
                        quantity = int(risk_per_trade / risk_per_share)
                    else:
                        quantity = int((self.capital * 0.10) / entry_price)  # Fallback

                    if quantity > 0:
                        position = self.position_manager.enter_position(
                            symbol=symbol,
                            entry_price=entry_price,
                            entry_date=current_date,
                            quantity=quantity,
                            atr_value=atr_value,
                            entry_bar=i,
                            entry_confidence=confidence,  # NEW
                        )
                        if position:
                            cost = entry_price * quantity
                            brokerage = cost * self.brokerage_rate
                            stt = cost * self.stt_rate
                            total_cost = cost + brokerage + stt
                            self.capital -= total_cost
                            logger.debug(f"ENTRY {symbol}: cost={cost:.2f}, brokerage={brokerage:.2f}, STT={stt:.2f}")

            # Exit logic: SELL signal
            elif pred_class == 0:
                exit_price = current_price * (1 - self.slippage_pct)
                exited = self.position_manager.exit_position(
                    symbol=symbol,
                    exit_price=exit_price,
                    exit_date=current_date,
                    reason="ML_SELL_SIGNAL",
                    exit_bar=i,
                )
                if exited:
                    self._finalize_exit(exited, exit_price)

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
            already_logged = any(
                t["entry_date"] == exited_pos.entry_date and t["symbol"] == exited_pos.symbol
                for t in self.trade_log
            )
            if not already_logged:
                self._finalize_exit(exited_pos, exited_pos.exit_price)

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
            "prediction_log": self.prediction_log,
        }

    def _get_prediction_with_confidence(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        idx: int,
    ) -> Tuple[int, float]:
        """Extract prediction class and confidence (max probability)."""
        pred_class = int(predictions[idx]) if idx < len(predictions) else 1
        confidence = 0.0
        if probabilities is not None and idx < len(probabilities):
            probs = probabilities[idx]
            confidence = float(np.max(probs))
        return pred_class, confidence

    def _calculate_stop_loss(self, entry_price: float, atr_value: float = None) -> float:
        """Calculate stop loss price using ATR or fixed pct."""
        if self.position_manager.use_atr_sl and atr_value is not None and atr_value > 0:
            return entry_price - (atr_value * self.position_manager.atr_sl_multiplier)
        return entry_price * (1 - self.position_manager.stop_loss_pct)

    def _calculate_target(self, entry_price: float, atr_value: float = None) -> float:
        """Calculate target price using ATR or fixed pct."""
        if self.position_manager.use_atr_sl and atr_value is not None and atr_value > 0:
            return entry_price + (atr_value * self.position_manager.atr_target_multiplier)
        return entry_price * (1 + self.position_manager.target_pct)

    def _finalize_exit(self, position: Position, exit_price: float):
        """Handle capital updates and trade logging with brokerage."""
        cost_basis = position.entry_price * position.quantity
        brokerage = cost_basis * self.brokerage_rate
        stt = (exit_price * position.quantity) * self.stt_rate

        self.capital += position.pnl + cost_basis - brokerage - stt

        self.trade_log.append({
            "symbol": position.symbol,
            "entry_date": position.entry_date,
            "exit_date": position.exit_date,
            "entry_price": position.entry_price,
            "exit_price": position.exit_price,
            "quantity": position.quantity,
            "pnl": position.pnl,
            "pnl_pct": position.pnl_pct,
            "exit_reason": position.exit_reason,
            "brokerage": brokerage,
            "stt": stt,
            "entry_confidence": position.entry_confidence,  # NEW
        })

    def get_results(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "final_capital": self.capital,
            "total_trades": len(self.trade_log),
            "trade_log": self.trade_log,
            "equity_curve": self.equity_curve,
        }
