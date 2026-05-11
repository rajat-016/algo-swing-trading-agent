from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from ai.inference.chromadb_client import ChromaDBClient
from memory.schemas.memory_schemas import MemoryType


class MemoryCollectionManager:
    COLLECTION_NAMES = {
        MemoryType.TRADE: "trade_memory",
        MemoryType.MARKET: "market_memory",
        MemoryType.RESEARCH: "research_memory",
    }

    COLLECTION_METADATA = {
        MemoryType.TRADE: {
            "description": "Trade reasoning, failures, and observations",
            "hnsw:space": "cosine",
        },
        MemoryType.MARKET: {
            "description": "Market regime transitions, volatility events, anomalies",
            "hnsw:space": "cosine",
        },
        MemoryType.RESEARCH: {
            "description": "Feature observations, experiment findings, strategy insights",
            "hnsw:space": "cosine",
        },
    }

    def __init__(self, chromadb_client: Optional[ChromaDBClient] = None):
        self._client = chromadb_client or ChromaDBClient()
        self._initialized = False

    async def initialize(self):
        if not self._client.is_ready:
            await self._client.initialize()
        for mem_type in MemoryType:
            self._get_or_create(mem_type)
        self._initialized = True
        logger.info("Memory collections initialized")

    def _require_initialized(self):
        if not self._initialized:
            raise RuntimeError("MemoryCollectionManager not initialized. Call initialize() first.")

    def _get_or_create(self, mem_type: MemoryType):
        name = self.COLLECTION_NAMES[mem_type]
        meta = self.COLLECTION_METADATA[mem_type]
        return self._client.get_or_create_collection(name, metadata=meta)

    def get_collection_name(self, mem_type: MemoryType) -> str:
        return self.COLLECTION_NAMES[mem_type]

    def list_collections(self) -> list[str]:
        self._require_initialized()
        return self._client.list_collections()

    def count(self, mem_type: MemoryType) -> int:
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        return self._client.count(name)

    def peek(self, mem_type: MemoryType, limit: int = 10) -> dict:
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        return self._client.peek(name, limit=limit)

    def add_memory(
        self,
        mem_type: MemoryType,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        self._client.add_documents(name, documents, embeddings, metadatas=metadatas, ids=ids)

    def upsert_memory(
        self,
        mem_type: MemoryType,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        self._client.upsert_documents(name, documents, embeddings, metadatas=metadatas, ids=ids)

    def query(
        self,
        mem_type: MemoryType,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        return self._client.query(name, query_embedding, n_results=n_results, where=where, where_document=where_document)

    def query_by_text(
        self,
        mem_type: MemoryType,
        query_text: str,
        n_results: int = 10,
        where: Optional[dict] = None,
    ) -> dict:
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        return self._client.query_by_text(name, query_text, n_results=n_results, where=where)

    def get_by_ids(self, mem_type: MemoryType, ids: list[str]) -> dict:
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        return self._client.get_by_ids(name, ids)

    def delete_collection(self, mem_type: MemoryType):
        self._require_initialized()
        name = self.COLLECTION_NAMES[mem_type]
        self._client.delete_collection(name)

    @property
    def is_ready(self) -> bool:
        return self._initialized
