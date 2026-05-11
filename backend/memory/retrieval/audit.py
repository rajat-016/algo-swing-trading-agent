from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from loguru import logger

from memory.schemas.memory_schemas import AuditLogEntry, MemoryType, SearchResult

_audit_lock = threading.Lock()


class RetrievalAuditor:
    def __init__(self, persist_path: Optional[str] = None, max_entries: int = 10000):
        self._persist_path = persist_path
        self._max_entries = max_entries
        self._entries: list[AuditLogEntry] = []
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False

    def enable(self):
        self._enabled = True

    def log(
        self,
        query: str,
        query_type: str,
        n_requested: int,
        n_returned: int,
        latency_ms: float,
        memory_types_queried: list[str],
        result_ids: list[str],
        mean_relevance: Optional[float] = None,
        filters_applied: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> AuditLogEntry:
        if not self._enabled:
            return AuditLogEntry(
                query=query, query_type=query_type, n_requested=n_requested,
                n_returned=n_returned, latency_ms=latency_ms,
            )

        entry = AuditLogEntry(
            query=query,
            query_type=query_type,
            n_requested=n_requested,
            n_returned=n_returned,
            latency_ms=latency_ms,
            memory_types_queried=memory_types_queried,
            result_ids=result_ids,
            mean_relevance=mean_relevance,
            filters_applied=filters_applied,
            error=error,
        )

        with _audit_lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                self._entries.pop(0)

        logger.debug(
            f"Audit: {query_type} query '{query[:40]}' "
            f"returned {n_returned}/{n_requested} in {latency_ms:.0f}ms"
        )
        return entry

    def log_search(
        self,
        query: str,
        results: list[SearchResult],
        latency_ms: float,
        mem_types: list[MemoryType],
        n_requested: int,
        filters_applied: Optional[dict[str, Any]] = None,
        error: Optional[str] = None,
    ) -> AuditLogEntry:
        mean_rel = None
        if results:
            mean_rel = sum(r.relevance_score for r in results) / len(results)
        return self.log(
            query=query,
            query_type="semantic",
            n_requested=n_requested,
            n_returned=len(results),
            latency_ms=latency_ms,
            memory_types_queried=[mt.value for mt in mem_types],
            result_ids=[r.id for r in results],
            mean_relevance=mean_rel,
            filters_applied=filters_applied,
            error=error,
        )

    def get_recent(self, limit: int = 50) -> list[AuditLogEntry]:
        with _audit_lock:
            return list(self._entries[-limit:])

    def get_stats(self) -> dict[str, Any]:
        with _audit_lock:
            total = len(self._entries)
            if total == 0:
                return {"total_queries": 0, "enabled": self._enabled}
            latencies = [e.latency_ms for e in self._entries]
            return {
                "total_queries": total,
                "enabled": self._enabled,
                "avg_latency_ms": sum(latencies) / len(latencies),
                "max_latency_ms": max(latencies),
                "min_latency_ms": min(latencies),
                "error_count": sum(1 for e in self._entries if e.error),
                "memory_types": list(
                    set(mt for e in self._entries for mt in e.memory_types_queried)
                ),
            }

    def persist(self, filepath: Optional[str] = None):
        path = filepath or self._persist_path
        if not path:
            return
        with _audit_lock:
            data = [e.model_dump() for e in self._entries]
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Persisted {len(data)} audit entries to {path}")
        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")

    def load(self, filepath: Optional[str] = None):
        path = filepath or self._persist_path
        if not path or not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            with _audit_lock:
                self._entries = [AuditLogEntry(**e) for e in data]
            logger.info(f"Loaded {len(self._entries)} audit entries from {path}")
        except Exception as e:
            logger.error(f"Failed to load audit log: {e}")

    def clear(self):
        with _audit_lock:
            self._entries.clear()
        logger.info("Audit log cleared")
