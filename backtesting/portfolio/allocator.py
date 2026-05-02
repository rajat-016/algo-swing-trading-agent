"""
Portfolio Allocation Module

Allocates capital across multiple signals using configurable strategies.
Designed to be modular for future strategies (Kelly, Risk Parity, etc.)
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PortfolioAllocator:
    """
    Allocates capital across trading signals.
    
    Strategies:
    - equal: Equal weight across top N signals
    - confidence_proportional: Allocate proportional to confidence scores
    - edge_score: Allocate proportional to edge score (confidence * reward/risk)
    """

    def __init__(
        self,
        max_positions: int = 5,
        max_capital_pct_per_trade: float = 0.20,
        strategy: str = "edge_score",
        min_edge_score: float = 0.5,  # NEW: filter weak signals
    ):
        self.max_positions = max_positions
        self.max_capital_pct_per_trade = max_capital_pct_per_trade
        self.strategy = strategy
        self.min_edge_score = min_edge_score  # NEW

    def allocate(
        self,
        signals: List[Dict],
        available_capital: float,
    ) -> List[Dict]:
        """
        Allocate capital across signals.
        
        Args:
            signals: List of signal dicts with keys:
                - symbol: str
                - prediction: int (2 = BUY)
                - confidence: float (0.0 to 1.0)
                - edge_score: float (optional, used for ranking if available)
            available_capital: Total capital available for allocation
            
        Returns:
            List of allocation dicts with keys:
                - symbol: str
                - allocated_capital: float
                - weight: float (fraction of total capital)
                - edge_score: float
        """
        if not signals or available_capital <= 0:
            return []

        buy_signals = [s for s in signals if s.get("prediction") == 2]

        if not buy_signals:
            logger.debug("No BUY signals to allocate")
            return []

        if self.strategy == "equal":
            allocations = self._allocate_equal(buy_signals, available_capital)
        elif self.strategy == "confidence_proportional":
            allocations = self._allocate_confidence_proportional(buy_signals, available_capital)
        elif self.strategy == "edge_score":
            allocations = self._allocate_edge_score(buy_signals, available_capital)
        else:
            logger.warning(f"Unknown strategy '{self.strategy}', falling back to confidence_proportional")
            allocations = self._allocate_confidence_proportional(buy_signals, available_capital)

        logger.info(
            f"Allocated {len(allocations)} positions, "
            f"total allocated: {sum(a['allocated_capital'] for a in allocations):.2f}"
        )
        return allocations

    def _allocate_equal(
        self,
        signals: List[Dict],
        capital: float,
    ) -> List[Dict]:
        """Equal weight allocation across top N signals by confidence."""
        sorted_signals = sorted(
            signals,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )[:self.max_positions]

        n = len(sorted_signals)
        if n == 0:
            return []

        max_per_trade = capital * self.max_capital_pct_per_trade
        equal_share = capital / n

        allocations = []
        for sig in sorted_signals:
            alloc = min(equal_share, max_per_trade)
            weight = alloc / capital
            allocations.append({
                "symbol": sig["symbol"],
                "allocated_capital": alloc,
                "weight": weight,
                "confidence": sig.get("confidence", 0),
            })

        return allocations

    def _allocate_edge_score(
        self,
        signals: List[Dict],
        capital: float,
    ) -> List[Dict]:
        """Allocate proportional to edge_score, capped at max per trade. Filters weak signals."""
        # Filter signals with valid edge scores AND above minimum threshold
        valid_signals = [
            s for s in signals
            if s.get("edge_score", 0) > self.min_edge_score
        ]
        
        if not valid_signals:
            logger.warning(
                f"No signals with edge_score > {self.min_edge_score:.2f}, "
                f"falling back to confidence_proportional"
            )
            return self._allocate_confidence_proportional(signals, capital)

        sorted_signals = sorted(
            valid_signals,
            key=lambda x: x.get("edge_score", 0),
            reverse=True
        )[:self.max_positions]

        total_edge = sum(s.get("edge_score", 0) for s in sorted_signals)
        if total_edge <= 0:
            return []

        max_per_trade = capital * self.max_capital_pct_per_trade

        allocations = []
        for sig in sorted_signals:
            edge = sig.get("edge_score", 0)
            raw_alloc = (edge / total_edge) * capital
            alloc = min(raw_alloc, max_per_trade)
            weight = alloc / capital
            allocations.append({
                "symbol": sig["symbol"],
                "allocated_capital": alloc,
                "weight": weight,
                "confidence": sig.get("confidence", 0),
                "edge_score": edge,
            })

        logger.info(
            f"Edge score allocation: {len(allocations)} signals "
            f"(filtered {len(signals) - len(valid_signals)} weak signals)"
        )
        return allocations

    def _allocate_confidence_proportional(
        self,
        signals: List[Dict],
        capital: float,
    ) -> List[Dict]:
        """Allocate proportional to confidence scores, capped at max per trade."""
        sorted_signals = sorted(
            signals,
            key=lambda x: x.get("confidence", 0),
            reverse=True
        )[:self.max_positions]

        total_confidence = sum(s.get("confidence", 0) for s in sorted_signals)
        if total_confidence <= 0:
            return []

        max_per_trade = capital * self.max_capital_pct_per_trade

        allocations = []
        for sig in sorted_signals:
            confidence = sig.get("confidence", 0)
            raw_alloc = (confidence / total_confidence) * capital
            alloc = min(raw_alloc, max_per_trade)
            weight = alloc / capital
            allocations.append({
                "symbol": sig["symbol"],
                "allocated_capital": alloc,
                "weight": weight,
                "confidence": confidence,
            })

        return allocations


class PortfolioSimulator:
    """
    Simulates portfolio-level trading with allocation.
    Wraps the existing TradeSimulator to handle multiple positions per bar.
    """

    def __init__(
        self,
        initial_capital: float = 100000,
        max_positions: int = 5,
        stop_loss_pct: float = 0.03,
        target_pct: float = 0.15,
        slippage_pct: float = 0.001,
        brokerage_rate: float = 0.0015,
        stt_rate: float = 0.00025,
        use_atr_sl: bool = True,
        atr_sl_multiplier: float = 2.0,
        atr_target_multiplier: float = 4.0,
        cooldown_bars: int = 3,
        max_holding_bars: int = 7,
        confidence_high: float = 0.65,
        confidence_medium: float = 0.50,
        allocation_strategy: str = "confidence_proportional",
    ):
        from backtest_engine.trade_simulator import TradeSimulator

        self.allocator = PortfolioAllocator(
            max_positions=max_positions,
            max_capital_pct_per_trade=0.20,
            strategy=allocation_strategy,
        )

        self.simulator = TradeSimulator(
            initial_capital=initial_capital,
            position_size_pct=1.0,  # Not used directly
            max_positions=max_positions,
            stop_loss_pct=stop_loss_pct,
            target_pct=target_pct,
            slippage_pct=slippage_pct,
            brokerage_rate=brokerage_rate,
            stt_rate=stt_rate,
            use_atr_sl=use_atr_sl,
            atr_sl_multiplier=atr_sl_multiplier,
            atr_target_multiplier=atr_target_multiplier,
            cooldown_bars=cooldown_bars,
            max_holding_bars=max_holding_bars,
            confidence_high=confidence_high,
            confidence_medium=confidence_medium,
        )

        self.confidence_high = confidence_high
        self.confidence_medium = confidence_medium

    def run(
        self,
        df: object,
        predictions: object,
        probabilities: object = None,
        datetime_col: str = "datetime",
    ) -> Dict:
        """
        Run simulation with portfolio-level allocation.
        
        Note: This is a simplified version that processes signals per bar.
        For full portfolio simulation, consider processing all signals for a bar
        before executing trades.
        """
        return self.simulator.run(df, predictions, probabilities, datetime_col)

    def get_results(self) -> Dict:
        return self.simulator.get_results()
