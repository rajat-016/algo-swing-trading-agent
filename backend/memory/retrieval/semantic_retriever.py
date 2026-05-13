from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from memory.chromadb.collection_manager import MemoryCollectionManager
from memory.embeddings.memory_embedder import MemoryEmbedder
from memory.retrieval.audit import RetrievalAuditor
from memory.retrieval.hybrid_search import hybrid_search
from memory.retrieval.ranking import rank_results
from memory.retrieval.scoring import (
    clip_relevance,
    compute_cross_collection_similarity,
    normalize_scores,
)
from core.monitoring import get_metrics_collector
from core.governance import get_governance_manager
from memory.schemas.memory_schemas import (
    MarketMemory,
    MemoryFilter,
    MemoryType,
    QueryIntent,
    ResearchMemory,
    SearchResult,
    TradeMemory,
)


class SemanticRetriever:
    def __init__(
        self,
        collection_manager: Optional[MemoryCollectionManager] = None,
        memory_embedder: Optional[MemoryEmbedder] = None,
        auditor: Optional[RetrievalAuditor] = None,
    ):
        self._collections = collection_manager or MemoryCollectionManager()
        self._embedder = memory_embedder or MemoryEmbedder()
        self._auditor = auditor or RetrievalAuditor()
        self._metrics = get_metrics_collector()
        self._governance = get_governance_manager()
        self._initialized = False

    async def initialize(self):
        await self._collections.initialize()
        self._initialized = True
        logger.info("SemanticRetriever initialized")

    def _require_initialized(self):
        if not self._initialized:
            raise RuntimeError("SemanticRetriever not initialized. Call initialize() first.")

    def _resolve_memory_types(
        self, memory_filter: Optional[MemoryFilter] = None
    ) -> list[MemoryType]:
        if memory_filter and memory_filter.memory_type:
            return [memory_filter.memory_type]
        return list(MemoryType)

    def _validate_integrity(
        self, results: list[SearchResult]
    ) -> list[SearchResult]:
        valid: list[SearchResult] = []
        for r in results:
            ok, _ = self._governance.integrity.validate_on_retrieve(
                r.metadata, r.text
            )
            if ok:
                valid.append(r)
        return valid

    def _apply_safety_check(self, query: str) -> tuple[bool, Optional[str]]:
        safe, check_result = self._governance.safety.check_query(query)
        if not safe:
            reason = str(check_result.get("checks", {}))
            self._governance.log_ai_output(
                action="retrieval_blocked",
                component="semantic_retriever",
                details={"query": query[:200], "reason": reason},
                status="blocked",
                error=reason,
            )
            return False, reason
        return True, None

    async def store_trade(self, trade: TradeMemory):
        self._require_initialized()
        start = time.monotonic()
        try:
            doc_id, embedding, metadata = await self._embedder.embed_trade(trade)
            text = trade.to_embedding_text()
            self._collections.add_memory(
                MemoryType.TRADE,
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_trade", latency * 1000)
            logger.debug(f"Stored trade memory: {doc_id}")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_trade", str(e))
            raise

    async def store_trades(self, trades: list[TradeMemory]):
        self._require_initialized()
        if not trades:
            return
        start = time.monotonic()
        try:
            ids, embeddings, metadatas, texts = await self._embedder.embed_trades(trades)
            self._collections.add_memory(
                MemoryType.TRADE,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_trades", latency * 1000)
            logger.info(f"Stored {len(trades)} trade memories")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_trades", str(e))
            raise

    async def store_market(self, market: MarketMemory):
        self._require_initialized()
        start = time.monotonic()
        try:
            doc_id, embedding, metadata = await self._embedder.embed_market(market)
            text = market.to_embedding_text()
            self._collections.add_memory(
                MemoryType.MARKET,
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_market", latency * 1000)
            logger.debug(f"Stored market memory: {doc_id}")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_market", str(e))
            raise

    async def store_markets(self, markets: list[MarketMemory]):
        self._require_initialized()
        if not markets:
            return
        start = time.monotonic()
        try:
            ids, embeddings, metadatas, texts = await self._embedder.embed_markets(markets)
            self._collections.add_memory(
                MemoryType.MARKET,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_markets", latency * 1000)
            logger.info(f"Stored {len(markets)} market memories")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_markets", str(e))
            raise

    async def store_research(self, research: ResearchMemory):
        self._require_initialized()
        start = time.monotonic()
        try:
            doc_id, embedding, metadata = await self._embedder.embed_research(research)
            text = research.to_embedding_text()
            self._collections.add_memory(
                MemoryType.RESEARCH,
                documents=[text],
                embeddings=[embedding],
                metadatas=[metadata],
                ids=[doc_id],
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_research", latency * 1000)
            logger.debug(f"Stored research memory: {doc_id}")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_research", str(e))
            raise

    async def store_researches(self, researches: list[ResearchMemory]):
        self._require_initialized()
        if not researches:
            return
        start = time.monotonic()
        try:
            ids, embeddings, metadatas, texts = await self._embedder.embed_researches(researches)
            self._collections.add_memory(
                MemoryType.RESEARCH,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
            latency = time.monotonic() - start
            self._metrics.record_latency("retriever.store_researches", latency * 1000)
            logger.info(f"Stored {len(researches)} research memories")
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("retriever.store_researches", str(e))
            raise

    async def search(
        self,
        query: str,
        memory_filter: Optional[MemoryFilter] = None,
        n_results: int = 10,
    ) -> list[SearchResult]:
        self._require_initialized()
        start = time.monotonic()
        error = None

        safe, safe_reason = self._apply_safety_check(query)
        if not safe:
            self._auditor.log_search(
                query=query, results=[], latency_ms=0,
                mem_types=[], n_requested=n_results,
                error=f"Safety check failed: {safe_reason}",
            )
            return []

        mem_types = self._resolve_memory_types(memory_filter)
        query_embedding = await self._embedder._service.embed(query)
        where_clause = memory_filter.to_chroma_where() if memory_filter else None
        effective_n = memory_filter.max_results if memory_filter else n_results
        offset = memory_filter.offset if memory_filter else 0

        all_results: list[SearchResult] = []
        for mem_type in mem_types:
            try:
                chroma_result = self._collections.query(
                    mem_type,
                    query_embedding,
                    n_results=effective_n + offset,
                    where=where_clause,
                )
                results = SearchResult.from_chroma_batch(chroma_result)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Query failed for {mem_type.value}: {e}")
                if error is None:
                    error = str(e)

        if all_results:
            all_results = self._validate_integrity(all_results)
            all_results = normalize_scores(all_results, "relevance_score")
            all_results = compute_cross_collection_similarity(all_results)
            all_results = rank_results(all_results, memory_filter.ranking_config if memory_filter else None)

        all_results.sort(key=lambda r: r.ranked_score or r.relevance_score, reverse=True)
        paginated = all_results[offset:offset + effective_n]

        elapsed = time.monotonic() - start
        if error:
            self._metrics.record_error("retriever.search", error)
        else:
            self._metrics.record_latency("retriever.search", elapsed * 1000)
        self._auditor.log_search(
            query=query,
            results=paginated,
            latency_ms=elapsed * 1000,
            mem_types=mem_types,
            n_requested=effective_n,
            filters_applied=memory_filter.model_dump(exclude_none=True) if memory_filter else None,
            error=error,
        )

        self._governance.log_ai_output(
            action="semantic_search",
            component="semantic_retriever",
            details={
                "query": query[:200],
                "n_requested": effective_n,
                "n_returned": len(paginated),
                "mem_types": [m.value for m in mem_types],
            },
            start_time=start,
            status="error" if error else "success",
            error=error,
        )

        logger.info(
            f"Semantic search '{query[:50]}' returned "
            f"{len(paginated)} results in {elapsed:.3f}s"
        )
        return paginated

    async def search_by_text(
        self,
        query: str,
        memory_filter: Optional[MemoryFilter] = None,
        n_results: int = 10,
    ) -> list[SearchResult]:
        self._require_initialized()
        start = time.monotonic()
        error = None

        safe, safe_reason = self._apply_safety_check(query)
        if not safe:
            self._auditor.log_search(
                query=query, results=[], latency_ms=0,
                mem_types=[], n_requested=n_results,
                error=f"Safety check failed: {safe_reason}",
            )
            return []

        mem_types = self._resolve_memory_types(memory_filter)
        where_clause = memory_filter.to_chroma_where() if memory_filter else None
        effective_n = memory_filter.max_results if memory_filter else n_results
        offset = memory_filter.offset if memory_filter else 0

        all_results: list[SearchResult] = []
        for mem_type in mem_types:
            try:
                chroma_result = self._collections.query_by_text(
                    mem_type,
                    query,
                    n_results=effective_n + offset,
                    where=where_clause,
                )
                results = SearchResult.from_chroma_batch(chroma_result)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Text query failed for {mem_type.value}: {e}")
                if error is None:
                    error = str(e)

        if all_results:
            all_results = self._validate_integrity(all_results)
            all_results = normalize_scores(all_results, "relevance_score")
            all_results = rank_results(all_results, memory_filter.ranking_config if memory_filter else None)

        all_results.sort(key=lambda r: r.ranked_score or r.relevance_score, reverse=True)
        paginated = all_results[offset:offset + effective_n]

        elapsed = time.monotonic() - start
        if error:
            self._metrics.record_error("retriever.search_by_text", error)
        else:
            self._metrics.record_latency("retriever.search_by_text", elapsed * 1000)
        self._auditor.log_search(
            query=query,
            results=paginated,
            latency_ms=elapsed * 1000,
            mem_types=mem_types,
            n_requested=effective_n,
            filters_applied=memory_filter.model_dump(exclude_none=True) if memory_filter else None,
            error=error,
        )

        self._governance.log_ai_output(
            action="text_search",
            component="semantic_retriever",
            details={
                "query": query[:200],
                "n_requested": effective_n,
                "n_returned": len(paginated),
                "mem_types": [m.value for m in mem_types],
            },
            start_time=start,
            status="error" if error else "success",
            error=error,
        )

        logger.info(
            f"Text search '{query[:50]}' returned "
            f"{len(paginated)} results in {elapsed:.3f}s"
        )
        return paginated

    async def advanced_search(
        self,
        query: str,
        memory_filter: Optional[MemoryFilter] = None,
        n_results: int = 10,
        use_hybrid: bool = False,
        min_relevance: float = 0.0,
    ) -> list[SearchResult]:
        self._require_initialized()
        start = time.monotonic()
        error = None

        safe, safe_reason = self._apply_safety_check(query)
        if not safe:
            self._auditor.log_search(
                query=query, results=[], latency_ms=0,
                mem_types=[], n_requested=n_results,
                error=f"Safety check failed: {safe_reason}",
            )
            return []

        mem_types = self._resolve_memory_types(memory_filter)
        query_embedding = await self._embedder._service.embed(query)
        where_clause = memory_filter.to_chroma_where() if memory_filter else None
        effective_n = memory_filter.max_results if memory_filter else n_results
        offset = memory_filter.offset if memory_filter else 0

        all_results: list[SearchResult] = []

        for mem_type in mem_types:
            try:
                chroma_result = self._collections.query(
                    mem_type,
                    query_embedding,
                    n_results=effective_n + offset,
                    where=where_clause,
                )
                results = SearchResult.from_chroma_batch(chroma_result)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Vector query failed for {mem_type.value}: {e}")
                if error is None:
                    error = str(e)

        if use_hybrid and memory_filter and memory_filter.hybrid_config.enabled:
            try:
                hybrid_results = await hybrid_search(
                    query=query,
                    query_embedding=query_embedding,
                    collection_manager=self._collections,
                    mem_types=mem_types,
                    memory_filter=memory_filter,
                    n_results=effective_n + offset,
                )
                hybrid_map = {r.id: r for r in hybrid_results}
                for r in all_results:
                    if r.id in hybrid_map:
                        r.hybrid_score = hybrid_map[r.id].hybrid_score
            except Exception as e:
                logger.error(f"Hybrid search failed: {e}")
                if error is None:
                    error = str(e)

        if all_results:
            all_results = self._validate_integrity(all_results)
            all_results = normalize_scores(all_results, "relevance_score")
            all_results = compute_cross_collection_similarity(all_results)
            all_results = rank_results(all_results, memory_filter.ranking_config if memory_filter else None)

        all_results.sort(key=lambda r: r.ranked_score or r.relevance_score, reverse=True)
        paginated = all_results[offset:offset + effective_n]

        if min_relevance > 0.0:
            paginated = clip_relevance(paginated, threshold=min_relevance)

        elapsed = time.monotonic() - start
        if error:
            self._metrics.record_error("retriever.advanced_search", error)
        else:
            self._metrics.record_latency("retriever.advanced_search", elapsed * 1000)
        self._auditor.log_search(
            query=query,
            results=paginated,
            latency_ms=elapsed * 1000,
            mem_types=mem_types,
            n_requested=effective_n,
            filters_applied=memory_filter.model_dump(exclude_none=True) if memory_filter else None,
            error=error,
        )

        self._governance.log_ai_output(
            action="advanced_search",
            component="semantic_retriever",
            details={
                "query": query[:200],
                "n_requested": effective_n,
                "n_returned": len(paginated),
                "mem_types": [m.value for m in mem_types],
                "use_hybrid": use_hybrid,
            },
            start_time=start,
            status="error" if error else "success",
            error=error,
        )

        logger.info(
            f"Advanced search '{query[:50]}' returned "
            f"{len(paginated)} results in {elapsed:.3f}s"
        )
        return paginated

    async def search_by_intent(
        self,
        query: str,
        n_results: int = 10,
        use_hybrid: bool = False,
        min_relevance: float = 0.0,
    ) -> list[SearchResult]:
        intent = QueryIntent.parse(query)
        memory_filter = MemoryFilter.from_query_intent(intent)
        return await self.advanced_search(
            query=query,
            memory_filter=memory_filter,
            n_results=n_results,
            use_hybrid=use_hybrid,
            min_relevance=min_relevance,
        )

    async def get_memory_stats(self) -> dict[str, Any]:
        self._require_initialized()
        stats = {}
        for mem_type in MemoryType:
            try:
                stats[mem_type.value] = {
                    "count": self._collections.count(mem_type),
                    "collection": self._collections.get_collection_name(mem_type),
                }
            except Exception as e:
                stats[mem_type.value] = {"error": str(e)}
        stats["embedding_cache"] = self._embedder.cache_stats()
        stats["audit"] = self._auditor.get_stats()
        return stats

    @property
    def auditor(self) -> RetrievalAuditor:
        return self._auditor

    @property
    def is_ready(self) -> bool:
        return self._initialized
