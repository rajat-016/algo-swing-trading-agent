import time
from typing import Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ContextBundle:
    regime: dict = field(default_factory=dict)
    portfolio: dict = field(default_factory=dict)
    trade_journal: dict = field(default_factory=dict)
    memory: dict = field(default_factory=dict)
    drift: dict = field(default_factory=dict)
    governance: dict = field(default_factory=dict)
    evaluation: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v}

    def merge_into(self, target: dict, prefix: str = "") -> dict:
        for key, value in self.to_dict().items():
            target_key = f"{prefix}{key}" if prefix else key
            target[target_key] = value
        return target


class ContextInjector:
    def __init__(self, inference=None, regime_service=None, portfolio_service=None,
                 journal_service=None, retriever=None, drift_service=None):
        self._inference = inference
        self._regime_service = regime_service
        self._portfolio_service = portfolio_service
        self._journal_service = journal_service
        self._retriever = retriever
        self._drift_service = drift_service

    async def get_regime_context(self) -> dict:
        if not self._regime_service:
            return {}
        try:
            current = await self._regime_service.get_current_regime()
            if current and hasattr(current, "to_dict"):
                return current.to_dict()
            if isinstance(current, dict):
                return current
            return {}
        except Exception:
            return {}

    async def get_portfolio_context(self) -> dict:
        if not self._portfolio_service:
            return {}
        try:
            analysis = await self._portfolio_service.analyze()
            if hasattr(analysis, "to_dict"):
                return analysis.to_dict()
            if isinstance(analysis, dict):
                return analysis
            return {}
        except Exception:
            return {}

    async def get_trade_context(self, symbol: str = "", limit: int = 5) -> dict:
        if not self._journal_service:
            return {}
        try:
            trades = await self._journal_service.get_recent_trades(limit=limit)
            result = {"recent_trades": trades, "total": len(trades)}
            if symbol:
                symbol_trades = [
                    t for t in trades
                    if isinstance(t, dict) and t.get("ticker", "").upper() == symbol.upper()
                ]
                result["symbol_trades"] = symbol_trades
            return result
        except Exception:
            return {}

    async def get_semantic_context(self, query: str = "", limit: int = 5) -> dict:
        if not self._retriever:
            return {}
        try:
            results = await self._retriever.search(query=query or "recent market context", limit=limit)
            return {"semantic_results": results, "total": len(results)}
        except Exception:
            return {}

    async def get_drift_context(self) -> dict:
        if not self._drift_service:
            return {}
        try:
            alerts = self._drift_service.get_alerts()
            pipeline = self._drift_service.run_full_pipeline()
            return {
                "drift_alerts": alerts if isinstance(alerts, list) else [],
                "drift_pipeline": pipeline if isinstance(pipeline, dict) else {},
            }
        except Exception:
            return {}

    async def get_all_context(self, symbol: str = "", query: str = "") -> ContextBundle:
        bundle = ContextBundle()
        bundle.regime = await self.get_regime_context()
        bundle.portfolio = await self.get_portfolio_context()
        bundle.trade_journal = await self.get_trade_context(symbol=symbol)
        bundle.memory = await self.get_semantic_context(query=query)
        bundle.drift = await self.get_drift_context()
        return bundle

    async def inject_into_kwargs(self, prompt_type: str, symbol: str = "",
                                  query: str = "", **kwargs) -> dict:
        enriched = dict(kwargs)
        context_map = {
            "market_regime": ["regime"],
            "trade_explanation": ["regime", "trade_journal", "memory"],
            "portfolio_risk": ["portfolio", "regime"],
            "research_query": ["memory", "drift", "regime"],
            "reflection": ["trade_journal", "drift", "regime"],
            "post_trade_reflection": ["regime", "trade_journal"],
            "feature_drift_analysis": ["drift", "regime"],
            "strategy_deep_compare": ["trade_journal", "drift", "regime"],
            "experiment_analysis": ["drift", "trade_journal"],
        }
        needed = context_map.get(prompt_type, [])
        if "regime" in needed:
            enriched["_regime_context"] = await self.get_regime_context()
        if "portfolio" in needed:
            enriched["_portfolio_context"] = await self.get_portfolio_context()
        if "trade_journal" in needed:
            enriched["_trade_context"] = await self.get_trade_context(symbol=symbol)
        if "memory" in needed:
            enriched["_semantic_context"] = await self.get_semantic_context(query=query or symbol)
        if "drift" in needed:
            enriched["_drift_context"] = await self.get_drift_context()
        return enriched
