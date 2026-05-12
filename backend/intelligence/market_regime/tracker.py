from datetime import datetime, timezone
from typing import List, Optional, Dict
from collections import deque
from dataclasses import dataclass, field

from intelligence.market_regime.config import RegimeConfig
from intelligence.market_regime.regimes import RegimeType


@dataclass
class RegimeTransition:
    from_regime: str
    to_regime: str
    timestamp: str
    confidence: float
    transition_type: str

    def to_dict(self) -> dict:
        return {
            "from_regime": self.from_regime,
            "to_regime": self.to_regime,
            "timestamp": self.timestamp,
            "confidence": self.confidence,
            "transition_type": self.transition_type,
        }


class RegimeTransitionTracker:
    def __init__(self, config: RegimeConfig):
        self.config = config
        self._history: deque[RegimeTransition] = deque(maxlen=config.max_transition_history)
        self._current_regime: Optional[str] = None

    def record_transition(
        self,
        new_regime: str,
        confidence: float,
        timestamp: Optional[str] = None,
    ) -> Optional[RegimeTransition]:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        if self._current_regime is None:
            transition_type = "initial"
        elif new_regime == self._current_regime:
            transition_type = "no_change"
        else:
            transition_type = "transition"

        old_regime = self._current_regime or "none"
        self._current_regime = new_regime

        transition = RegimeTransition(
            from_regime=old_regime,
            to_regime=new_regime,
            timestamp=timestamp,
            confidence=confidence,
            transition_type=transition_type,
        )

        self._history.append(transition)
        return transition if transition_type != "no_change" else None

    def get_recent_regimes(self, n: Optional[int] = None) -> List[str]:
        if n is None:
            n = self.config.stability_lookback

        transitions_list = list(self._history)
        if not transitions_list:
            return []

        regimes = []
        for t in reversed(transitions_list):
            if t.to_regime not in regimes:
                regimes.append(t.to_regime)
            if len(regimes) >= n:
                break

        regimes.reverse()
        return regimes

    def get_all_regimes(self) -> List[str]:
        return [t.to_regime for t in self._history]

    def get_recent_transitions(self, n: int = 10) -> List[dict]:
        transitions_list = list(self._history)
        return [t.to_dict() for t in transitions_list[-n:]]

    def get_transition_count(self) -> int:
        return sum(1 for t in self._history if t.transition_type == "transition")

    def get_stats(self) -> dict:
        transitions_list = list(self._history)
        if not transitions_list:
            return {
                "current_regime": None,
                "total_transitions": 0,
                "regime_changes": 0,
                "history_length": 0,
            }

        regime_counts: Dict[str, int] = {}
        for t in transitions_list:
            regime_counts[t.to_regime] = regime_counts.get(t.to_regime, 0) + 1

        return {
            "current_regime": self._current_regime,
            "total_transitions": len(transitions_list),
            "regime_changes": self.get_transition_count(),
            "history_length": len(transitions_list),
            "regime_distribution": regime_counts,
        }

    def reset(self):
        self._history.clear()
        self._current_regime = None
