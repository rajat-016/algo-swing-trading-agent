import asyncio
import hashlib
import json
import os
import random
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

import httpx
from loguru import logger

from ai.config.settings import ai_settings
from ai.llm.client import OllamaClient
from core.monitoring import get_metrics_collector


class EmbeddingCache:
    def __init__(
        self,
        max_size: int = 10000,
        ttl_seconds: int = 86400,
        persist_path: Optional[str] = None,
    ):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._persist_path = persist_path
        self._mem_cache: OrderedDict[str, tuple[list[float], float]] = OrderedDict()
        self._dirty = False
        self._loaded = False

    def _make_key(self, text: str, model: str) -> str:
        raw = f"{model}:::{text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_expired(self, timestamp: float) -> bool:
        return (time.monotonic() - timestamp) > self._ttl

    def _load_persistent(self):
        if self._loaded:
            return
        self._loaded = True
        if not self._persist_path:
            return
        path = Path(self._persist_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text("utf-8"))
            for key, entry in data.items():
                self._mem_cache[key] = (entry["v"], entry["t"])
            logger.info(
                f"Loaded {len(data)} cached embeddings from {self._persist_path}"
            )
        except Exception as e:
            logger.warning(f"Failed to load embedding cache: {e}")

    def _save_persistent(self):
        if not self._persist_path:
            return
        if not self._dirty:
            return
        path = Path(self._persist_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for key, (vec, ts) in self._mem_cache.items():
                data[key] = {"v": vec, "t": ts}
            path.write_text(json.dumps(data), "utf-8")
            self._dirty = False
            logger.debug(f"Saved {len(data)} cached embeddings to {self._persist_path}")
        except Exception as e:
            logger.warning(f"Failed to save embedding cache: {e}")

    def _evict_lru(self):
        while len(self._mem_cache) > self._max_size:
            self._mem_cache.popitem(last=False)
            self._dirty = True

    def _evict_expired(self):
        now = time.monotonic()
        expired_keys = [
            k for k, (_, ts) in self._mem_cache.items()
            if (now - ts) > self._ttl
        ]
        for k in expired_keys:
            del self._mem_cache[k]
        if expired_keys:
            self._dirty = True

    def get(self, text: str, model: str) -> Optional[list[float]]:
        self._load_persistent()
        key = self._make_key(text, model)
        entry = self._mem_cache.get(key)
        if entry is None:
            return None
        vec, ts = entry
        if self._is_expired(ts):
            del self._mem_cache[key]
            self._dirty = True
            return None
        self._mem_cache.move_to_end(key)
        return vec

    def set(self, text: str, model: str, embedding: list[float]):
        self._load_persistent()
        key = self._make_key(text, model)
        self._mem_cache[key] = (embedding, time.monotonic())
        self._mem_cache.move_to_end(key)
        self._dirty = True
        self._evict_lru()

    def clear(self):
        self._mem_cache.clear()
        self._dirty = True
        if self._persist_path:
            path = Path(self._persist_path)
            if path.exists():
                path.unlink(missing_ok=True)
        logger.info("Embedding cache cleared")

    def stats(self) -> dict:
        self._load_persistent()
        self._evict_expired()
        return {
            "size": len(self._mem_cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
            "persist_path": self._persist_path or "none",
            "eviction_policy": "lru",
        }


class EmbeddingService:
    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self._ollama = ollama_client or OllamaClient()
        self._model = ai_settings.embedding_model
        self._batch_size = ai_settings.embedding_batch_size
        self._max_concurrency = ai_settings.embedding_max_concurrency
        self._semaphore = asyncio.Semaphore(self._max_concurrency)
        self._metrics = get_metrics_collector()
        self._cache = EmbeddingCache(
            max_size=ai_settings.embedding_cache_max_size,
            ttl_seconds=ai_settings.embedding_cache_ttl_seconds,
            persist_path=ai_settings.embedding_cache_persist_path,
        )

    async def _get_embedding_with_retry(self, text: str, model: str) -> list[float]:
        max_retries = ai_settings.embedding_retry_max_retries
        base_delay = ai_settings.embedding_retry_base_delay
        max_delay = ai_settings.embedding_retry_max_delay

        last_exc = None
        for attempt in range(max_retries + 1):
            try:
                return await self._ollama.get_embedding(text, model=model)
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout,
                    httpx.RemoteProtocolError, httpx.HTTPStatusError) as e:
                last_exc = e
                if isinstance(e, httpx.HTTPStatusError):
                    if e.response.status_code not in {429, 500, 502, 503, 504}:
                        raise
                if attempt >= max_retries:
                    raise
                delay = min(base_delay * (2 ** attempt) + random.uniform(0, 0.5), max_delay)
                logger.warning(
                    f"Embedding retry {attempt + 1}/{max_retries} "
                    f"in {delay:.1f}s: {e}"
                )
                await asyncio.sleep(delay)
            except Exception as e:
                raise

    async def embed(
        self,
        text: str,
        use_cache: bool = True,
        model: Optional[str] = None,
    ) -> list[float]:
        embed_model = model or self._model
        if not text or not text.strip():
            logger.warning("Empty text passed to embed")
            return [0.0] * ai_settings.embedding_dimension

        if use_cache:
            cached = self._cache.get(text, embed_model)
            if cached is not None:
                return cached

        start = time.monotonic()
        try:
            embedding = await self._get_embedding_with_retry(text, embed_model)
            latency = time.monotonic() - start
            self._metrics.record_latency("embedding.embed", latency * 1000)

            if use_cache:
                self._cache.set(text, embed_model, embedding)

            return embedding
        except Exception as e:
            latency = time.monotonic() - start
            self._metrics.record_error("embedding.embed", str(e))
            raise

    async def embed_batch(
        self,
        texts: list[str],
        use_cache: bool = True,
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> list[list[float]]:
        start = time.monotonic()
        embed_model = model or self._model
        results: list[Optional[list[float]]] = [None] * len(texts)
        fail_count = 0

        async def _process_one(idx: int, t: str):
            nonlocal fail_count
            async with self._semaphore:
                try:
                    results[idx] = await self.embed(t, use_cache=use_cache, model=embed_model)
                except Exception as e:
                    fail_count += 1
                    logger.error(f"Embedding failed for item {idx}: {e}")
                    results[idx] = [0.0] * ai_settings.embedding_dimension

        total = len(texts)
        done = 0

        for i in range(0, total, self._batch_size):
            batch = texts[i:i + self._batch_size]
            indices = list(range(i, min(i + self._batch_size, total)))
            tasks = [_process_one(idx, texts[idx]) for idx in indices]
            await asyncio.gather(*tasks, return_exceptions=True)

            done += len(batch)
            if progress_callback:
                progress_callback(done, total)

        latency = time.monotonic() - start
        self._metrics.record_latency("embedding.embed_batch", latency * 1000)

        return [r for r in results if r is not None]

    async def embed_documents(
        self,
        documents: list[dict],
        text_key: str = "text",
        use_cache: bool = True,
        model: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        auto_metadata: bool = True,
    ) -> list[dict]:
        start = time.monotonic()
        texts = [doc[text_key] for doc in documents]
        embeddings = await self.embed_batch(
            texts,
            use_cache=use_cache,
            model=model,
            progress_callback=progress_callback,
        )
        latency = time.monotonic() - start
        self._metrics.record_latency("embedding.embed_documents", latency * 1000)
        now = datetime.now(timezone.utc).isoformat()
        result = []
        for doc, emb in zip(documents, embeddings):
            doc["embedding"] = emb
            if auto_metadata:
                meta = doc.setdefault("metadata", {})
                if "embedded_at" not in meta:
                    meta["embedded_at"] = now
                if "embedding_model" not in meta:
                    meta["embedding_model"] = model or self._model
                if "embedding_dimension" not in meta:
                    meta["embedding_dimension"] = len(emb)
            result.append(doc)
        return result

    def cache_stats(self) -> dict:
        return self._cache.stats()

    def clear_cache(self):
        self._cache.clear()
