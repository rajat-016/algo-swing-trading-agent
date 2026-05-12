from collections import deque, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from loguru import logger

from intelligence.market_regime.config import RegimeConfig


TRANSITION_DETECTOR_VERSION = "1.0.0"

TRANSITION_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS regime_transition_log (
    id INTEGER PRIMARY KEY,
    current_regime VARCHAR NOT NULL,
    previous_regime VARCHAR,
    transition_probability DOUBLE,
    regime_persistence_bars INTEGER,
    avg_regime_duration DOUBLE,
    volatility_spike_score DOUBLE,
    vol_spike_detected BOOLEAN,
    confidence_current DOUBLE,
    confidence_previous DOUBLE,
    confidence_degradation DOUBLE,
    confidence_degraded BOOLEAN,
    transition_alert VARCHAR,
    markov_next_regime VARCHAR,
    markov_next_probability DOUBLE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

TRANSITION_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_transition_log_created
ON regime_transition_log(created_at DESC);
"""


@dataclass
class TransitionDetectorOutput:
    transition_probability_matrix: Dict[str, Dict[str, float]] = field(default_factory=dict)
    current_transition_probability: float = 0.0
    most_likely_next_regime: Optional[str] = None
    most_likely_next_probability: float = 0.0
    regime_persistence_bars: int = 0
    avg_regime_duration: float = 0.0
    persistence_ratio: float = 0.0
    persistence_alert: Optional[str] = None
    volatility_spike_score: float = 0.0
    vol_spike_detected: bool = False
    vol_spike_severity: str = "none"
    confidence_degradation: float = 0.0
    confidence_degraded: bool = False
    confidence_trend: str = "stable"
    transition_alert: Optional[str] = None
    is_unstable: bool = False
    is_transitioning: bool = False


class TransitionDetector:
    def __init__(self, config: RegimeConfig):
        self.config = config
        self._regime_history: deque[str] = deque(maxlen=config.max_transition_history)
        self._confidence_history: deque[float] = deque(maxlen=config.max_transition_history)
        self._timestamps: deque[str] = deque(maxlen=config.max_transition_history)
        self._transition_matrix: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._regime_durations: Dict[str, List[int]] = defaultdict(list)
        self._current_regime_start: Optional[str] = None
        self._current_regime_bar: int = 0

    def record(
        self,
        regime: str,
        confidence: float,
        timestamp: Optional[str] = None,
    ) -> Optional[TransitionDetectorOutput]:
        ts = timestamp or datetime.now(timezone.utc).isoformat()

        previous_regime = self._regime_history[-1] if self._regime_history else None

        self._regime_history.append(regime)
        self._confidence_history.append(confidence)
        self._timestamps.append(ts)

        if previous_regime is not None:
            self._transition_matrix[previous_regime][regime] += 1

        if regime != previous_regime:
            if previous_regime is not None and self._current_regime_start is not None:
                if previous_regime in self._regime_durations:
                    self._regime_durations[previous_regime].append(self._current_regime_bar)
            self._current_regime_start = regime
            self._current_regime_bar = 1
        else:
            self._current_regime_bar += 1

        return self.compute()

    def compute(self) -> TransitionDetectorOutput:
        current_regime = self._regime_history[-1] if self._regime_history else None

        prob_matrix = self._compute_transition_probability_matrix()
        transition_prob, next_regime, next_prob = self._get_most_likely_transition(current_regime, prob_matrix)

        persistence_bars = self._current_regime_bar
        avg_duration = self._get_avg_duration(current_regime)
        persistence_ratio = persistence_bars / max(avg_duration, 1)
        persistence_alert = self._check_persistence_alert(persistence_ratio, persistence_bars, avg_duration)

        spike_score, spike_detected, spike_severity = self._detect_volatility_spike()

        confidence_degradation, confidence_degraded, confidence_trend = (
            self._check_confidence_degradation()
        )

        is_unstable, is_transitioning, transition_alert = self._assess_stability(
            transition_prob, spike_score, spike_detected, confidence_degraded, persistence_ratio
        )

        return TransitionDetectorOutput(
            transition_probability_matrix=prob_matrix,
            current_transition_probability=transition_prob,
            most_likely_next_regime=next_regime,
            most_likely_next_probability=next_prob,
            regime_persistence_bars=persistence_bars,
            avg_regime_duration=round(avg_duration, 2),
            persistence_ratio=round(persistence_ratio, 4),
            persistence_alert=persistence_alert,
            volatility_spike_score=round(spike_score, 6),
            vol_spike_detected=spike_detected,
            vol_spike_severity=spike_severity,
            confidence_degradation=round(confidence_degradation, 4),
            confidence_degraded=confidence_degraded,
            confidence_trend=confidence_trend,
            transition_alert=transition_alert,
            is_unstable=is_unstable,
            is_transitioning=is_transitioning,
        )

    def _compute_transition_probability_matrix(self) -> Dict[str, Dict[str, float]]:
        matrix: Dict[str, Dict[str, float]] = {}
        for from_regime, targets in self._transition_matrix.items():
            total = sum(targets.values())
            if total > 0:
                matrix[from_regime] = {
                    to: round(count / total, 4) for to, count in sorted(targets.items(), key=lambda x: -x[1])
                }
        return matrix

    def _get_most_likely_transition(
        self, current_regime: Optional[str], prob_matrix: Dict[str, Dict[str, float]]
    ) -> Tuple[float, Optional[str], float]:
        if current_regime is None or current_regime not in prob_matrix:
            return 0.0, None, 0.0

        transitions = prob_matrix[current_regime]
        if not transitions:
            return 0.0, None, 0.0

        best_to = max(transitions, key=transitions.get)
        best_prob = transitions[best_to]
        return best_prob, best_to, best_prob

    def _get_avg_duration(self, regime: Optional[str]) -> float:
        if regime is None or regime not in self._regime_durations:
            return float(self.config.stability_lookback)
        durations = self._regime_durations[regime]
        if not durations:
            return float(self.config.stability_lookback)
        return float(np.mean(durations))

    def _check_persistence_alert(self, ratio: float, bars: int, avg: float) -> Optional[str]:
        if bars == 0:
            return None
        if ratio > 2.5 and bars > self.config.stability_lookback:
            return f"regime_extended_{bars}v{avg:.0f}avg"
        if ratio < 0.3 and bars < self.config.stability_lookback:
            return f"regime_short_lived_{bars}v{avg:.0f}avg"
        return None

    def _detect_volatility_spike(self) -> Tuple[float, bool, str]:
        if len(self._confidence_history) < self.config.stability_lookback:
            return 0.0, False, "none"

        confidences = np.array(list(self._confidence_history)[-self.config.stability_lookback:])
        if len(confidences) < self.config.stability_lookback:
            return 0.0, False, "none"

        rewards = list(self._regime_history)
        if len(rewards) < self.config.stability_lookback:
            return 0.0, False, "none"

        recent_changes = 0
        for i in range(1, min(self.config.stability_lookback, len(rewards))):
            if rewards[-(i + 1)] != rewards[-i]:
                recent_changes += 1
        regime_vol = recent_changes / max(self.config.stability_lookback - 1, 1)

        conf_vol = float(np.std(confidences))
        spike_score = (regime_vol * 0.5) + (min(conf_vol / 0.1, 1.0) * 0.5)

        if spike_score > 0.7:
            return spike_score, True, "high"
        elif spike_score > 0.4:
            return spike_score, True, "medium"
        elif spike_score > 0.2:
            return spike_score, True, "low"

        return spike_score, False, "none"

    def _check_confidence_degradation(self) -> Tuple[float, bool, str]:
        if len(self._confidence_history) < self.config.stability_lookback + 1:
            return 0.0, False, "stable"

        confidences = list(self._confidence_history)
        recent = confidences[-self.config.stability_lookback:]
        prior = confidences[-(self.config.stability_lookback * 2):-self.config.stability_lookback]

        if len(recent) < 2 or len(prior) < 2:
            return 0.0, False, "stable"

        recent_mean = float(np.mean(recent))
        prior_mean = float(np.mean(prior))

        if prior_mean == 0:
            return 0.0, False, "stable"

        degradation_raw = (prior_mean - recent_mean) / prior_mean
        degradation_abs = max(0.0, min(abs(degradation_raw), 1.0))

        degraded = degradation_abs > self.config.transition_confidence_degradation_threshold and degradation_raw > 0

        if degradation_raw > 0.15:
            trend = "declining"
        elif degradation_raw < -0.05:
            trend = "improving"
        else:
            trend = "stable"

        return round(degradation_abs, 4), degraded, trend

    def _assess_stability(
        self,
        transition_prob: float,
        spike_score: float,
        spike_detected: bool,
        confidence_degraded: bool,
        persistence_ratio: float,
    ) -> Tuple[bool, bool, Optional[str]]:
        alerts: List[str] = []

        is_unstable = False
        is_transitioning = False

        if spike_detected:
            is_unstable = True
            alerts.append("volatility_spike")

        if confidence_degraded:
            is_unstable = True
            alerts.append("confidence_degradation")

        if persistence_ratio > 3.0:
            is_unstable = True
            alerts.append("regime_fatigue")

        if transition_prob > self.config.transition_high_probability_threshold:
            is_transitioning = True
            if persistence_ratio >= 1.5:
                is_transitioning = True
                alerts.append("high_transition_probability")

        if self._current_regime_bar > 0 and self._current_regime_bar <= self.config.stability_lookback:
            is_transitioning = True
            alerts.append("recent_transition")

        alert_str = ";".join(alerts) if alerts else None
        return is_unstable, is_transitioning, alert_str

    def get_transition_summary(self) -> Dict[str, Any]:
        output = self.compute()
        return {
            "transition_probability_matrix": output.transition_probability_matrix,
            "current_transition_probability": output.current_transition_probability,
            "most_likely_next_regime": output.most_likely_next_regime,
            "most_likely_next_probability": output.most_likely_next_probability,
            "regime_persistence_bars": output.regime_persistence_bars,
            "avg_regime_duration": output.avg_regime_duration,
            "persistence_alert": output.persistence_alert,
            "volatility_spike_score": output.volatility_spike_score,
            "vol_spike_detected": output.vol_spike_detected,
            "vol_spike_severity": output.vol_spike_severity,
            "confidence_degradation": output.confidence_degradation,
            "confidence_degraded": output.confidence_degraded,
            "confidence_trend": output.confidence_trend,
            "transition_alert": output.transition_alert,
            "is_unstable": output.is_unstable,
            "is_transitioning": output.is_transitioning,
        }

    def reset(self):
        self._regime_history.clear()
        self._confidence_history.clear()
        self._timestamps.clear()
        self._transition_matrix.clear()
        self._regime_durations.clear()
        self._current_regime_start = None
        self._current_regime_bar = 0
