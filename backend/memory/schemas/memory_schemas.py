from __future__ import annotations

import enum
import json
from datetime import datetime, timezone
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RankingBoost(str, enum.Enum):
    CONFIDENCE = "confidence"
    RECENCY = "recency"
    OUTCOME_PRIORITY = "outcome_priority"
    NONE = "none"


class RankingConfig(BaseModel):
    enabled: bool = Field(default=True, description="Enable metadata ranking")
    boosts: list[RankingBoost] = Field(
        default=[RankingBoost.CONFIDENCE, RankingBoost.RECENCY],
        description="Ordered list of boost factors to apply",
    )
    confidence_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for confidence boost")
    recency_weight: float = Field(default=0.2, ge=0.0, le=1.0, description="Weight for recency boost")
    outcome_priority_weight: float = Field(default=0.15, ge=0.0, le=1.0, description="Weight for outcome priority")
    outcome_priority_order: list[str] = Field(
        default=["stop_loss_hit", "failed", "partial_exit", "target_hit", "success"],
        description="Outcome priority ranking (earlier = higher boost)",
    )
    recency_half_life_days: float = Field(default=30.0, ge=1.0, description="Half-life for recency decay in days")


class HybridSearchConfig(BaseModel):
    enabled: bool = Field(default=False, description="Enable hybrid vector + keyword search")
    vector_weight: float = Field(default=0.7, ge=0.0, le=1.0, description="Weight for vector similarity score")
    keyword_weight: float = Field(default=0.3, ge=0.0, le=1.0, description="Weight for keyword score")
    keyword_n_results_multiplier: int = Field(default=2, ge=1, description="Multiply n_results for keyword query")


class QueryIntent(BaseModel):
    raw_query: str = Field(description="Original user query")
    memory_types: Optional[list[MemoryType]] = Field(default=None, description="Inferred memory types")
    tickers: list[str] = Field(default_factory=list, description="Extracted ticker symbols")
    outcomes: list[str] = Field(default_factory=list, description="Extracted outcome filters")
    regimes: list[str] = Field(default_factory=list, description="Extracted regime filters")
    volatility: Optional[str] = Field(default=None, description="Extracted volatility context")
    confidence_min: Optional[float] = Field(default=None, description="Inferred minimum confidence")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    boost_recent: bool = Field(default=True, description="Boost recent results")

    STOP_WORDS: ClassVar[frozenset[str]] = frozenset({
        "the", "a", "an", "in", "on", "at", "to", "for", "of", "with",
        "and", "or", "but", "not", "find", "show", "get", "what", "when",
        "where", "why", "how", "all", "any", "during", "last", "week",
        "month", "day", "trade", "trades", "market", "regime", "research",
        "feature", "high", "low", "medium", "failed", "success", "successful",
        "breakout", "volatile", "volatility", "confidence", "results",
        "me", "me", "during", "from", "than", "this", "that", "these",
        "those", "are", "was", "were", "been", "being", "have", "has",
        "had", "do", "does", "did", "will", "would", "can", "could",
        "shall", "should", "may", "might", "about", "into", "over",
    })

    @classmethod
    def parse(cls, query: str) -> QueryIntent:
        q = query.lower()
        tickers = []
        outcomes = []
        regimes = []
        volatility = None
        confidence_min = None
        memory_types = None

        if "failed" in q or "stop" in q or "loss" in q:
            outcomes.append("stop_loss_hit")
        if "breakout" in q:
            regimes.append("breakout")
        if "failed breakout" in q:
            outcomes.append("stop_loss_hit")
            regimes.append("breakout")
        if "high volatility" in q or "volatile" in q:
            volatility = "high"
        if "low volatility" in q:
            volatility = "low"
        if "success" in q or "profitable" in q or "win" in q:
            outcomes.append("target_hit")
        if "high confidence" in q:
            confidence_min = 0.7
        if "medium confidence" in q:
            confidence_min = 0.5
        if "market" in q or "regime" in q:
            memory_types = [MemoryType.MARKET]
        if "research" in q or "feature" in q or "experiment" in q:
            memory_types = [MemoryType.RESEARCH]
        if "trade" in q or memory_types is None:
            memory_types = [MemoryType.TRADE]

        tokens = q.split()
        for t in tokens:
            if t in cls.STOP_WORDS:
                continue
            cleaned = "".join(c for c in t if c.isalpha())
            if not cleaned:
                continue
            t_upper = cleaned.upper()
            if len(t_upper) >= 2 and len(t_upper) <= 10 and t_upper.isalpha():
                tickers.append(t_upper)

        return cls(
            raw_query=query,
            memory_types=memory_types,
            tickers=list(set(tickers)),
            outcomes=list(set(outcomes)),
            regimes=list(set(regimes)),
            volatility=volatility,
            confidence_min=confidence_min,
            boost_recent=True,
        )


class AuditLogEntry(BaseModel):
    query: str = Field(description="Original query text")
    query_type: str = Field(default="semantic", description="Query type (semantic/text/hybrid)")
    filters_applied: Optional[dict[str, Any]] = Field(default=None, description="Filters used in query")
    n_requested: int = Field(description="Number of results requested")
    n_returned: int = Field(description="Number of results returned")
    latency_ms: float = Field(description="Query latency in milliseconds")
    memory_types_queried: list[str] = Field(default_factory=list, description="Memory types queried")
    result_ids: list[str] = Field(default_factory=list, description="Returned result document IDs")
    mean_relevance: Optional[float] = Field(default=None, description="Mean relevance score of results")
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="ISO 8601 timestamp")
    error: Optional[str] = Field(default=None, description="Error message if query failed")


class MemoryType(str, enum.Enum):
    TRADE = "trade_memory"
    MARKET = "market_memory"
    RESEARCH = "research_memory"


class TradeMemory(BaseModel):
    SCHEMA_VERSION: ClassVar[str] = "1.0"

    trade_id: str = Field(description="Unique trade identifier")
    ticker: str = Field(description="Stock ticker symbol")
    timestamp: str = Field(description="ISO 8601 timestamp of trade entry/event")
    market_regime: Optional[str] = Field(default=None, description="Market regime classification at trade time")
    feature_snapshot: Optional[dict[str, float]] = Field(default=None, description="ML feature values at decision time")
    prediction: Optional[str] = Field(default=None, description="Model prediction class (BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL/NO_TRADE)")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Model confidence score")
    reasoning: str = Field(description="Reasoning behind the trade decision")
    outcome: Optional[str] = Field(default=None, description="Trade outcome classification")
    portfolio_state: Optional[dict[str, Any]] = Field(default=None, description="Portfolio snapshot at trade time")
    reflection_notes: Optional[str] = Field(default=None, description="Post-trade analysis and reflection")
    schema_version: str = Field(default=SCHEMA_VERSION, description="Schema version identifier")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        try:
            datetime.fromisoformat(v)
        except (ValueError, TypeError):
            raise ValueError(f"timestamp must be ISO 8601 format, got: {v}")
        return v

    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("ticker must not be empty")
        stripped = v.strip().upper()
        if not stripped.isalpha():
            raise ValueError(f"ticker must contain only letters, got: {v}")
        return stripped

    @field_validator("trade_id")
    @classmethod
    def validate_trade_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("trade_id must not be empty")
        return v.strip()

    @field_validator("reasoning")
    @classmethod
    def validate_reasoning(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("reasoning must not be empty")
        return v.strip()

    VALID_PREDICTIONS: ClassVar[frozenset[str]] = frozenset({"BUY", "SELL", "HOLD", "STRONG_BUY", "STRONG_SELL", "NO_TRADE"})

    @field_validator("prediction")
    @classmethod
    def validate_prediction(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            val = v.strip().upper()
            if val not in cls.VALID_PREDICTIONS:
                raise ValueError(
                    f"prediction must be one of {sorted(cls.VALID_PREDICTIONS)}, got: {v}"
                )
            return val
        return v

    @field_validator("feature_snapshot")
    @classmethod
    def validate_feature_snapshot(cls, v: Optional[dict[str, float]]) -> Optional[dict[str, float]]:
        if v is not None and not v:
            raise ValueError("feature_snapshot must not be empty dict; use None if absent")
        return v

    @field_validator("portfolio_state")
    @classmethod
    def validate_portfolio_state(cls, v: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if v is not None and not v:
            raise ValueError("portfolio_state must not be empty dict; use None if absent")
        return v

    @model_validator(mode="after")
    def validate_confidence_range(self):
        if self.confidence is not None and (self.confidence < 0.0 or self.confidence > 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        return self

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=False)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TradeMemory:
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> TradeMemory:
        return cls.model_validate_json(json_str)

    @classmethod
    def validate_schema(cls, data: dict[str, Any]) -> tuple[bool, Optional[str]]:
        try:
            cls(**data)
            return True, None
        except Exception as e:
            return False, str(e)

    def to_embedding_text(self) -> str:
        parts = [
            f"Trade {self.trade_id}: {self.ticker}",
            f"Reasoning: {self.reasoning}",
        ]
        if self.market_regime:
            parts.append(f"Regime: {self.market_regime}")
        if self.prediction:
            parts.append(f"Prediction: {self.prediction}")
        if self.confidence is not None:
            parts.append(f"Confidence: {self.confidence:.2f}")
        if self.outcome:
            parts.append(f"Outcome: {self.outcome}")
        if self.reflection_notes:
            parts.append(f"Reflection: {self.reflection_notes}")
        if self.feature_snapshot:
            top = sorted(self.feature_snapshot.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
            feat_str = ", ".join(f"{k}={v:.3f}" for k, v in top)
            parts.append(f"Top features: [{feat_str}]")
        if self.portfolio_state:
            port_items = []
            for key in ("capital", "exposure", "positions_count", "daily_pnl"):
                if key in self.portfolio_state:
                    port_items.append(f"{key}={self.portfolio_state[key]}")
            if port_items:
                parts.append(f"Portfolio: [{', '.join(port_items)}]")
        return ". ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "memory_type": MemoryType.TRADE.value,
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "schema_version": self.schema_version,
        }
        if self.market_regime:
            meta["market_regime"] = self.market_regime
        if self.prediction:
            meta["prediction"] = self.prediction
        if self.outcome:
            meta["outcome"] = self.outcome
        if self.confidence is not None:
            meta["confidence"] = self.confidence
        return meta

    def collection_id(self) -> str:
        return f"trade_{self.trade_id}_{self.ticker}"


class MarketMemory(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp")
    regime_type: str = Field(description="Market regime classification")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Regime confidence")
    volatility: Optional[str] = Field(default=None, description="Volatility level")
    event_type: Optional[str] = Field(default=None, description="Type of market event")
    description: str = Field(description="Detailed market observation")
    indicators: Optional[dict[str, float]] = Field(default=None, description="Key indicator values")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")

    def to_embedding_text(self) -> str:
        parts = [
            f"Market regime: {self.regime_type}",
            f"Description: {self.description}",
        ]
        if self.volatility:
            parts.append(f"Volatility: {self.volatility}")
        if self.event_type:
            parts.append(f"Event: {self.event_type}")
        if self.indicators:
            ind_str = ", ".join(f"{k}={v:.2f}" for k, v in self.indicators.items())
            parts.append(f"Indicators: [{ind_str}]")
        return ". ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "memory_type": MemoryType.MARKET.value,
            "regime_type": self.regime_type,
            "timestamp": self.timestamp,
        }
        if self.confidence is not None:
            meta["confidence"] = self.confidence
        if self.volatility:
            meta["volatility"] = self.volatility
        if self.event_type:
            meta["event_type"] = self.event_type
        if self.metadata:
            meta.update(self.metadata)
        return meta

    def collection_id(self) -> str:
        return f"market_{self.timestamp}_{self.regime_type}"


class ResearchMemory(BaseModel):
    timestamp: str = Field(description="ISO 8601 timestamp")
    experiment_id: Optional[str] = Field(default=None, description="Experiment identifier")
    feature_name: Optional[str] = Field(default=None, description="Feature under analysis")
    finding: str = Field(description="Research finding or observation")
    insight: Optional[str] = Field(default=None, description="AI-generated insight")
    strategy: Optional[str] = Field(default=None, description="Related strategy")
    metric_value: Optional[float] = Field(default=None, description="Key metric value")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")

    def to_embedding_text(self) -> str:
        parts = [f"Finding: {self.finding}"]
        if self.feature_name:
            parts.append(f"Feature: {self.feature_name}")
        if self.insight:
            parts.append(f"Insight: {self.insight}")
        if self.strategy:
            parts.append(f"Strategy: {self.strategy}")
        if self.experiment_id:
            parts.append(f"Experiment: {self.experiment_id}")
        if self.metric_value is not None:
            parts.append(f"Metric: {self.metric_value}")
        return ". ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "memory_type": MemoryType.RESEARCH.value,
            "timestamp": self.timestamp,
        }
        if self.experiment_id:
            meta["experiment_id"] = self.experiment_id
        if self.feature_name:
            meta["feature_name"] = self.feature_name
        if self.strategy:
            meta["strategy"] = self.strategy
        if self.metric_value is not None:
            meta["metric_value"] = self.metric_value
        if self.metadata:
            meta.update(self.metadata)
        return meta

    def collection_id(self) -> str:
        return f"research_{self.timestamp}_{self.feature_name or 'general'}"


class MemoryFilter(BaseModel):
    memory_type: Optional[MemoryType] = Field(default=None, description="Filter by memory type")
    ticker: Optional[str] = Field(default=None, description="Filter by ticker (trade memory)")
    outcome: Optional[str] = Field(default=None, description="Filter by outcome (trade memory)")
    market_regime: Optional[str] = Field(default=None, description="Filter by market regime")
    event_type: Optional[str] = Field(default=None, description="Filter by event type (market memory)")
    regime_type: Optional[str] = Field(default=None, description="Filter by regime type (market memory)")
    feature_name: Optional[str] = Field(default=None, description="Filter by feature name (research memory)")
    strategy: Optional[str] = Field(default=None, description="Filter by strategy (research memory)")
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum confidence filter")
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results to return")
    offset: int = Field(default=0, ge=0, description="Offset for pagination")
    volatility: Optional[str] = Field(default=None, description="Filter by volatility level")
    tickers: Optional[list[str]] = Field(default=None, description="Filter by multiple tickers")
    outcomes: Optional[list[str]] = Field(default=None, description="Filter by multiple outcomes")
    regimes: Optional[list[str]] = Field(default=None, description="Filter by multiple market regimes")
    min_timestamp: Optional[str] = Field(default=None, description="Minimum timestamp (ISO 8601) for recency filter")
    ranking_config: RankingConfig = Field(default_factory=RankingConfig, description="Metadata ranking configuration")
    hybrid_config: HybridSearchConfig = Field(default_factory=HybridSearchConfig, description="Hybrid search configuration")

    def to_chroma_where(self) -> Optional[dict]:
        clauses = []
        if self.memory_type:
            clauses.append({"memory_type": {"$eq": self.memory_type.value}})
        if self.ticker:
            clauses.append({"ticker": {"$eq": self.ticker}})
        if self.outcome:
            clauses.append({"outcome": {"$eq": self.outcome}})
        if self.market_regime:
            clauses.append({"market_regime": {"$eq": self.market_regime}})
        if self.event_type:
            clauses.append({"event_type": {"$eq": self.event_type}})
        if self.regime_type:
            clauses.append({"regime_type": {"$eq": self.regime_type}})
        if self.feature_name:
            clauses.append({"feature_name": {"$eq": self.feature_name}})
        if self.strategy:
            clauses.append({"strategy": {"$eq": self.strategy}})
        if self.min_confidence is not None:
            clauses.append({"confidence": {"$gte": self.min_confidence}})
        if self.volatility:
            clauses.append({"volatility": {"$eq": self.volatility}})
        if self.outcomes:
            if len(self.outcomes) == 1:
                clauses.append({"outcome": {"$eq": self.outcomes[0]}})
            else:
                clauses.append({"outcome": {"$in": self.outcomes}})
        if self.tickers:
            if len(self.tickers) == 1:
                clauses.append({"ticker": {"$eq": self.tickers[0]}})
            else:
                clauses.append({"ticker": {"$in": self.tickers}})
        if self.regimes:
            if len(self.regimes) == 1:
                clauses.append({"market_regime": {"$eq": self.regimes[0]}})
            else:
                clauses.append({"market_regime": {"$in": self.regimes}})

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}

    @classmethod
    def from_query_intent(cls, intent: QueryIntent) -> MemoryFilter:
        return cls(
            memory_type=intent.memory_types[0] if intent.memory_types and len(intent.memory_types) == 1 else None,
            ticker=intent.tickers[0] if len(intent.tickers) == 1 else None,
            tickers=intent.tickers if len(intent.tickers) > 1 else None,
            outcome=intent.outcomes[0] if len(intent.outcomes) == 1 else None,
            outcomes=intent.outcomes if len(intent.outcomes) > 1 else None,
            regimes=intent.regimes if intent.regimes else None,
            volatility=intent.volatility,
            min_confidence=intent.confidence_min,
            max_results=intent.max_results,
        )


class SearchResult(BaseModel):
    id: str = Field(description="Document ID")
    memory_type: MemoryType = Field(description="Type of memory")
    text: str = Field(description="Document text")
    metadata: dict[str, Any] = Field(description="Metadata")
    distance: float = Field(description="Cosine distance (0 = identical)")
    relevance_score: float = Field(description="Normalized relevance (1 = best)")
    ranked_score: Optional[float] = Field(default=None, description="Metadata-ranked score (1 = best)")
    hybrid_score: Optional[float] = Field(default=None, description="Hybrid vector + keyword score (1 = best)")

    @classmethod
    def from_chroma_result(cls, chroma_result: dict, index: int) -> "SearchResult":
        ids = chroma_result.get("ids", [[]])[0]
        documents = chroma_result.get("documents", [[]])[0]
        metadatas = chroma_result.get("metadatas", [[]])[0]
        distances = chroma_result.get("distances", [[]])[0]

        mem_type_str = metadatas[index].get("memory_type", "unknown") if metadatas else "unknown"
        try:
            mem_type = MemoryType(mem_type_str)
        except ValueError:
            mem_type = MemoryType.TRADE

        dist = distances[index] if distances else 1.0
        relevance = max(0.0, 1.0 - dist)

        return cls(
            id=ids[index] if ids else "",
            memory_type=mem_type,
            text=documents[index] if documents else "",
            metadata=metadatas[index] if metadatas else {},
            distance=dist,
            relevance_score=relevance,
        )

    @classmethod
    def from_chroma_batch(cls, chroma_result: dict) -> list["SearchResult"]:
        ids_list = chroma_result.get("ids", [])
        if not ids_list:
            return []
        count = len(ids_list[0])
        return [cls.from_chroma_result(chroma_result, i) for i in range(count)]
