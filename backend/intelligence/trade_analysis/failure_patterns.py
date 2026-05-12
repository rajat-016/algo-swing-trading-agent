import asyncio
from typing import Any, Optional
from core.logging import logger


PATTERN_CATEGORIES: dict[str, list[str]] = {
    "regime_mismatch": ["regime_mismatch", "mismatch", "direction conflict", "regime risk"],
    "volatility_expansion": ["volatility_expansion", "vol spike", "high volatility", "atr expansion"],
    "weak_momentum": ["weak_momentum", "low adx", "weak trend", "momentum divergence", "declining volume"],
    "poor_confirmations": ["weak_confirmations", "low confidence", "thin margin", "conflicting features"],
    "stop_loss": ["stop_loss", "sl trigger", "stop loss"],
    "regime_instability": ["regime_instability", "unstable", "transitioning", "regime flip"],
    "feature_alignment": ["feature_alignment", "inappropriate features", "missing features"],
}


class FailurePatternAnalyzer:
    def __init__(self):
        self._retriever = None

    def _get_retriever(self):
        if self._retriever is not None:
            return self._retriever
        try:
            from memory.retrieval.semantic_retriever import SemanticRetriever
            retriever = SemanticRetriever()
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.ensure_future(retriever.initialize())
                else:
                    loop.run_until_complete(retriever.initialize())
            except RuntimeError:
                asyncio.run(retriever.initialize())
            self._retriever = retriever
            return self._retriever
        except Exception as e:
            logger.warning(f"SemanticRetriever not available: {e}")
            return None

    def analyze_patterns(self, symbol: Optional[str] = None,
                          max_results: int = 50) -> dict:
        retriever = self._get_retriever()
        if retriever is None:
            return {"patterns_found": 0, "patterns": [], "error": "Retriever not available"}

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType

            query = "failed trade stop_loss hit loss"
            if symbol:
                query = f"{symbol} {query}"

            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                outcomes=["stop_loss_hit", "failed"],
                max_results=max_results,
            )

            loop = asyncio.get_event_loop()
            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    retriever.search(query, memory_filter=memory_filter, n_results=max_results),
                    loop,
                )
                results = future.result(timeout=5)
            else:
                results = loop.run_until_complete(
                    retriever.search(query, memory_filter=memory_filter, n_results=max_results)
                )
        except RuntimeError:
            try:
                from memory.schemas.memory_schemas import MemoryFilter, MemoryType
                memory_filter = MemoryFilter(
                    memory_type=MemoryType.TRADE,
                    ticker=symbol,
                    outcomes=["stop_loss_hit", "failed"],
                    max_results=max_results,
                )
                results = asyncio.run(
                    retriever.search(query, memory_filter=memory_filter, n_results=max_results)
                )
            except Exception as e:
                logger.warning(f"Pattern search failed: {e}")
                return {"patterns_found": 0, "patterns": [], "error": str(e)}
        except Exception as e:
            logger.warning(f"Pattern search failed: {e}")
            return {"patterns_found": 0, "patterns": [], "error": str(e)}

        return self._classify_patterns(results, symbol)

    def _classify_patterns(self, results: list, symbol: Optional[str] = None) -> dict:
        if not results:
            return {"patterns_found": 0, "patterns": []}

        pattern_hits: dict[str, int] = {cat: 0 for cat in PATTERN_CATEGORIES}
        trades_by_pattern: dict[str, list[dict]] = {cat: [] for cat in PATTERN_CATEGORIES}
        regime_counts: dict[str, int] = {}
        outcome_counts: dict[str, int] = {}
        total = len(results)

        for r in results:
            meta = r.metadata or {}
            text_lower = r.text.lower() if r.text else ""

            outcome = meta.get("outcome", "unknown")
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

            regime = meta.get("market_regime", "unknown")
            if regime != "unknown":
                regime_counts[regime] = regime_counts.get(regime, 0) + 1

            for cat, keywords in PATTERN_CATEGORIES.items():
                matched = any(kw in text_lower for kw in keywords)
                if matched:
                    pattern_hits[cat] += 1
                    if len(trades_by_pattern[cat]) < 5:
                        trades_by_pattern[cat].append({
                            "trade_id": meta.get("trade_id", r.id),
                            "ticker": meta.get("ticker", "unknown"),
                            "outcome": outcome,
                            "regime": regime,
                        })

        sorted_patterns = sorted(
            [{"category": cat, "count": cnt, "frequency": round(cnt / total, 4)}
             for cat, cnt in pattern_hits.items() if cnt > 0],
            key=lambda x: x["count"],
            reverse=True,
        )

        recurring = [
            p for p in sorted_patterns
            if p["frequency"] >= 0.3
        ]

        if symbol:
            top_regime = max(regime_counts.items(), key=lambda x: x[1]) if regime_counts else None
        else:
            top_regime = None

        return {
            "patterns_found": len(sorted_patterns),
            "total_trades_analyzed": total,
            "symbol": symbol,
            "patterns": sorted_patterns,
            "recurring_patterns": recurring,
            "most_common_regime": top_regime[0] if top_regime else None,
            "regime_breakdown": dict(sorted(regime_counts.items(), key=lambda x: x[1], reverse=True)),
            "outcome_breakdown": outcome_counts,
            "sample_trades_by_pattern": {k: v for k, v in trades_by_pattern.items() if v},
        }
