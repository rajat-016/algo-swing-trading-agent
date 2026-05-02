import numpy as np
from dataclasses import dataclass
from typing import Optional
from core.logging import logger


@dataclass
class Position:
    symbol: str
    entry_price: float
    quantity: int
    stop_loss: float
    target: float
    current_price: float


class ExitEngine:
    def __init__(
        self,
        ml_sell_threshold: float = 0.65,
    ):
        self.ml_sell_threshold = ml_sell_threshold

    def decide(self, probs: Optional[np.ndarray], position: Position) -> str:
        if position.current_price <= position.stop_loss:
            return "EXIT_SL"

        if position.current_price >= position.target:
            return "EXIT_TARGET"

        if probs is not None:
            p_sell = float(probs[0])
            if p_sell > self.ml_sell_threshold:
                return "EXIT_ML"

        return "HOLD"
