from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np
import pandas as pd

from core.logging import logger
from core.config import get_settings


@dataclass
class StrategyMetrics:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0


@dataclass
class StrategyParams:
    name: str
    target_pct: float = 10.0
    stop_loss_pct: float = 3.0
    entry_buffer_pct: float = 0.0
    trailing_stop_pct: float = 0.0
    max_hold_hours: int = 48
    min_confidence: float = 60.0
    use_trailing_stop: bool = False
    use_adaptive_sl: bool = True
    use_optimal_entry: bool = True


@dataclass
class TradeAnalysis:
    symbol: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    exit_reason: str
    holding_hours: float
    pnl_pct: float
    entry_rsi: float
    entry_volatility: float
    features: Dict = field(default_factory=dict)


class StrategyOptimizer:
    """
    Strategy optimizer that learns from trade history.
    
    Responsibilities:
    - Analyze past trades
    - Optimize entry/exit parameters
    - Suggest new strategies
    - Track performance metrics
    """

    def __init__(self):
        self.settings = get_settings()
        self.trade_history: List[TradeAnalysis] = []
        self.strategies: Dict[str, StrategyParams] = {}
        self.current_strategy = StrategyParams(
            name="default",
            target_pct=self.settings.target_profit_pct,
            stop_loss_pct=self.settings.stop_loss_pct,
        )
        self._initialize_default_strategies()

    def _initialize_default_strategies(self) -> None:
        """Initialize default trading strategies."""
        self.strategies = {
            "conservative": StrategyParams(
                name="conservative",
                target_pct=8.0,
                stop_loss_pct=2.0,
                entry_buffer_pct=0.5,
                trailing_stop_pct=1.0,
                max_hold_hours=72,
                min_confidence=70.0,
                use_trailing_stop=True,
            ),
            "moderate": StrategyParams(
                name="moderate",
                target_pct=12.0,
                stop_loss_pct=3.0,
                entry_buffer_pct=0.0,
                trailing_stop_pct=2.0,
                max_hold_hours=48,
                min_confidence=60.0,
                use_trailing_stop=True,
            ),
            "aggressive": StrategyParams(
                name="aggressive",
                target_pct=15.0,
                stop_loss_pct=4.0,
                entry_buffer_pct=-0.5,
                trailing_stop_pct=0.0,
                max_hold_hours=24,
                min_confidence=50.0,
                use_trailing_stop=False,
            ),
        }

    def load_trades_from_db(self, db) -> int:
        """Load historical trades from database."""
        from models.stock import Stock

        try:
            completed_trades = db.query(Stock).filter(
                Stock.status == "EXITED",
                Stock.exit_date.isnot(None),
                Stock.pnl_percentage.isnot(None),
            ).all()

            for trade in completed_trades:
                analysis = TradeAnalysis(
                    symbol=trade.symbol,
                    entry_price=trade.entry_price or 0,
                    exit_price=trade.current_price or trade.entry_price or 0,
                    entry_time=trade.entry_date or datetime.now(),
                    exit_time=trade.exit_date or datetime.now(),
                    exit_reason=trade.exit_reason.value if trade.exit_reason else "UNKNOWN",
                    holding_hours=0,
                    pnl_pct=trade.pnl_percentage or 0,
                    entry_rsi=0,
                    entry_volatility=0,
                )

                if trade.exit_date and trade.entry_date:
                    delta = trade.exit_date - trade.entry_date
                    analysis.holding_hours = delta.total_seconds() / 3600

                self.trade_history.append(analysis)

            logger.info(f"Loaded {len(self.trade_history)} trades from database")
            return len(self.trade_history)

        except Exception as e:
            logger.error(f"Failed to load trades: {e}")
            return 0

    def add_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: float,
        entry_time: datetime,
        exit_time: datetime,
        exit_reason: str,
        entry_rsi: float = 0,
        entry_volatility: float = 0,
        features: Optional[Dict] = None,
    ) -> None:
        """Add a completed trade for analysis."""
        holding_hours = 0
        if exit_time and entry_time:
            delta = exit_time - entry_time
            holding_hours = delta.total_seconds() / 3600

        pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price > 0 else 0

        analysis = TradeAnalysis(
            symbol=symbol,
            entry_price=entry_price,
            exit_price=exit_price,
            entry_time=entry_time,
            exit_time=exit_time,
            exit_reason=exit_reason,
            holding_hours=holding_hours,
            pnl_pct=pnl_pct,
            entry_rsi=entry_rsi,
            entry_volatility=entry_volatility,
            features=features or {},
        )

        self.trade_history.append(analysis)

        if len(self.trade_history) > 500:
            self.trade_history = self.trade_history[-500:]

    def calculate_metrics(self) -> StrategyMetrics:
        """Calculate performance metrics from trade history."""
        if not self.trade_history:
            return StrategyMetrics()

        recent_trades = self.trade_history[-100:]

        wins = [t for t in recent_trades if t.pnl_pct > 0]
        losses = [t for t in recent_trades if t.pnl_pct <= 0]

        total_pnl = sum(t.pnl_pct for t in recent_trades)
        cumulative = 0
        max_drawdown = 0

        for trade in recent_trades:
            cumulative += trade.pnl_pct
            if cumulative < 0:
                max_drawdown = min(max_drawdown, cumulative)

        avg_profit = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = abs(np.mean([t.pnl_pct for t in losses])) if losses else 0

        std_returns = np.std([t.pnl_pct for t in recent_trades]) if len(recent_trades) > 1 else 0
        sharpe = (total_pnl / len(recent_trades)) / std_returns if std_returns > 0 else 0

        return StrategyMetrics(
            total_trades=len(recent_trades),
            wins=len(wins),
            losses=len(losses),
            win_rate=len(wins) / len(recent_trades) * 100 if recent_trades else 0,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=avg_profit / avg_loss if avg_loss > 0 else 0,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
        )

    def analyze_exit_reasons(self) -> Dict[str, Dict]:
        """Analyze performance by exit reason."""
        reasons = {}

        for trade in self.trade_history:
            reason = trade.exit_reason
            if reason not in reasons:
                reasons[reason] = {"count": 0, "total_pnl": 0, "wins": 0}

            reasons[reason]["count"] += 1
            reasons[reason]["total_pnl"] += trade.pnl_pct
            if trade.pnl_pct > 0:
                reasons[reason]["wins"] += 1

        for reason, data in reasons.items():
            data["win_rate"] = data["wins"] / data["count"] * 100 if data["count"] > 0 else 0
            data["avg_pnl"] = data["total_pnl"] / data["count"] if data["count"] > 0 else 0

        return reasons

    def analyze_entry_conditions(self) -> Dict:
        """Analyze which entry conditions perform best."""
        conditions = {
            "low_rsi": {"count": 0, "total_pnl": 0},
            "high_rsi": {"count": 0, "total_pnl": 0},
            "low_volatility": {"count": 0, "total_pnl": 0},
            "high_volatility": {"count": 0, "total_pnl": 0},
            "short_hold": {"count": 0, "total_pnl": 0},
            "long_hold": {"count": 0, "total_pnl": 0},
        }

        for trade in self.trade_history:
            if trade.entry_rsi > 0:
                if trade.entry_rsi < 40:
                    conditions["low_rsi"]["count"] += 1
                    conditions["low_rsi"]["total_pnl"] += trade.pnl_pct
                elif trade.entry_rsi > 60:
                    conditions["high_rsi"]["count"] += 1
                    conditions["high_rsi"]["total_pnl"] += trade.pnl_pct

            if trade.entry_volatility > 0:
                if trade.entry_volatility < 0.02:
                    conditions["low_volatility"]["count"] += 1
                    conditions["low_volatility"]["total_pnl"] += trade.pnl_pct
                elif trade.entry_volatility > 0.04:
                    conditions["high_volatility"]["count"] += 1
                    conditions["high_volatility"]["total_pnl"] += trade.pnl_pct

            if trade.holding_hours > 0:
                if trade.holding_hours < 24:
                    conditions["short_hold"]["count"] += 1
                    conditions["short_hold"]["total_pnl"] += trade.pnl_pct
                elif trade.holding_hours > 48:
                    conditions["long_hold"]["count"] += 1
                    conditions["long_hold"]["total_pnl"] += trade.pnl_pct

        for cond, data in conditions.items():
            if data["count"] > 0:
                data["avg_pnl"] = data["total_pnl"] / data["count"]
            else:
                data["avg_pnl"] = 0

        return conditions

    def suggest_optimizations(self) -> List[str]:
        """Suggest optimizations based on trade analysis."""
        suggestions = []
        metrics = self.calculate_metrics()
        reasons = self.analyze_exit_reasons()
        conditions = self.analyze_entry_conditions()

        if metrics.win_rate < 40:
            suggestions.append("Win rate low - consider widening stop loss or tightening entry criteria")

        if metrics.profit_factor < 1.5:
            suggestions.append("Profit factor low - review target levels, consider taking partial profits")

        if "TARGET" in reasons:
            target_metrics = reasons["TARGET"]
            if target_metrics["win_rate"] > 70:
                suggestions.append("Good target hit rate - targets are well calibrated")

        if conditions["low_rsi"]["avg_pnl"] > conditions["high_rsi"]["avg_pnl"]:
            suggestions.append("Better results at low RSI - tighten entry to RSI < 40")

        if conditions["short_hold"]["avg_pnl"] > conditions["long_hold"]["avg_pnl"]:
            suggestions.append("Short holds perform better - reduce max hold time")

        if conditions["low_volatility"]["avg_pnl"] > conditions["high_volatility"]["avg_pnl"]:
            suggestions.append("Better results in low volatility - add volatility filter")

        avg_holding = np.mean([t.holding_hours for t in self.trade_history]) if self.trade_history else 0
        if avg_holding > 40:
            suggestions.append(f"Average hold time high ({avg_holding:.1f}h) - targets may be too aggressive")

        return suggestions

    def optimize_strategy(self) -> StrategyParams:
        """Optimize strategy based on historical performance."""
        metrics = self.calculate_metrics()
        reasons = self.analyze_exit_reasons()
        conditions = self.analyze_entry_conditions()

        optimized = StrategyParams(
            name="optimized",
            target_pct=self.current_strategy.target_pct,
            stop_loss_pct=self.current_strategy.stop_loss_pct,
            entry_buffer_pct=self.current_strategy.entry_buffer_pct,
            trailing_stop_pct=self.current_strategy.trailing_stop_pct,
            max_hold_hours=self.current_strategy.max_hold_hours,
            min_confidence=self.current_strategy.min_confidence,
        )

        if len(self.trade_history) >= 20:
            avg_pnl = metrics.avg_profit
            if metrics.win_rate > 55 and avg_pnl > 5:
                optimized.target_pct = min(optimized.target_pct * 1.1, 15.0)
            elif metrics.win_rate < 45 or avg_pnl < 3:
                optimized.target_pct = max(optimized.target_pct * 0.9, 6.0)

            if "SL" in reasons and reasons["SL"]["win_rate"] < 30:
                optimized.stop_loss_pct = min(optimized.stop_loss_pct * 1.2, 5.0)

            if conditions["short_hold"]["avg_pnl"] > conditions["long_hold"]["avg_pnl"]:
                optimized.max_hold_hours = int(optimized.max_hold_hours * 0.8)

            if conditions["low_rsi"]["avg_pnl"] > conditions["high_rsi"]["avg_pnl"]:
                optimized.entry_buffer_pct = -0.5
                optimized.min_confidence = max(optimized.min_confidence, 65)

            optimized.use_trailing_stop = metrics.max_drawdown < -5
            optimized.use_adaptive_sl = metrics.win_rate < 50

        logger.info(f"Strategy optimized: target={optimized.target_pct}%, SL={optimized.stop_loss_pct}%")
        return optimized

    def get_best_strategy(self) -> StrategyParams:
        """Get best performing strategy based on metrics."""
        metrics = self.calculate_metrics()

        if metrics.win_rate >= 60 and metrics.profit_factor >= 2.0:
            return self.strategies.get("conservative", self.current_strategy)
        elif metrics.win_rate >= 50 and metrics.profit_factor >= 1.5:
            return self.strategies.get("moderate", self.current_strategy)
        else:
            return self.strategies.get("aggressive", self.current_strategy)

    def get_full_report(self) -> Dict:
        """Get complete strategy analysis report."""
        return {
            "metrics": {
                "total_trades": len(self.trade_history),
                **vars(self.calculate_metrics()),
            },
            "exit_reasons": self.analyze_exit_reasons(),
            "entry_conditions": self.analyze_entry_conditions(),
            "suggestions": self.suggest_optimizations(),
            "optimized_strategy": {
                "target_pct": self.optimize_strategy().target_pct,
                "stop_loss_pct": self.optimize_strategy().stop_loss_pct,
                "max_hold_hours": self.optimize_strategy().max_hold_hours,
                "entry_buffer_pct": self.optimize_strategy().entry_buffer_pct,
            },
            "current_strategy": {
                "target_pct": self.current_strategy.target_pct,
                "stop_loss_pct": self.current_strategy.stop_loss_pct,
            },
        }