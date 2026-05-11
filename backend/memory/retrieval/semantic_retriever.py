from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger

from memory.chromadb.collection_manager import MemoryCollectionManager
from memory.embeddings.memory_embedder import MemoryEmbedder
from memory.schemas.memory_schemas import (
    MarketMemory,
    MemoryFilter,
    MemoryType,
    ResearchMemory,
    SearchResult,
    TradeMemory,
)


class SemanticRetriever:
    def __init__(
        self,
        collection_manager: Optional[MemoryCollectionManager] = None,
        memory_embedder: Optional[MemoryEmbedder] = None,
    ):
        self._collections = collection_manager or MemoryCollectionManager()
        self._embedder = memory_embedder or MemoryEmbedder()
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

    async def store_trade(self, trade: TradeMemory):
        self._require_initialized()
        doc_id, embedding, metadata = await self._embedder.embed_trade(trade)
        text = trade.to_embedding_text()
        self._collections.add_memory(
            MemoryType.TRADE,
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )
        logger.debug(f"Stored trade memory: {doc_id}")

    async def store_trades(self, trades: list[TradeMemory]):
        self._require_initialized()
        if not trades:
            return
        ids, embeddings, metadatas, texts = await self._embedder.embed_trades(trades)
        self._collections.add_memory(
            MemoryType.TRADE,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Stored {len(trades)} trade memories")

    async def store_market(self, market: MarketMemory):
        self._require_initialized()
        doc_id, embedding, metadata = await self._embedder.embed_market(market)
        text = market.to_embedding_text()
        self._collections.add_memory(
            MemoryType.MARKET,
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )
        logger.debug(f"Stored market memory: {doc_id}")

    async def store_markets(self, markets: list[MarketMemory]):
        self._require_initialized()
        if not markets:
            return
        ids, embeddings, metadatas, texts = await self._embedder.embed_markets(markets)
        self._collections.add_memory(
            MemoryType.MARKET,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Stored {len(markets)} market memories")

    async def store_research(self, research: ResearchMemory):
        self._require_initialized()
        doc_id, embedding, metadata = await self._embedder.embed_research(research)
        text = research.to_embedding_text()
        self._collections.add_memory(
            MemoryType.RESEARCH,
            documents=[text],
            embeddings=[embedding],
            metadatas=[metadata],
            ids=[doc_id],
        )
        logger.debug(f"Stored research memory: {doc_id}")

    async def store_researches(self, researches: list[ResearchMemory]):
        self._require_initialized()
        if not researches:
            return
        ids, embeddings, metadatas, texts = await self._embedder.embed_researches(researches)
        self._collections.add_memory(
            MemoryType.RESEARCH,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )
        logger.info(f"Stored {len(researches)} research memories")

    async def search(
        self,
        query: str,
        memory_filter: Optional[MemoryFilter] = None,
        n_results: int = 10,
    ) -> list[SearchResult]:
        self._require_initialized()
        start = time.monotonic()
        mem_types = self._resolve_memory_types(memory_filter)
        query_embedding = await self._embedder._service.embed(query)
        where_clause = memory_filter.to_chroma_where() if memory_filter else None

        all_results: list[SearchResult] = []
        for mem_type in mem_types:
            try:
                chroma_result = self._collections.query(
                    mem_type,
                    query_embedding,
                    n_results=n_results,
                    where=where_clause,
                )
                results = SearchResult.from_chroma_batch(chroma_result)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Query failed for {mem_type.value}: {e}")

        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        max_results = (memory_filter.max_results if memory_filter else 10)
        offset = (memory_filter.offset if memory_filter else 0)
        paginated = all_results[offset:offset + max_results]

        elapsed = time.monotonic() - start
        logger.info(
            f"Semantic search '{query[:50]}...' returned "
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
        mem_types = self._resolve_memory_types(memory_filter)
        where_clause = memory_filter.to_chroma_where() if memory_filter else None

        all_results: list[SearchResult] = []
        for mem_type in mem_types:
            try:
                chroma_result = self._collections.query_by_text(
                    mem_type,
                    query,
                    n_results=n_results,
                    where=where_clause,
                )
                results = SearchResult.from_chroma_batch(chroma_result)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Text query failed for {mem_type.value}: {e}")

        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        max_results = (memory_filter.max_results if memory_filter else 10)
        offset = (memory_filter.offset if memory_filter else 0)
        paginated = all_results[offset:offset + max_results]

        elapsed = time.monotonic() - start
        logger.info(
            f"Text search '{query[:50]}...' returned "
            f"{len(paginated)} results in {elapsed:.3f}s"
        )
        return paginated

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
        return stats

    @property
    def is_ready(self) -> bool:
        return self._initialized
