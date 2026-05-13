from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from core.governance.config import GovernanceConfig
from core.governance.safety_checker import RetrievalSafetyChecker


class ExecutionPermissionGuard:
    def __init__(
        self,
        config: Optional[GovernanceConfig] = None,
        safety_checker: Optional[RetrievalSafetyChecker] = None,
    ):
        self._config = config or GovernanceConfig.default()
        self._safety = safety_checker or RetrievalSafetyChecker(config)
        self._enabled = self._config.execution_guard_enabled
        self._blocked_attempts: list[dict[str, Any]] = []

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False
        logger.info("ExecutionPermissionGuard disabled")

    def enable(self):
        self._enabled = True
        logger.info("ExecutionPermissionGuard enabled")

    def check_output(self, ai_output: str, source: str = "unknown") -> tuple[bool, Optional[str]]:
        if not self._enabled:
            return True, None

        ok, reason = self._safety.check_execution_intent(ai_output)
        if not ok:
            self._blocked_attempts.append({
                "source": source,
                "reason": reason,
                "output_snippet": ai_output[:200],
            })
            logger.warning(
                f"Execution BLOCKED from '{source}': {reason}"
            )
            return False, reason

        return True, None

    def get_blocked_attempts(
        self, limit: int = 50
    ) -> list[dict[str, Any]]:
        return list(self._blocked_attempts[-limit:])

    def get_stats(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "total_blocked": len(self._blocked_attempts),
        }
