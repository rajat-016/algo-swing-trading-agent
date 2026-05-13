import time
from typing import Optional, Any
from dataclasses import dataclass, field


@dataclass
class RetrievalResult:
    source: str
    data: Any = None
    latency_ms: float = 0.0
    error: Optional[str] = None
    count: int = 0

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "latency_ms": round(self.latency_ms, 2),
            "error": self.error,
            "count": self.count,
            "has_data": self.data is not None and self.count > 0,
        }


@dataclass
class MultiRetrievalResult:
    results: dict[str, RetrievalResult] = field(default_factory=dict)
    total_latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "sources": {k: v.to_dict() for k, v in self.results.items()},
            "total_latency_ms": round(self.total_latency_ms, 2),
            "available_sources": sum(1 for r in self.results.values() if r.count > 0),
            "total_sources": len(self.results),
        }


class RetrievalOrchestrator:
    def __init__(self, context_injector=None, regime_service=None,
                 portfolio_service=None, trade_explainer=None,
                 journal_service=None, retriever=None, drift_service=None,
                 reflection_service=None, research_assistant=None):
        self._context = context_injector
        self._regime = regime_service
        self._portfolio = portfolio_service
        self._explainer = trade_explainer
        self._journal = journal_service
        self._retriever = retriever
        self._drift = drift_service
        self._reflection = reflection_service
        self._research = research_assistant

    async def retrieve_market_intelligence(self) -> MultiRetrievalResult:
        result = MultiRetrievalResult()
        start = time.monotonic()

        result.results["regime"] = await self._safe_retrieve(
            "regime",
            self._regime.get_current_regime() if self._regime else None,
        )
        result.results["regime_features"] = await self._safe_retrieve(
            "regime_features",
            self._regime.get_feature_snapshot() if hasattr(self._regime, "get_feature_snapshot") and self._regime else None,
        )

        result.total_latency_ms = (time.monotonic() - start) * 1000
        return result

    async def retrieve_trade_intelligence(self, symbol: str) -> MultiRetrievalResult:
        result = MultiRetrievalResult()
        start = time.monotonic()

        result.results["regime"] = await self._safe_retrieve(
            "regime",
            self._regime.get_current_regime() if self._regime else None,
        )
        result.results["explanation"] = await self._safe_retrieve(
            "explanation",
            self._explainer.explain_trade(symbol=symbol) if self._explainer else None,
        )
        result.results["similar_trades"] = await self._safe_retrieve(
            "similar_trades",
            self._retriever.search(query=symbol, limit=5) if self._retriever else None,
        )
        result.results["journal"] = await self._safe_retrieve(
            "journal",
            self._journal.get_recent_trades(limit=5) if self._journal else None,
        )

        result.total_latency_ms = (time.monotonic() - start) * 1000
        return result

    async def retrieve_portfolio_intelligence(self) -> MultiRetrievalResult:
        result = MultiRetrievalResult()
        start = time.monotonic()

        result.results["risk"] = await self._safe_retrieve(
            "risk",
            self._portfolio.analyze() if self._portfolio else None,
        )
        result.results["exposure"] = await self._safe_retrieve(
            "exposure",
            self._portfolio.analyze_exposure() if hasattr(self._portfolio, "analyze_exposure") and self._portfolio else None,
        )
        result.results["correlation"] = await self._safe_retrieve(
            "correlation",
            self._portfolio.analyze_correlation() if hasattr(self._portfolio, "analyze_correlation") and self._portfolio else None,
        )
        result.results["regime"] = await self._safe_retrieve(
            "regime",
            self._regime.get_current_regime() if self._regime else None,
        )

        result.total_latency_ms = (time.monotonic() - start) * 1000
        return result

    async def retrieve_research_intelligence(self, query: str = "") -> MultiRetrievalResult:
        result = MultiRetrievalResult()
        start = time.monotonic()

        result.results["drift"] = await self._safe_retrieve(
            "drift",
            self._drift.run_full_pipeline() if self._drift else None,
        )
        result.results["reflection"] = await self._safe_retrieve(
            "reflection",
            self._reflection.get_recent_logs(limit=5) if self._reflection else None,
        )
        result.results["semantic"] = await self._safe_retrieve(
            "semantic",
            self._retriever.search(query=query or "research context", limit=10) if self._retriever else None,
        )
        result.results["regime"] = await self._safe_retrieve(
            "regime",
            self._regime.get_current_regime() if self._regime else None,
        )

        result.total_latency_ms = (time.monotonic() - start) * 1000
        return result

    async def multi_source_retrieve(self, sources: list[str], symbol: str = "",
                                     query: str = "") -> MultiRetrievalResult:
        source_map = {
            "regime": lambda: self._safe_retrieve(
                "regime", self._regime.get_current_regime() if self._regime else None),
            "portfolio": lambda: self._safe_retrieve(
                "portfolio", self._portfolio.analyze() if self._portfolio else None),
            "exposure": lambda: self._safe_retrieve(
                "exposure", self._portfolio.analyze_exposure() if self._portfolio else None),
            "correlation": lambda: self._safe_retrieve(
                "correlation", self._portfolio.analyze_correlation() if self._portfolio else None),
            "explanation": lambda: self._safe_retrieve(
                "explanation", self._explainer.explain_trade(symbol=symbol) if self._explainer else None),
            "similar_trades": lambda: self._safe_retrieve(
                "similar_trades", self._retriever.search(query=symbol, limit=5) if self._retriever else None),
            "journal": lambda: self._safe_retrieve(
                "journal", self._journal.get_recent_trades(limit=5) if self._journal else None),
            "drift": lambda: self._safe_retrieve(
                "drift", self._drift.run_full_pipeline() if self._drift else None),
            "reflection": lambda: self._safe_retrieve(
                "reflection", self._reflection.get_recent_logs(limit=5) if self._reflection else None),
            "memory": lambda: self._safe_retrieve(
                "memory", self._retriever.search(query=query or "context", limit=10) if self._retriever else None),
        }

        result = MultiRetrievalResult()
        start = time.monotonic()
        for source in sources:
            fn = source_map.get(source)
            if fn:
                result.results[source] = await fn()
        result.total_latency_ms = (time.monotonic() - start) * 1000
        return result

    async def _safe_retrieve(self, source: str, awaitable_or_none) -> RetrievalResult:
        rr = RetrievalResult(source=source)
        start = time.monotonic()
        try:
            if awaitable_or_none is None:
                rr.error = "source unavailable"
            else:
                data = await awaitable_or_none if hasattr(awaitable_or_none, "__await__") else awaitable_or_none
                rr.data = data
                if isinstance(data, dict):
                    rr.count = len(data)
                elif isinstance(data, list):
                    rr.count = len(data)
                elif hasattr(data, "to_dict"):
                    rr.data = data.to_dict()
                    rr.count = 1
                else:
                    rr.count = 1 if data else 0
        except Exception as e:
            rr.error = str(e)
        rr.latency_ms = (time.monotonic() - start) * 1000
        return rr
