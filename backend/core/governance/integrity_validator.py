from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from loguru import logger

from core.governance.config import GovernanceConfig


class MemoryIntegrityValidator:
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self._config = config or GovernanceConfig.default()
        self._enabled = self._config.integrity_validation_enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False
        logger.info("MemoryIntegrityValidator disabled")

    def enable(self):
        self._enabled = True
        logger.info("MemoryIntegrityValidator enabled")

    @staticmethod
    def compute_hash(data: dict[str, Any]) -> str:
        serialized = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def validate_on_store(self, memory_data: dict[str, Any]) -> dict[str, Any]:
        if not self._enabled:
            return memory_data
        integrity_hash = self.compute_hash(memory_data)
        memory_data["integrity_hash"] = integrity_hash
        return memory_data

    def validate_on_retrieve(
        self, metadata: dict[str, Any], text: str
    ) -> tuple[bool, Optional[str]]:
        if not self._enabled:
            return True, None
        stored_hash = metadata.get("integrity_hash")
        if stored_hash is None:
            if self._config.integrity_reject_corrupted:
                return False, "No integrity_hash found in metadata"
            return True, "No integrity_hash found (warning only)"
        check_data = {k: v for k, v in metadata.items() if k != "integrity_hash"}
        computed = self.compute_hash(check_data)
        if computed != stored_hash:
            msg = (
                f"Integrity mismatch: stored={stored_hash[:16]}... "
                f"computed={computed[:16]}..."
            )
            if self._config.integrity_reject_corrupted:
                return False, msg
            logger.warning(f"Memory integrity warning: {msg}")
            return True, msg
        return True, None

    def validate_integrity_batch(
        self, results: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not self._enabled:
            return results
        valid: list[dict[str, Any]] = []
        for r in results:
            metadata = r.get("metadata", {}) or {}
            text = r.get("text", "") or ""
            ok, _ = self.validate_on_retrieve(metadata, text)
            if ok:
                valid.append(r)
            elif not self._config.integrity_reject_corrupted:
                valid.append(r)
        return valid
