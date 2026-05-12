import asyncio
from typing import Any, Optional
from core.logging import logger


class SimilarTradeRetriever:
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

    def find_similar_by_outcome(self, symbol: str, outcome: str,
                                 max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade {symbol} {outcome}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                outcomes=[outcome] if outcome else None,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by outcome search failed: {e}")
            return None

    def find_similar_by_regime(self, regime: str, symbol: Optional[str] = None,
                                max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade regime {regime}"
            if symbol:
                query = f"{symbol} {query}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                market_regime=regime,
                ticker=symbol,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by regime search failed: {e}")
            return None

    def find_similar_by_features(self, feature_names: list[str],
                                  symbol: Optional[str] = None,
                                  max_results: int = 5) -> Optional[dict]:
        retriever = self._get_retriever()
        if retriever is None:
            return None

        try:
            from memory.schemas.memory_schemas import MemoryFilter, MemoryType
            query = f"trade features {' '.join(feature_names[:5])}"
            if symbol:
                query = f"{symbol} {query}"
            memory_filter = MemoryFilter(
                memory_type=MemoryType.TRADE,
                ticker=symbol,
                max_results=max_results,
            )
            return self._execute_search(retriever, query, memory_filter, max_results)
        except Exception as e:
            logger.warning(f"Similar by features search failed: {e}")
            return None

    def find_all_similar(self, symbol: str, regime: Optional[str] = None,
                          outcome: Optional[str] = None,
                          feature_names: Optional[list] = None,
                          max_results: int = 5) -> dict:
        all_trades = {}
        seen_ids = set()
        queries_run = 0

        if outcome:
            result = self.find_similar_by_outcome(symbol, outcome, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        if regime:
            result = self.find_similar_by_regime(regime, symbol, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        if feature_names:
            result = self.find_similar_by_features(feature_names, symbol, max_results)
            if result:
                for t in result.get("similar_trades", []):
                    tid = t.get("trade_id")
                    if tid and tid not in seen_ids:
                        seen_ids.add(tid)
                        all_trades[tid] = t
                queries_run += 1

        sorted_trades = sorted(
            all_trades.values(),
            key=lambda x: x.get("relevance_score", 0),
            reverse=True,
        )[:max_results]

        return {
            "similar_trades_found": len(sorted_trades),
            "similar_trades": sorted_trades,
            "queries_run": queries_run,
        }

    def _execute_search(self, retriever, query: str, memory_filter,
                         max_results: int) -> dict:
        try:
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
            results = asyncio.run(
                retriever.search(query, memory_filter=memory_filter, n_results=max_results)
            )

        if not results:
            return {"similar_trades_found": 0, "similar_trades": []}

        trades = []
        for r in results:
            meta = r.metadata or {}
            trades.append({
                "trade_id": meta.get("trade_id", r.id),
                "ticker": meta.get("ticker", "unknown"),
                "outcome": meta.get("outcome", "unknown"),
                "confidence": meta.get("confidence"),
                "regime": meta.get("market_regime"),
                "relevance_score": round(r.relevance_score, 4),
            })

        trades.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        return {
            "similar_trades_found": len(trades),
            "similar_trades": trades[:max_results],
        }
