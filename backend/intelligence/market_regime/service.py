import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict
from loguru import logger

from intelligence.market_regime.config import RegimeConfig
from intelligence.market_regime.regimes import RegimeOutput, RegimeType
from intelligence.market_regime.classifier import RegimeClassifier
from intelligence.market_regime.tracker import RegimeTransitionTracker
from intelligence.market_regime.persistence import RegimePersistence
from intelligence.market_regime.features import RegimeFeaturePipeline
from intelligence.market_regime.features.feature_drift_logger import FeatureDriftLogger
from intelligence.market_regime.transition_detector import TransitionDetector


class RegimeService:
    def __init__(self, config: Optional[RegimeConfig] = None, db=None):
        self.config = config or RegimeConfig()
        self.classifier = RegimeClassifier(self.config)
        self.tracker = RegimeTransitionTracker(self.config)
        self.persistence = RegimePersistence(self.config, db)
        self.drift_logger = FeatureDriftLogger(db)
        self.feature_pipeline = RegimeFeaturePipeline(self.drift_logger, db)
        self.transition_detector = TransitionDetector(self.config)
        self._latest_output: Optional[RegimeOutput] = None

    def initialize(self, db=None):
        if db is not None:
            self.persistence.initialize(db)
            self.drift_logger.initialize(db)
            self.feature_pipeline.initialize(db)
        logger.info("RegimeService initialized")

    def analyze(
        self,
        df: pd.DataFrame,
        store: bool = True,
        persist: bool = True,
        vix_level: Optional[float] = None,
        vix_change: Optional[float] = None,
        put_call_ratio: Optional[float] = None,
        sector_returns: Optional[Dict[str, float]] = None,
        nifty_return: Optional[float] = None,
        per_stock_df: Optional[pd.DataFrame] = None,
        pct_above_ma50: Optional[float] = None,
        pct_above_ma200: Optional[float] = None,
    ) -> RegimeOutput:
        if df is None or df.empty:
            output = RegimeOutput(
                regime=RegimeType.UNKNOWN,
                confidence=0.0,
                risk_level="medium",
                stability="unknown",
            )
            self._latest_output = output
            return output

        recent_regimes = self.tracker.get_recent_regimes()
        output = self.classifier.classify(df, recent_regimes)
        output.timestamp = datetime.now(timezone.utc).isoformat()

        if store:
            transition = self.tracker.record_transition(
                new_regime=output.regime.value if isinstance(output.regime, RegimeType) else output.regime,
                confidence=output.confidence,
                timestamp=output.timestamp,
            )
            if transition:
                logger.info(
                    f"Regime transition: {transition.from_regime} -> {transition.to_regime} "
                    f"(confidence: {output.confidence:.2f})"
                )

        if persist:
            self.persistence.store_regime(output)

        regime_features = self.feature_pipeline.compute_and_log(
            ohlcv_df=df,
            vix_level=vix_level,
            vix_change=vix_change,
            put_call_ratio=put_call_ratio,
            sector_returns=sector_returns,
            nifty_return=nifty_return,
            per_stock_df=per_stock_df,
            pct_above_ma50=pct_above_ma50,
            pct_above_ma200=pct_above_ma200,
        )

        if persist:
            regime_name = output.regime.value if isinstance(output.regime, RegimeType) else str(output.regime)
            self.feature_pipeline.persist_snapshot(
                regime=regime_name,
                confidence=output.confidence,
                feature_data=regime_features,
            )

        output.regime_features = regime_features

        transition_output = self.transition_detector.record(
            regime=regime_name,
            confidence=output.confidence,
            timestamp=output.timestamp,
        )
        if transition_output is not None:
            output.transition_data = {
                "transition_probability_matrix": transition_output.transition_probability_matrix,
                "current_transition_probability": transition_output.current_transition_probability,
                "most_likely_next_regime": transition_output.most_likely_next_regime,
                "most_likely_next_probability": transition_output.most_likely_next_probability,
                "regime_persistence_bars": transition_output.regime_persistence_bars,
                "avg_regime_duration": transition_output.avg_regime_duration,
                "persistence_alert": transition_output.persistence_alert,
                "volatility_spike_score": transition_output.volatility_spike_score,
                "vol_spike_detected": transition_output.vol_spike_detected,
                "vol_spike_severity": transition_output.vol_spike_severity,
                "confidence_degradation": transition_output.confidence_degradation,
                "confidence_degraded": transition_output.confidence_degraded,
                "confidence_trend": transition_output.confidence_trend,
                "transition_alert": transition_output.transition_alert,
                "is_unstable": transition_output.is_unstable,
                "is_transitioning": transition_output.is_transitioning,
            }
            if persist and self.persistence.is_ready:
                self.persistence.store_transition_log(transition_output, regime_name)

            if transition_output.is_unstable or transition_output.is_transitioning:
                logger.warning(
                    f"Regime instability detected: regime={regime_name} "
                    f"unstable={transition_output.is_unstable} "
                    f"transitioning={transition_output.is_transitioning} "
                    f"alerts={transition_output.transition_alert}"
                )

        self._latest_output = output
        return output

    def get_current_regime(self) -> Optional[RegimeOutput]:
        return self._latest_output

    def get_regime_history(self, limit: int = 100) -> List[dict]:
        return self.persistence.get_recent_regimes(limit)

    def get_regime_stats(self) -> dict:
        tracker_stats = self.tracker.get_stats()
        persistence_stats = {
            "persistence_ready": self.persistence.is_ready,
        }
        return {**tracker_stats, **persistence_stats}

    def get_transitions(self, n: int = 10) -> List[dict]:
        return self.tracker.get_recent_transitions(n)

    def get_regime_distribution(self, days: int = 30) -> Dict[str, int]:
        return self.persistence.get_regime_distribution(days)

    def get_transition_summary(self) -> dict:
        return self.transition_detector.get_transition_summary()

    def get_transition_logs(self, limit: int = 50) -> List[dict]:
        return self.persistence.get_transition_logs(limit)

    def reset(self):
        self.tracker.reset()
        self.transition_detector.reset()
        self._latest_output = None
        logger.info("RegimeService reset")
