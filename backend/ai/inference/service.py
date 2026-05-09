import asyncio
import time
from loguru import logger
from typing import Optional
from ai.config.settings import ai_settings
from ai.llm.client import OllamaClient
from ai.llm.models import ModelConfig, CHAT_CONFIGS
from ai.inference.embedding_service import EmbeddingService
from ai.inference.chromadb_client import ChromaDBClient
from ai.inference.duckdb_setup import DuckDBAnalytics
from ai.prompts.registry import registry as prompt_registry
from ai.orchestration.circuit_breaker import AICircuitBreaker


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

    async def embed(self, text: str) -> list[float]:
        return await self.embedding.embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self.embedding.embed_batch(texts)

    async def semantic_search(
        self,
        collection: str,
        query: str,
        n_results: int = 10,
        where: Optional[dict] = None,
    ) -> dict:
        query_embedding = await self.embed(query)
        return self.chroma.query(
            collection_name=collection,
            query_embedding=query_embedding,
            n_results=n_results,
            where=where,
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

    async def render_and_generate(
        self,
        prompt_name: str,
        config_key: str = "default",
        **kwargs,
    ) -> str:
        prompt = prompt_registry.render(prompt_name, **kwargs)
        return await self.generate(prompt, config_key=config_key)

    async def check_health(self) -> dict:
        ollama_ok = await self.ollama.check_health()
        return {
            "ollama": ollama_ok,
            "chromadb": self.chroma.is_ready,
            "duckdb": self.duck.is_ready,
            "circuit_breaker": self.circuit_breaker.state,
            "initialized": self._initialized,
        }

    async def close(self):
        await self.ollama.close()
        await self.chroma.close()
        await self.duck.close()
        self._initialized = False
        logger.info("InferenceService closed")
