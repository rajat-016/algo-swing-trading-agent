import asyncio
from loguru import logger
from typing import Optional
from ai.config.settings import ai_settings
from ai.llm.client import OllamaClient


class EmbeddingService:
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self._ollama = ollama_client or OllamaClient()
        self._cache: dict[str, list[float]] = {}
        self._model = ai_settings.embedding_model
        self._batch_size = ai_settings.embedding_batch_size

    async def embed(self, text: str, use_cache: bool = True) -> list[float]:
        if use_cache and text in self._cache:
            return self._cache[text]

        embedding = await self._ollama.get_embedding(text, model=self._model)

        if use_cache:
            self._cache[text] = embedding

        return embedding

    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
    ) -> list[list[float]]:
        results: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            tasks = [self.embed(t, use_cache=use_cache) for t in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in batch_results:
                if isinstance(r, Exception):
                    logger.error(f"Embedding failed: {r}")
                    results.append([0.0] * ai_settings.embedding_dimension)
                else:
                    results.append(r)
        return results

    async def embed_documents(
        self,
        documents: list[dict],
        text_key: str = "text",
        use_cache: bool = True,
    ) -> list[dict]:
        texts = [doc[text_key] for doc in documents]
        embeddings = await self.embed_batch(texts, use_cache=use_cache)
        result = []
        for doc, emb in zip(documents, embeddings):
            doc["embedding"] = emb
            result.append(doc)
        return result

    def clear_cache(self):
        self._cache.clear()
        logger.info("Embedding cache cleared")
