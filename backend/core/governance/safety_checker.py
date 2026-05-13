from __future__ import annotations

import re
from typing import Any, Optional

from loguru import logger

from core.governance.config import GovernanceConfig

SQL_INJECTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bSELECT\s+.+\bFROM\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    re.compile(r"\bUNION\s+ALL\b", re.IGNORECASE),
    re.compile(r"'\s*OR\s*'1'\s*=\s*'1", re.IGNORECASE),
    re.compile(r"'\s*OR\s*1\s*=\s*1", re.IGNORECASE),
    re.compile(r"--\s*$", re.IGNORECASE),
    re.compile(r"/\*.*\*/"),
    re.compile(r"\bEXEC\b", re.IGNORECASE),
    re.compile(r"\bxp_cmdshell\b", re.IGNORECASE),
]

PII_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"),
    re.compile(r"\b\d{16,19}\b"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    re.compile(
        r"\b(?:password|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*\S+",
        re.IGNORECASE,
    ),
]

EXECUTION_PATTERNS: list[re.Pattern] = [
    re.compile(r"\bplace\s+(buy|sell|order)\b", re.IGNORECASE),
    re.compile(r"\bexecute\s+(buy|sell|trade|order)\b", re.IGNORECASE),
    re.compile(r"\benter\s+(long|short|position)\b", re.IGNORECASE),
    re.compile(r"\bexit\s+(long|short|position|all)\b", re.IGNORECASE),
    re.compile(r"\bclose\s+(position|all|trade)\b", re.IGNORECASE),
    re.compile(r"\bsubmit\s+order\b", re.IGNORECASE),
]


class RetrievalSafetyChecker:
    def __init__(self, config: Optional[GovernanceConfig] = None):
        self._config = config or GovernanceConfig.default()
        self._enabled = self._config.retrieval_safety_enabled

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self):
        self._enabled = False
        logger.info("RetrievalSafetyChecker disabled")

    def enable(self):
        self._enabled = True
        logger.info("RetrievalSafetyChecker enabled")

    def check_query(self, query: str) -> tuple[bool, dict[str, Any]]:
        result: dict[str, Any] = {
            "original_length": len(query),
            "checks": {},
            "blocked": False,
        }

        if not self._enabled:
            result["checks"]["enabled"] = False
            return True, result

        if len(query) > self._config.retrieval_max_query_length:
            result["blocked"] = True
            result["checks"]["max_length"] = (
                f"Query exceeds max length "
                f"({len(query)} > {self._config.retrieval_max_query_length})"
            )
            logger.warning(f"Query blocked: exceeds max length ({len(query)} chars)")
            return False, result

        if self._config.retrieval_block_sql_injection:
            for pattern in SQL_INJECTION_PATTERNS:
                match = pattern.search(query)
                if match:
                    result["blocked"] = True
                    found = match.group()[:60]
                    result["checks"]["sql_injection"] = f"Pattern matched: '{found}'"
                    logger.warning(f"Query blocked: SQL injection pattern '{found}'")
                    return False, result

        if self._config.retrieval_block_pii:
            for pattern in PII_PATTERNS:
                match = pattern.search(query)
                if match:
                    result["blocked"] = True
                    found = match.group()[:40]
                    result["checks"]["pii"] = f"PII pattern matched: '{found}'"
                    logger.warning(f"Query blocked: PII detected '{found}'")
                    return False, result

        result["checks"]["passed"] = True
        return True, result

    def check_execution_intent(self, text: str) -> tuple[bool, Optional[str]]:
        for pattern in EXECUTION_PATTERNS:
            match = pattern.search(text)
            if match:
                found = match.group()
                msg = f"Execution intent detected in AI output: '{found}'"
                logger.warning(msg)
                return False, msg
        return True, None
