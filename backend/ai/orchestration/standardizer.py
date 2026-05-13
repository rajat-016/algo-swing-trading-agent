import time
import json
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


ORCHESTRATION_VERSION = "1.0.0"


@dataclass
class StandardIntelligenceOutput:
    status: str = "ok"
    version: str = ORCHESTRATION_VERSION
    module: str = ""
    latency_ms: float = 0.0
    timestamp: str = ""
    error: Optional[str] = None
    data: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ("status", "version", "module", "latency_ms", "timestamp")}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)

    @classmethod
    def error_output(cls, module: str, error: str, latency_ms: float = 0) -> "StandardIntelligenceOutput":
        return cls(
            status="error",
            module=module,
            latency_ms=latency_ms,
            error=error,
        )


@dataclass
class StandardTradeExplanation:
    symbol: str = ""
    prediction: str = ""
    confidence: float = 0.0
    confidence_level: str = ""
    top_features: list[dict] = field(default_factory=list)
    regime_context: dict = field(default_factory=dict)
    similar_trades: list[dict] = field(default_factory=list)
    failure_analysis: dict = field(default_factory=dict)
    reasoning: str = ""
    latency_ms: float = 0.0

    def to_standard(self, module: str = "trade_explanation") -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput(
            module=module,
            latency_ms=self.latency_ms,
            data={
                "symbol": self.symbol,
                "prediction": self.prediction,
                "confidence": self.confidence,
                "confidence_level": self.confidence_level,
                "top_features": self.top_features,
                "reasoning": self.reasoning,
            },
            context={
                "regime": self.regime_context,
                "similar_trades": self.similar_trades,
                "failure_analysis": self.failure_analysis,
            },
        )


@dataclass
class StandardPortfolioAnalysis:
    risk_score: float = 0.0
    risk_level: str = ""
    sector_exposure: list[dict] = field(default_factory=list)
    correlations: list[dict] = field(default_factory=list)
    diversification_score: float = 0.0
    directional_bias: str = ""
    volatility_exposure: str = ""
    alerts: list[str] = field(default_factory=list)
    holding_count: int = 0
    latency_ms: float = 0.0

    def to_standard(self, module: str = "portfolio_analysis") -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput(
            module=module,
            latency_ms=self.latency_ms,
            data={
                "risk_score": self.risk_score,
                "risk_level": self.risk_level,
                "diversification_score": self.diversification_score,
                "directional_bias": self.directional_bias,
                "volatility_exposure": self.volatility_exposure,
                "holding_count": self.holding_count,
            },
            context={
                "sector_exposure": self.sector_exposure,
                "correlations": self.correlations,
                "alerts": self.alerts,
            },
        )


@dataclass
class StandardRegimeAnalysis:
    regime: str = ""
    confidence: float = 0.0
    stability: str = ""
    risk_level: str = ""
    transitions: list[dict] = field(default_factory=list)
    volatility_context: dict = field(default_factory=dict)
    trend_context: dict = field(default_factory=dict)
    breadth_context: dict = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_standard(self, module: str = "market_regime") -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput(
            module=module,
            latency_ms=self.latency_ms,
            data={
                "regime": self.regime,
                "confidence": self.confidence,
                "stability": self.stability,
                "risk_level": self.risk_level,
            },
            context={
                "transitions": self.transitions,
                "volatility": self.volatility_context,
                "trend": self.trend_context,
                "breadth": self.breadth_context,
            },
        )


@dataclass
class StandardResearchFinding:
    question: str = ""
    answer: str = ""
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    related_findings: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_standard(self, module: str = "research_assistant") -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput(
            module=module,
            latency_ms=self.latency_ms,
            data={
                "question": self.question,
                "answer": self.answer,
                "confidence": self.confidence,
            },
            context={
                "sources": self.sources,
                "recommendations": self.recommendations,
                "related_findings": self.related_findings,
            },
        )


@dataclass
class StandardReflectionReport:
    period: str = ""
    total_trades_analyzed: int = 0
    patterns_found: list[dict] = field(default_factory=list)
    degradation_signals: list[dict] = field(default_factory=list)
    regime_mismatches: list[dict] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_standard(self, module: str = "reflection_engine") -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput(
            module=module,
            latency_ms=self.latency_ms,
            data={
                "period": self.period,
                "total_trades_analyzed": self.total_trades_analyzed,
                "patterns_found_count": len(self.patterns_found),
                "degradation_signals_count": len(self.degradation_signals),
                "regime_mismatches_count": len(self.regime_mismatches),
            },
            context={
                "patterns": self.patterns_found,
                "degradation": self.degradation_signals,
                "regime_mismatches": self.regime_mismatches,
                "recommendations": self.recommendations,
            },
        )


class OutputStandardizer:
    @staticmethod
    def standardize(data: Any, module: str = "", latency_ms: float = 0) -> StandardIntelligenceOutput:
        if isinstance(data, StandardIntelligenceOutput):
            return data
        if isinstance(data, StandardTradeExplanation):
            return data.to_standard(module)
        if isinstance(data, StandardPortfolioAnalysis):
            return data.to_standard(module)
        if isinstance(data, StandardRegimeAnalysis):
            return data.to_standard(module)
        if isinstance(data, StandardResearchFinding):
            return data.to_standard(module)
        if isinstance(data, StandardReflectionReport):
            return data.to_standard(module)
        if isinstance(data, dict):
            return StandardIntelligenceOutput(
                module=module, latency_ms=latency_ms, data=data
            )
        return StandardIntelligenceOutput(
            module=module, latency_ms=latency_ms,
            data={"result": str(data)},
        )

    @staticmethod
    def error(module: str, error: str, latency_ms: float = 0) -> StandardIntelligenceOutput:
        return StandardIntelligenceOutput.error_output(module, error, latency_ms)

    @staticmethod
    def to_response(output: StandardIntelligenceOutput) -> dict:
        return output.to_dict()
