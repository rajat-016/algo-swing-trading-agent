from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from core.governance.audit_logger import AiAuditLogger, AuditEntry
from core.governance.confidence_enforcer import ConfidenceThresholdEnforcer
from core.governance.config import GovernanceConfig
from core.governance.execution_guard import ExecutionPermissionGuard
from core.governance.integrity_validator import MemoryIntegrityValidator
from core.governance.safety_checker import RetrievalSafetyChecker


class GovernanceManager:
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self._config = config or GovernanceConfig.default()
        self.audit: AiAuditLogger = AiAuditLogger(self._config)
        self.integrity: MemoryIntegrityValidator = MemoryIntegrityValidator(
            self._config
        )
        self.confidence: ConfidenceThresholdEnforcer = ConfidenceThresholdEnforcer(
            self._config
        )
        self.safety: RetrievalSafetyChecker = RetrievalSafetyChecker(self._config)
        self.execution: ExecutionPermissionGuard = ExecutionPermissionGuard(
            self._config, self.safety
        )
        self._initialized = False
        logger.info("GovernanceManager created")

    def initialize(self):
        if self._initialized:
            return
        self.audit.load()
        self._initialized = True
        logger.info("GovernanceManager initialized")

    def check_health(self) -> dict[str, Any]:
        return {
            "audit": {
                "enabled": self.audit.enabled,
                "stats": self.audit.get_stats(),
            },
            "integrity": {"enabled": self.integrity.enabled},
            "confidence": {"enabled": self.confidence.enabled},
            "safety": {"enabled": self.safety.enabled},
            "execution_guard": self.execution.get_stats(),
        }

    def log_ai_output(
        self,
        action: str,
        component: str,
        details: dict[str, Any],
        start_time: Optional[float] = None,
        user: str = "system",
        status: str = "success",
        error: Optional[str] = None,
    ) -> Optional[AuditEntry]:
        if start_time is not None:
            return self.audit.timed_log(
                action=action,
                component=component,
                details=details,
                start_time=start_time,
                user=user,
                status=status,
                error=error,
            )
        return self.audit.log(
            action=action,
            component=component,
            details=details,
            user=user,
            status=status,
            error=error,
        )


_governance_instance: Optional[GovernanceManager] = None


def get_governance_manager() -> GovernanceManager:
    global _governance_instance
    if _governance_instance is None:
        _governance_instance = GovernanceManager()
        _governance_instance.initialize()
    return _governance_instance
