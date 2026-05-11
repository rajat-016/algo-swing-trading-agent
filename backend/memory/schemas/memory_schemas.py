from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class MemoryType(str, enum.Enum):
    TRADE = "trade_memory"
    MARKET = "market_memory"
    RESEARCH = "research_memory"


class TradeMemory(BaseModel):
    trade_id: str = Field(description="Unique trade identifier")
    ticker: str = Field(description="Stock ticker symbol")
    timestamp: str = Field(description="ISO 8601 timestamp of trade")
    market_regime: Optional[str] = Field(default=None, description="Market regime at trade time")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Model confidence")
    reasoning: str = Field(description="Reasoning behind the trade")
    outcome: Optional[str] = Field(default=None, description="Trade outcome (win/loss/stop_loss_hit/etc)")
    features: Optional[dict[str, float]] = Field(default=None, description="Feature snapshot")
    pnl: Optional[float] = Field(default=None, description="Profit/loss for this trade")
    metadata: Optional[dict[str, Any]] = Field(default=None, description="Additional metadata")

    def to_embedding_text(self) -> str:
        parts = [
            f"Trade {self.trade_id}: {self.ticker}",
            f"Reasoning: {self.reasoning}",
        ]
        if self.market_regime:
            parts.append(f"Regime: {self.market_regime}")
        if self.outcome:
            parts.append(f"Outcome: {self.outcome}")
        if self.features:
            top = sorted(self.features.items(), key=lambda x: abs(x[1]), reverse=True)[:10]
            feat_str = ", ".join(f"{k}={v:.3f}" for k, v in top)
            parts.append(f"Top features: [{feat_str}]")
        return ". ".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "memory_type": MemoryType.TRADE.value,
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "timestamp": self.timestamp,
        }
        if self.market_regime:
            meta["market_regime"] = self.market_regime
        if self.outcome:
            meta["outcome"] = self.outcome
        if self.confidence is not None:
            meta["confidence"] = self.confidence
        if self.pnl is not None:
            meta["pnl"] = self.pnl
        if self.metadata:
            meta.update(self.metadata)
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

        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}


class SearchResult(BaseModel):
    id: str = Field(description="Document ID")
    memory_type: MemoryType = Field(description="Type of memory")
    text: str = Field(description="Document text")
    metadata: dict[str, Any] = Field(description="Metadata")
    distance: float = Field(description="Cosine distance (0 = identical)")
    relevance_score: float = Field(description="Normalized relevance (1 = best)")

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
