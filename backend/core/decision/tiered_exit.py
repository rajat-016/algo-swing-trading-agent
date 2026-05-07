import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, Tuple
from models.stock import SLBreachSeverity, ExitReason
from core.logging import logger


@dataclass
class TierConfig:
    tier: int
    trigger_pct: float
    qty_pct: float
    trailing_sl_offset: float


@dataclass
class TieredPosition:
    symbol: str
    entry_price: float
    original_quantity: int
    remaining_quantity: int
    stop_loss: float
    target: float
    current_price: float
    current_tier: int
    trailing_sl: Optional[float] = None


class TieredExitEngine:
    def __init__(
        self,
        tier_1_pct: float = 5.0,
        tier_1_qty_pct: float = 25.0,
        tier_2_pct: float = 10.0,
        tier_2_qty_pct: float = 25.0,
        tier_3_pct: float = 15.0,
        tier_3_qty_pct: float = 25.0,
        tier_4_pct: float = 20.0,
        tier_4_qty_pct: float = 25.0,
        trailing_sl_tier_1: float = 0.0,
        trailing_sl_tier_2: float = 3.0,
        trailing_sl_tier_3: float = 7.0,
        ml_sell_threshold: float = 0.65,
        ml_exit_min_tier: int = 2,
        exit_only_profit: bool = False,
    ):
        self.tiers = [
            TierConfig(1, tier_1_pct, tier_1_qty_pct, trailing_sl_tier_1),
            TierConfig(2, tier_2_pct, tier_2_qty_pct, trailing_sl_tier_2),
            TierConfig(3, tier_3_pct, tier_3_qty_pct, trailing_sl_tier_3),
            TierConfig(4, tier_4_pct, tier_4_qty_pct, None),
        ]
        self.ml_sell_threshold = ml_sell_threshold
        self.ml_exit_min_tier = ml_exit_min_tier
        self.exit_only_profit = exit_only_profit

    def decide(
        self,
        probs: Optional[np.ndarray],
        position: TieredPosition,
    ) -> Tuple[str, int, float, ExitReason]:
        pnl_pct = ((position.current_price - position.entry_price) / position.entry_price) * 100

        if self.exit_only_profit and pnl_pct <= 0:
            return ("HOLD", 0, 0.0, ExitReason.MANUAL)

        if position.current_tier <= 4:
            tier = self.tiers[position.current_tier - 1]
            if pnl_pct >= tier.trigger_pct:
                qty = int(position.original_quantity * tier.qty_pct / 100)
                qty = min(qty, position.remaining_quantity)
                if qty <= 0:
                    qty = position.remaining_quantity
                reason_map = {1: ExitReason.TIER_1, 2: ExitReason.TIER_2, 3: ExitReason.TIER_3, 4: ExitReason.TIER_4}
                return ("EXIT_TIER", qty, position.current_price, reason_map[tier.tier])

        if position.current_tier >= self.ml_exit_min_tier and probs is not None:
            p_sell = float(probs[0])
            if p_sell > self.ml_sell_threshold:
                return ("EXIT_ML", position.remaining_quantity, position.current_price, ExitReason.ML_SIGNAL)

        return ("HOLD", 0, 0.0, ExitReason.MANUAL)

    def get_trailing_sl(self, position: TieredPosition) -> Optional[float]:
        if position.current_tier <= 1:
            return None
        tier = self.tiers[position.current_tier - 2]
        if tier.trailing_sl_offset is None:
            return None
        return position.entry_price * (1 + tier.trailing_sl_offset / 100)

    def track_sl_breach(self, position: TieredPosition) -> Dict:
        if position.current_price > position.stop_loss:
            distance_pct = ((position.current_price - position.stop_loss) / position.stop_loss) * 100
            return {
                "status": "SAFE",
                "severity": SLBreachSeverity.SAFE,
                "distance_pct": round(distance_pct, 2),
                "breach_pct": 0.0,
            }

        breach_pct = ((position.stop_loss - position.current_price) / position.stop_loss) * 100

        if breach_pct <= 5:
            severity = SLBreachSeverity.YELLOW
        elif breach_pct <= 15:
            severity = SLBreachSeverity.ORANGE
        elif breach_pct <= 25:
            severity = SLBreachSeverity.RED
        else:
            severity = SLBreachSeverity.CRITICAL

        return {
            "status": "BREACHED",
            "severity": severity,
            "distance_pct": 0.0,
            "breach_pct": round(breach_pct, 2),
        }

    def get_next_tier_info(self, position: TieredPosition) -> Optional[Dict]:
        if position.current_tier > 4:
            return None
        tier = self.tiers[position.current_tier - 1]
        trigger_price = position.entry_price * (1 + tier.trigger_pct / 100)
        return {
            "tier": tier.tier,
            "trigger_pct": tier.trigger_pct,
            "qty_pct": tier.qty_pct,
            "trigger_price": round(trigger_price, 2),
        }
