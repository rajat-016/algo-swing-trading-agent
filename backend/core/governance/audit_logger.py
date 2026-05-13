from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from core.governance.config import GovernanceConfig


class AuditEntry:
    def __init__(
        self,
        action: str,
        component: str,
        details: dict[str, Any],
        user: str = "system",
        status: str = "success",
        error: Optional[str] = None,
    ):
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.action: str = action
        self.component: str = component
        self.user: str = user
        self.status: str = status
        self.details: dict[str, Any] = details
        self.error: Optional[str] = error
        self.latency_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "timestamp": self.timestamp,
            "action": self.action,
            "component": self.component,
            "user": self.user,
            "status": self.status,
            "details": self._sanitize_details(self.details),
        }
        if self.error:
            d["error"] = self.error
        if self.latency_ms is not None:
            d["latency_ms"] = self.latency_ms
        return d

    @staticmethod
    def _sanitize_details(details: dict[str, Any]) -> dict[str, Any]:
        SENSITIVE_KEYS = {"api_key", "secret", "password", "token", "access_token"}
        sanitized: dict[str, Any] = {}
        for k, v in details.items():
            if k.lower() in SENSITIVE_KEYS:
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, dict):
                sanitized[k] = AuditEntry._sanitize_details(v)
            elif isinstance(v, str) and len(v) > 5000:
                sanitized[k] = v[:5000] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized


_audit_lock = threading.Lock()


class AiAuditLogger:
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self._config = config or GovernanceConfig.default()
        self._entries: list[AuditEntry] = []
        self._enabled = self._config.audit_enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False
        logger.info("AiAuditLogger disabled")

    def enable(self):
        self._enabled = True
        logger.info("AiAuditLogger enabled")

    def log(
        self,
        action: str,
        component: str,
        details: dict[str, Any],
        user: str = "system",
        status: str = "success",
        error: Optional[str] = None,
    ) -> Optional[AuditEntry]:
        if not self._enabled:
            return None
        entry = AuditEntry(
            action=action,
            component=component,
            details=details,
            user=user,
            status=status,
            error=error,
        )
        with _audit_lock:
            self._entries.append(entry)
            if len(self._entries) > self._config.audit_max_entries:
                self._entries.pop(0)
        logger.debug(
            f"Audit: {component}.{action} -> {status} "
            f"({list(details.keys())[:3]})"
        )
        return entry

    def timed_log(
        self,
        action: str,
        component: str,
        details: dict[str, Any],
        start_time: float,
        user: str = "system",
        status: str = "success",
        error: Optional[str] = None,
    ) -> Optional[AuditEntry]:
        entry = self.log(
            action=action,
            component=component,
            details=details,
            user=user,
            status=status,
            error=error,
        )
        if entry is not None:
            entry.latency_ms = (time.monotonic() - start_time) * 1000
        return entry

    def get_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        with _audit_lock:
            return [e.to_dict() for e in self._entries[-limit:]]

    def get_stats(self) -> dict[str, Any]:
        with _audit_lock:
            total = len(self._entries)
            if total == 0:
                return {"total_entries": 0, "enabled": self._enabled}
            error_count = sum(1 for e in self._entries if e.error)
            action_counts: dict[str, int] = {}
            component_counts: dict[str, int] = {}
            for e in self._entries:
                action_counts[e.action] = action_counts.get(e.action, 0) + 1
                component_counts[e.component] = component_counts.get(e.component, 0) + 1
            return {
                "total_entries": total,
                "enabled": self._enabled,
                "error_count": error_count,
                "error_rate": round(error_count / total, 4),
                "actions": dict(
                    sorted(action_counts.items(), key=lambda x: -x[1])[:10]
                ),
                "components": dict(
                    sorted(component_counts.items(), key=lambda x: -x[1])[:10]
                ),
            }

    def query(
        self,
        action: Optional[str] = None,
        component: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        with _audit_lock:
            filtered = list(self._entries)
        if action:
            filtered = [e for e in filtered if e.action == action]
        if component:
            filtered = [e for e in filtered if e.component == component]
        if status:
            filtered = [e for e in filtered if e.status == status]
        return [e.to_dict() for e in filtered[-limit:]]

    def persist(self, filepath: Optional[str] = None):
        path = filepath or self._config.audit_persist_path
        if not path:
            return
        with _audit_lock:
            data = [e.to_dict() for e in self._entries]
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Persisted {len(data)} audit entries to {path}")
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")

    def load(self, filepath: Optional[str] = None):
        path = filepath or self._config.audit_persist_path
        if not path or not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            with _audit_lock:
                self._entries = []
                for item in data:
                    entry = AuditEntry(
                        action=item.get("action", "unknown"),
                        component=item.get("component", "unknown"),
                        details=item.get("details", {}),
                        user=item.get("user", "system"),
                        status=item.get("status", "success"),
                        error=item.get("error"),
                    )
                    entry.timestamp = item.get("timestamp", entry.timestamp)
                    entry.latency_ms = item.get("latency_ms")
                    self._entries.append(entry)
            logger.info(f"Loaded {len(self._entries)} audit entries from {path}")
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")

    def clear(self):
        with _audit_lock:
            self._entries.clear()
        logger.info("Audit log cleared")
