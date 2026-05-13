from __future__ import annotations

from typing import Optional

from loguru import logger

from core.governance.config import GovernanceConfig

COMPONENT_CONFIDENCE_KEYS: dict[str, str] = {
    "trade_explain": "confidence_min_trade_explain",
    "trade_explanation": "confidence_min_trade_explain",
    "research": "confidence_min_research",
    "research_assistant": "confidence_min_research",
    "reflection": "confidence_min_reflection",
    "reflection_engine": "confidence_min_reflection",
    "market_regime": "confidence_min_global",
    "portfolio_analysis": "confidence_min_global",
    "memory_search": "confidence_min_global",
    "intelligence_summary": "confidence_min_global",
    "default": "confidence_min_global",
}


class ConfidenceThresholdEnforcer:
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self._config = config or GovernanceConfig.default()
        self._enabled = self._config.confidence_enforcement_enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False
        logger.info("ConfidenceThresholdEnforcer disabled")

    def enable(self):
        self._enabled = True
        logger.info("ConfidenceThresholdEnforcer enabled")

    def get_min_confidence(self, component: str = "default") -> float:
        config_key = COMPONENT_CONFIDENCE_KEYS.get(component, "confidence_min_global")
        return getattr(self._config, config_key, self._config.confidence_min_global)

    def check_confidence(
        self,
        confidence: Optional[float],
        component: str = "default",
    ) -> tuple[bool, Optional[str]]:
        if not self._enabled or confidence is None:
            return True, None
        min_conf = self.get_min_confidence(component)
        if confidence < min_conf:
            msg = (
                f"Confidence {confidence:.3f} below threshold "
                f"{min_conf:.3f} for component '{component}'"
            )
            logger.warning(msg)
            return False, msg
        return True, None
