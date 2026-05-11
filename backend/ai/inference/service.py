import asyncio
import time
from typing import Callable, Optional

from loguru import logger

from ai.config.settings import ai_settings
from ai.inference.chromadb_client import ChromaDBClient
from ai.inference.duckdb_setup import DuckDBAnalytics
from ai.inference.embedding_service import EmbeddingService
from ai.llm.client import OllamaClient
from ai.llm.models import CHAT_CONFIGS, ModelConfig
from ai.orchestration.circuit_breaker import AICircuitBreaker
from ai.prompts.registry import registry as prompt_registry


class InferenceService:
    def __init__(
        self,
        ollama: Optional[OllamaClient] = None,
        embedding: Optional[EmbeddingService] = None,
        chroma: Optional[ChromaDBClient] = None,
        duck: Optional[DuckDBAnalytics] = None,
    ):
        self.ollama = ollama or OllamaClient()
        self.embedding = embedding or EmbeddingService(self.ollama)
        self.chroma = chroma or ChromaDBClient()
        self.duck = duck or DuckDBAnalytics()
        self.circuit_breaker = AICircuitBreaker(
            threshold=ai_settings.inference_circuit_breaker_threshold,
            reset_seconds=ai_settings.inference_circuit_breaker_reset_seconds,
        )
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        await self.chroma.initialize()
        await self.duck.initialize()
        self._initialized = True
        logger.info("InferenceService initialized")

    async def generate(
        self,
        prompt: str,
        config_key: str = "default",
        **kwargs,
    ) -> str:
        if not self.circuit_breaker.allow_request():
            raise RuntimeError("AI inference circuit breaker is open")

        model_config = CHAT_CONFIGS.get(config_key, ModelConfig())
        for k, v in kwargs.items():
            if hasattr(model_config, k):
                setattr(model_config, k, v)

        start = time.monotonic()
        try:
            result = await self.ollama.generate(prompt, model_config=model_config)
            latency = time.monotonic() - start
            self.circuit_breaker.record_success()
            logger.debug(f"AI generate: {latency:.2f}s, prompt={len(prompt)} chars")
            return result
        except Exception as e:
            latency = time.monotonic() - start
            self.circuit_breaker.record_failure()
            logger.error(f"AI generate failed after {latency:.2f}s: {e}")
            raise

    async def chat(
        self,
        messages: list[dict],
        config_key: str = "default",
        **kwargs,
    ) -> str:
        if not self.circuit_breaker.allow_request():
            raise RuntimeError("AI inference circuit breaker is open")

        model_config = CHAT_CONFIGS.get(config_key, ModelConfig())
        for k, v in kwargs.items():
            if hasattr(model_config, k):
                setattr(model_config, k, v)

        start = time.monotonic()
        try:
            result = await self.ollama.chat(messages, model_config=model_config)
            latency = time.monotonic() - start
            self.circuit_breaker.record_success()
            logger.debug(f"AI chat: {latency:.2f}s, {len(messages)} messages")
            return result
        except Exception as e:
            latency = time.monotonic() - start
            self.circuit_breaker.record_failure()
            logger.error(f"AI chat failed after {latency:.2f}s: {e}")
            raise

    async def embed(
        self,
        text: str,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> list[float]:
        return await self.embedding.embed(text, use_cache=use_cache, model=model)

    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[list[float]]:
        return await self.embedding.embed_batch(
            texts,
            use_cache=use_cache,
            model=model,
            progress_callback=progress_callback,
        )

    async def embed_documents(
        self,
        documents: list[dict],
        text_key: str = "text",
        use_cache: bool = True,
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        auto_metadata: bool = True,
    ) -> list[dict]:
        return await self.embedding.embed_documents(
            documents,
            text_key=text_key,
            use_cache=use_cache,
            model=model,
            progress_callback=progress_callback,
            auto_metadata=auto_metadata,
        )

    async def semantic_search(
        self,
        collection: str,
        query: str,
        n_results: int = 10,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        query_embedding = await self.embed(query)
        return self.chroma.query(
            collection_name=collection,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
            where_document=where_document,
        )

    async def store_memory(
        self,
        collection: str,
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: Optional[list[dict]] = None,
        ids: Optional[list[str]] = None,
    ):
        self.chroma.add_documents(
            collection_name=collection,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    async def store_with_metadata(
        self,
        collection: str,
        documents: list[dict],
        text_key: str = "text",
        use_cache: bool = True,
        upsert: bool = False,
    ) -> int:
        enriched = await self.embed_documents(
            documents, text_key=text_key, use_cache=use_cache, auto_metadata=True,
        )
        texts = [d[text_key] for d in enriched]
        embeddings = [d["embedding"] for d in enriched]
        metadatas = [d.get("metadata", {}) for d in enriched]
        ids = [d.get("id") for d in enriched]

        if upsert:
            self.chroma.upsert_documents(
                collection_name=collection,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        else:
            self.chroma.add_documents(
                collection_name=collection,
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )
        return len(texts)

    async def render_and_generate(
        self,
        prompt_name: str,
        config_key: str = "default",
        **kwargs,
    ) -> str:
        prompt = prompt_registry.render(prompt_name, **kwargs)
        return await self.generate(prompt, config_key=config_key)

    def cache_stats(self) -> dict:
        return self.embedding.cache_stats()

    def clear_embedding_cache(self):
        self.embedding.clear_cache()

    async def check_health(self) -> dict:
        ollama_ok = await self.ollama.check_health()
        return {
            "ollama": ollama_ok,
            "chromadb": self.chroma.is_ready,
            "duckdb": self.duck.is_ready,
            "circuit_breaker": self.circuit_breaker.state,
            "initialized": self._initialized,
            "embedding_cache": self.cache_stats(),
        }

    async def close(self):
        await self.ollama.close()
        await self.chroma.close()
        await self.duck.close()
        self._initialized = False
        logger.info("InferenceService closed")
