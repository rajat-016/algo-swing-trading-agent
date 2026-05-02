import numpy as np
from typing import Dict, Optional, Any
from core.logging import logger


class DecisionEngine:
    def __init__(
        self,
        high_confidence_threshold: float = 0.65,
        medium_confidence_threshold: float = 0.50,
        buy_probability_threshold: float = 0.60,
    ):
        self.high_confidence_threshold = high_confidence_threshold
        self.medium_confidence_threshold = medium_confidence_threshold
        self.buy_probability_threshold = buy_probability_threshold

    def decide_entry(self, probs: np.ndarray) -> Dict[str, Any]:
        p_sell = float(probs[0])
        p_hold = float(probs[1])
        p_buy = float(probs[2])

        confidence = float(max(probs))
        predicted_class = int(np.argmax(probs))

        result = {
            "decision": "NO_TRADE",
            "confidence": confidence,
            "p_sell": p_sell,
            "p_hold": p_hold,
            "p_buy": p_buy,
            "predicted_class": predicted_class,
            "reason": "",
        }

        if confidence >= self.high_confidence_threshold:
            if p_buy > self.buy_probability_threshold:
                result["decision"] = "BUY"
                result["reason"] = f"ML HIGH CONF: BUY ({confidence:.0%})"
                return result
            elif p_sell > self.buy_probability_threshold:
                result["decision"] = "SELL"
                result["reason"] = f"ML HIGH CONF: SELL ({confidence:.0%})"
                return result

        elif confidence >= self.medium_confidence_threshold:
            if p_buy > self.buy_probability_threshold:
                if self._fallback_condition(p_buy, p_sell, p_hold):
                    result["decision"] = "BUY"
                    result["reason"] = f"ML MEDIUM CONF: BUY ({confidence:.0%}) + fallback"
                    return result

        if confidence < 0.40:
            result["reason"] = f"ML LOW CONF: NO_TRADE ({confidence:.0%})"
        else:
            result["reason"] = f"ML THRESHOLD NOT MET: NO_TRADE (conf={confidence:.0%}, p_buy={p_buy:.0%})"

        return result

    def _fallback_condition(self, p_buy: float, p_sell: float, p_hold: float) -> bool:
        buy_dominant = p_buy > p_sell and p_buy > p_hold
        buy_margin = p_buy - max(p_sell, p_hold)
        return buy_dominant and buy_margin > 0.10
