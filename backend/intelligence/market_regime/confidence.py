import numpy as np
from typing import Dict, List
from intelligence.market_regime.config import RegimeConfig


class ConfidenceScorer:
    def __init__(self, config: RegimeConfig):
        self.config = config

    def compute(
        self,
        regime_signals: Dict[str, float],
        signal_strengths: Dict[str, float],
        recent_regimes: List[str],
    ) -> float:
        if not regime_signals:
            return 0.0

        agreement = self._compute_agreement(regime_signals)
        strength = self._compute_strength(signal_strengths)
        stability = self._compute_stability(recent_regimes)

        confidence = (
            self.config.confidence_signal_agreement_weight * agreement
            + self.config.confidence_signal_strength_weight * strength
            + self.config.confidence_stability_weight * stability
        )

        return float(np.clip(confidence, 0.0, 1.0))

    def _compute_agreement(self, regime_signals: Dict[str, float]) -> float:
        if not regime_signals:
            return 0.0

        total = sum(regime_signals.values())
        if total == 0:
            return 0.0

        max_signal = max(regime_signals.values())
        max_pct = max_signal / total if total > 0 else 0

        num_signals = len(regime_signals)
        if num_signals <= 1:
            return 0.3

        agreement = max_pct
        return float(agreement)

    def _compute_strength(self, signal_strengths: Dict[str, float]) -> float:
        if not signal_strengths:
            return 0.0

        values = [abs(v) for v in signal_strengths.values()]
        avg_strength = np.mean(values) if values else 0

        if avg_strength >= 0.8:
            return 1.0
        elif avg_strength >= 0.6:
            return 0.8
        elif avg_strength >= 0.4:
            return 0.6
        elif avg_strength >= 0.2:
            return 0.4
        else:
            return 0.2

    def _compute_stability(self, recent_regimes: List[str]) -> float:
        if not recent_regimes or len(recent_regimes) < 2:
            return 0.5

        lookback = min(self.config.stability_lookback, len(recent_regimes))
        recent = recent_regimes[-lookback:]

        if len(set(recent)) == 1:
            return 1.0

        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i - 1])
        change_rate = changes / (len(recent) - 1)

        stability = 1.0 - change_rate
        return float(stability)
