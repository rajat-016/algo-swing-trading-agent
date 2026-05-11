from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from ai.inference.embedding_service import EmbeddingService
from memory.schemas.memory_schemas import (
    MarketMemory,
    MemoryType,
    ResearchMemory,
    TradeMemory,
)


class MemoryEmbedder:
    def __init__(self, embedding_service: Optional[EmbeddingService] = None):
        self._service = embedding_service or EmbeddingService()
        self._default_model = self._service._model

    async def embed_trade(
        self,
        trade: TradeMemory,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[str, list[float], dict[str, Any]]:
        text = trade.to_embedding_text()
        embedding = await self._service.embed(text, use_cache=use_cache, model=model)
        metadata = trade.to_metadata()
        metadata["memory_type"] = MemoryType.TRADE.value
        return trade.collection_id(), embedding, metadata

    async def embed_trades(
        self,
        trades: list[TradeMemory],
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[list[str], list[list[float]], list[dict[str, Any]], list[str]]:
        ids = []
        texts = []
        metadatas = []
        for t in trades:
            ids.append(t.collection_id())
            texts.append(t.to_embedding_text())
            metadatas.append(t.to_metadata())
        for m in metadatas:
            m["memory_type"] = MemoryType.TRADE.value
        embeddings = await self._service.embed_batch(texts, use_cache=use_cache, model=model)
        return ids, embeddings, metadatas, texts

    async def embed_market(
        self,
        market: MarketMemory,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[str, list[float], dict[str, Any]]:
        text = market.to_embedding_text()
        embedding = await self._service.embed(text, use_cache=use_cache, model=model)
        metadata = market.to_metadata()
        metadata["memory_type"] = MemoryType.MARKET.value
        return market.collection_id(), embedding, metadata

    async def embed_markets(
        self,
        markets: list[MarketMemory],
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[list[str], list[list[float]], list[dict[str, Any]], list[str]]:
        ids = []
        texts = []
        metadatas = []
        for m in markets:
            ids.append(m.collection_id())
            texts.append(m.to_embedding_text())
            metadatas.append(m.to_metadata())
        for m in metadatas:
            m["memory_type"] = MemoryType.MARKET.value
        embeddings = await self._service.embed_batch(texts, use_cache=use_cache, model=model)
        return ids, embeddings, metadatas, texts

    async def embed_research(
        self,
        research: ResearchMemory,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[str, list[float], dict[str, Any]]:
        text = research.to_embedding_text()
        embedding = await self._service.embed(text, use_cache=use_cache, model=model)
        metadata = research.to_metadata()
        metadata["memory_type"] = MemoryType.RESEARCH.value
        return research.collection_id(), embedding, metadata

    async def embed_researches(
        self,
        researches: list[ResearchMemory],
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> tuple[list[str], list[list[float]], list[dict[str, Any]], list[str]]:
        ids = []
        texts = []
        metadatas = []
        for r in researches:
            ids.append(r.collection_id())
            texts.append(r.to_embedding_text())
            metadatas.append(r.to_metadata())
        for m in metadatas:
            m["memory_type"] = MemoryType.RESEARCH.value
        embeddings = await self._service.embed_batch(texts, use_cache=use_cache, model=model)
        return ids, embeddings, metadatas, texts

    def cache_stats(self) -> dict:
        return self._service.cache_stats()

    def clear_cache(self):
        self._service.clear_cache()

    @property
    def default_model(self) -> str:
        return self._default_model
