from __future__ import annotations

from pydantic import BaseModel, Field


class GovernanceConfig(BaseModel):
    audit_enabled: bool = Field(
        default=True, description="Enable centralized audit logging for all AI outputs"
    )
    audit_max_entries: int = Field(
        default=50000, description="Max audit log entries in memory"
    )
    audit_persist_path: str = Field(
        default="data/governance/audit_log.json",
        description="File path for audit log persistence",
    )

    integrity_validation_enabled: bool = Field(
        default=True, description="Enable memory integrity hash validation on store/retrieve"
    )
    integrity_reject_corrupted: bool = Field(
        default=True, description="Reject reads of corrupted memory (True) or warn (False)"
    )

    confidence_enforcement_enabled: bool = Field(
        default=True, description="Enable global confidence threshold enforcement"
    )
    confidence_min_global: float = Field(
        default=0.50, ge=0.0, le=1.0, description="Global min confidence for AI-generated insights"
    )
    confidence_min_trade_explain: float = Field(
        default=0.40, ge=0.0, le=1.0, description="Min confidence for trade explanations"
    )
    confidence_min_research: float = Field(
        default=0.50, ge=0.0, le=1.0, description="Min confidence for research outputs"
    )
    confidence_min_reflection: float = Field(
        default=0.35, ge=0.0, le=1.0, description="Min confidence for reflection outputs"
    )

    retrieval_safety_enabled: bool = Field(
        default=True, description="Enable retrieval query safety checks"
    )
    retrieval_block_sql_injection: bool = Field(
        default=True, description="Block queries with SQL injection patterns"
    )
    retrieval_block_pii: bool = Field(
        default=True, description="Block queries containing PII patterns"
    )
    retrieval_max_query_length: int = Field(
        default=2000, ge=1, le=10000, description="Maximum allowed query length"
    )

    execution_guard_enabled: bool = Field(
        default=True, description="Enable execution permission guard"
    )

    @classmethod
    def default(cls) -> GovernanceConfig:
        return cls()
