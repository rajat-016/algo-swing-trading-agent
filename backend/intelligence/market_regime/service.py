import pandas as pd
from datetime import datetime, timezone
from typing import Optional, List, Dict
from loguru import logger

from intelligence.market_regime.config import RegimeConfig
from intelligence.market_regime.regimes import RegimeOutput, RegimeType
from intelligence.market_regime.classifier import RegimeClassifier
from intelligence.market_regime.tracker import RegimeTransitionTracker
from intelligence.market_regime.persistence import RegimePersistence


class RegimeService:
    def __init__(self, config: Optional[RegimeConfig] = None, db=None):
        self.config = config or RegimeConfig()
        self.classifier = RegimeClassifier(self.config)
        self.tracker = RegimeTransitionTracker(self.config)
        self.persistence = RegimePersistence(self.config, db)
        self._latest_output: Optional[RegimeOutput] = None

    def initialize(self, db=None):
        if db is not None:
            self.persistence.initialize(db)
        logger.info("RegimeService initialized")

    def analyze(
        self,
        df: pd.DataFrame,
        store: bool = True,
        persist: bool = True,
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

    def reset(self):
        self.tracker.reset()
        self._latest_output = None
        logger.info("RegimeService reset")
