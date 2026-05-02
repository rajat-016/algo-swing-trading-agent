from core.logging import logger


class PositionSizer:
    def __init__(self, risk_pct: float = 0.01):
        self.risk_pct = risk_pct

    def size(self, capital: float, entry: float, stop_loss: float) -> int:
        risk_amount = capital * self.risk_pct
        risk_per_share = abs(entry - stop_loss)

        if risk_per_share <= 0:
            logger.warning("PositionSizer: entry equals stop_loss, cannot size")
            return 0

        shares = int(risk_amount / risk_per_share)

        if shares <= 0:
            logger.debug(f"PositionSizer: risk_per_share={risk_per_share:.2f} too large for capital={capital:.0f}")
            return 0

        return shares

    def calculate_targets(
        self,
        entry: float,
        stop_loss: float,
        target_multiplier: float = 3.0,
    ) -> tuple:
        risk = abs(entry - stop_loss)
        target = entry + (risk * target_multiplier)
        risk_reward = risk / max(risk, 0.001)
        return target, risk_reward
