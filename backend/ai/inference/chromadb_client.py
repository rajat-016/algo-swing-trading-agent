import os
from loguru import logger
from typing import Optional
from ai.config.settings import ai_settings


class ChromaDBClient:
    def __init__(self):
        self._client: Optional["chromadb.PersistentClient"] = None
        self._ready = False

    async def initialize(self):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            persist_dir = ai_settings.chromadb_persist_directory
            os.makedirs(persist_dir, exist_ok=True)

            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                ),
            )
            self._ready = True
            logger.info(f"ChromaDB initialized at {persist_dir}")
        except ImportError:
            logger.warning("chromadb not installed; vector storage unavailable")
            self._ready = False
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self._ready = False

    def _require_client(self):
        if not self._ready or self._client is None:
            raise RuntimeError("ChromaDB not initialized. Call initialize() first.")

    def get_or_create_collection(self, name: str):
        self._require_client()
        full_name = f"{ai_settings.chromadb_collection_prefix}{name}"
        return self._client.get_or_create_collection(
            name=full_name,
            metadata={"hnsw:space": "cosine"},
        )

    def list_collections(self) -> list[str]:
        self._require_client()
        return [c.name for c in self._client.list_collections()]

    def delete_collection(self, name: str):
        self._require_client()
        full_name = f"{ai_settings.chromadb_collection_prefix}{name}"
        try:
            self._client.delete_collection(full_name)
            logger.info(f"Deleted collection: {full_name}")
        except ValueError:
            logger.warning(f"Collection not found: {full_name}")

    def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        self._require_client()
        collection = self.get_or_create_collection(collection_name)
        collection.add(
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def query(
        self,
        collection_name: str,
        query_embedding: list[float],
        n_results: int = 10,
        where: Optional[dict] = None,
    ) -> dict:
        self._require_client()
        collection = self.get_or_create_collection(collection_name)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

    def count(self, collection_name: str) -> int:
        self._require_client()
        collection = self.get_or_create_collection(collection_name)
        return collection.count()

    @property
    def is_ready(self) -> bool:
        return self._ready

    async def close(self):
        self._client = None
        self._ready = False
        logger.info("ChromaDB client closed")
