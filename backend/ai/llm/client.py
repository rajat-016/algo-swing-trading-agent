import asyncio
import json
import random
import time
from collections import deque
from typing import Any, AsyncIterator, Optional, Type, TypeVar

import httpx
from loguru import logger
from pydantic import BaseModel

from ai.config.settings import ai_settings
from ai.llm.models import (
    InferenceMetricsSummary,
    InferenceRecord,
    ModelConfig,
    ResponseParser,
)

T = TypeVar("T", bound=BaseModel)

_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


class OllamaClient:
    def __init__(self):
        self.base_url = ai_settings.ollama_host.rstrip("/")

        self.connect_timeout = ai_settings.ollama_connect_timeout
        self.read_timeout = ai_settings.ollama_read_timeout
        self.pool_timeout = ai_settings.ollama_pool_timeout
        self.request_timeout = ai_settings.ollama_request_timeout

        self.retry_enabled = ai_settings.ollama_retry_enabled
        self.max_retries = ai_settings.ollama_max_retries
        self.retry_base_delay = ai_settings.ollama_retry_base_delay
        self.retry_max_delay = ai_settings.ollama_retry_max_delay

        self.metrics_enabled = ai_settings.inference_metrics_enabled

        self._client: Optional[httpx.AsyncClient] = None
        self._records: deque[InferenceRecord] = deque(maxlen=10000)
        self._call_count = 0

    def _build_timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.read_timeout,
            pool=self.pool_timeout,
        )

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self._build_timeout(),
            )
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _retry_async(self, coro_factory, retryable_exceptions=None):
        if not self.retry_enabled:
            return await coro_factory()

        if retryable_exceptions is None:
            retryable_exceptions = (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
                httpx.HTTPStatusError,
            )

        last_exc = None
        for attempt in range(self.max_retries + 1):
            try:
                return await coro_factory()
            except httpx.HTTPStatusError as e:
                last_exc = e
                if e.response.status_code not in _RETRYABLE_STATUSES:
                    raise
                if attempt >= self.max_retries:
                    raise
            except retryable_exceptions as e:
                last_exc = e
                if attempt >= self.max_retries:
                    raise

            delay = min(
                self.retry_base_delay * (2 ** attempt)
                + random.uniform(0, 0.5),
                self.retry_max_delay,
            )
            logger.warning(
                f"Retry {attempt + 1}/{self.max_retries} in {delay:.1f}s: {last_exc}"
            )
            await asyncio.sleep(delay)

    def _resolve_model(
        self, model_config: Optional[ModelConfig], model: Optional[str]
    ) -> ModelConfig:
        if model is not None and model_config is not None:
            resolved = ModelConfig(
                model=model,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
                top_p=model_config.top_p,
                top_k=model_config.top_k,
                repeat_penalty=model_config.repeat_penalty,
                stop=model_config.stop,
                system_prompt=model_config.system_prompt,
                context_length=model_config.context_length,
            )
            return resolved
        if model_config is not None:
            return model_config
        cfg = ModelConfig()
        if model is not None:
            cfg.model = model
        return cfg

    def _record_metrics(
        self,
        model: str,
        latency_s: float,
        success: bool = True,
        error: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        call_type: str = "generate",
    ):
        if not self.metrics_enabled:
            return
        record = InferenceRecord(
            model=model,
            latency_ms=round(latency_s * 1000, 2),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            success=success,
            error=error,
            call_type=call_type,
        )
        self._records.append(record)
        self._call_count += 1

        if self._call_count % ai_settings.inference_metrics_log_interval == 0:
            summary = self.get_metrics_summary()
            logger.info(f"Inference metrics snapshot: {summary.to_dict()}")

    def get_metrics_summary(self) -> InferenceMetricsSummary:
        summary = InferenceMetricsSummary()
        for r in self._records:
            summary.total_calls += 1
            if r.success:
                summary.successful_calls += 1
            else:
                summary.failed_calls += 1
            summary.total_latency_ms += r.latency_ms
            summary.total_tokens += r.total_tokens
            summary.model_usage[r.model] = (
                summary.model_usage.get(r.model, 0) + 1
            )
        return summary

    def clear_metrics(self):
        self._records.clear()
        self._call_count = 0
        logger.info("Inference metrics cleared")

    async def _execute_generate(
        self, payload: dict
    ) -> tuple[str, int, int]:
        client = await self._get_client()
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        full_response = []
        prompt_tokens = 0
        completion_tokens = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
                full_response.append(chunk.get("response", ""))
                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                    completion_tokens = chunk.get(
                        "eval_count", 0
                    )
                    break
            except json.JSONDecodeError:
                continue
        return "".join(full_response), prompt_tokens, completion_tokens

    async def generate(
        self,
        prompt: str,
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> str:
        cfg = self._resolve_model(model_config, model)
        payload = cfg.to_ollama_payload()
        payload["prompt"] = prompt

        start = time.monotonic()
        try:
            text, prompt_tok, completion_tok = await self._retry_async(
                lambda: self._execute_generate(payload)
            )
            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                prompt_tokens=prompt_tok,
                completion_tokens=completion_tok,
                call_type="generate",
            )
            logger.debug(
                f"generate: {cfg.model} {latency:.2f}s "
                f"({prompt_tok}->{completion_tok} tok)"
            )
            return text
        except Exception as e:
            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                success=False,
                error=str(e),
                call_type="generate",
            )
            logger.error(f"generate failed after {latency:.2f}s: {e}")
            raise

    async def generate_structured(
        self,
        prompt: str,
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> dict:
        text = await self.generate(
            prompt=prompt, model_config=model_config, model=model
        )
        return ResponseParser.extract_json(text)

    async def generate_parse(
        self,
        prompt: str,
        model_class: Type[T],
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> T:
        text = await self.generate(
            prompt=prompt, model_config=model_config, model=model
        )
        return ResponseParser.parse_as(model_class, text)

    async def generate_stream(
        self,
        prompt: str,
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        cfg = self._resolve_model(model_config, model)
        payload = cfg.to_ollama_payload()
        payload["prompt"] = prompt
        payload["stream"] = True

        client = await self._get_client()
        start = time.monotonic()
        total_prompt = 0
        total_completion = 0
        chunks_collected = []
        try:
            async with client.stream(
                "POST", "/api/generate", json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        text = chunk.get("response", "")
                        if text:
                            chunks_collected.append(text)
                            yield text
                        if chunk.get("done"):
                            total_prompt = chunk.get(
                                "prompt_eval_count", 0
                            )
                            total_completion = chunk.get(
                                "eval_count", 0
                            )
                            break
                    except json.JSONDecodeError:
                        continue

            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                prompt_tokens=total_prompt,
                completion_tokens=total_completion,
                call_type="generate_stream",
            )
            logger.debug(
                f"generate_stream: {cfg.model} {latency:.2f}s "
                f"({total_prompt}->{total_completion} tok)"
            )
        except Exception as e:
            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                success=False,
                error=str(e),
                call_type="generate_stream",
            )
            logger.error(
                f"generate_stream failed after {latency:.2f}s: {e}"
            )
            raise

    async def _execute_chat(
        self, payload: dict
    ) -> tuple[str, int, int]:
        client = await self._get_client()
        resp = await client.post("/api/chat", json=payload)
        resp.raise_for_status()
        lines = resp.text.strip().split("\n")
        full_content = []
        prompt_tokens = 0
        completion_tokens = 0
        for line in lines:
            if not line.strip():
                continue
            try:
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                full_content.append(msg.get("content", ""))
                if chunk.get("done"):
                    prompt_tokens = chunk.get("prompt_eval_count", 0)
                    completion_tokens = chunk.get(
                        "eval_count", 0
                    )
                    break
            except json.JSONDecodeError:
                continue
        return "".join(full_content), prompt_tokens, completion_tokens

    async def chat(
        self,
        messages: list[dict],
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> str:
        cfg = self._resolve_model(model_config, model)
        payload = cfg.to_ollama_payload()
        payload["messages"] = messages

        start = time.monotonic()
        try:
            (
                text,
                prompt_tok,
                completion_tok,
            ) = await self._retry_async(
                lambda: self._execute_chat(payload)
            )
            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                prompt_tokens=prompt_tok,
                completion_tokens=completion_tok,
                call_type="chat",
            )
            logger.debug(
                f"chat: {cfg.model} {latency:.2f}s "
                f"({prompt_tok}->{completion_tok} tok, {len(messages)} msgs)"
            )
            return text
        except Exception as e:
            latency = time.monotonic() - start
            self._record_metrics(
                model=cfg.model,
                latency_s=latency,
                success=False,
                error=str(e),
                call_type="chat",
            )
            logger.error(f"chat failed after {latency:.2f}s: {e}")
            raise

    async def chat_structured(
        self,
        messages: list[dict],
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> dict:
        text = await self.chat(
            messages=messages, model_config=model_config, model=model
        )
        return ResponseParser.extract_json(text)

    async def chat_parse(
        self,
        messages: list[dict],
        model_class: Type[T],
        model_config: Optional[ModelConfig] = None,
        model: Optional[str] = None,
    ) -> T:
        text = await self.chat(
            messages=messages, model_config=model_config, model=model
        )
        return ResponseParser.parse_as(model_class, text)

    async def get_embedding(
        self, text: str, model: Optional[str] = None
    ) -> list[float]:
        model_name = model or ai_settings.embedding_model
        payload = {
            "model": model_name,
            "prompt": text,
        }

        start = time.monotonic()
        try:
            async def _fetch():
                client = await self._get_client()
                resp = await client.post(
                    "/api/embeddings", json=payload
                )
                resp.raise_for_status()
                return resp.json()

            data = await self._retry_async(_fetch)
            embedding = data.get("embedding", [])
            latency = time.monotonic() - start
            self._record_metrics(
                model=model_name,
                latency_s=latency,
                call_type="embedding",
            )
            logger.debug(
                f"embedding: {model_name} {latency:.2f}s "
                f"({len(embedding)} dim)"
            )
            return embedding
        except Exception as e:
            latency = time.monotonic() - start
            self._record_metrics(
                model=model_name,
                latency_s=latency,
                success=False,
                error=str(e),
                call_type="embedding",
            )
            logger.error(
                f"embedding failed after {latency:.2f}s: {e}"
            )
            raise

    async def check_health(self) -> bool:
        try:
            client = await self._get_client()
            resp = await client.get("/api/tags")
            return resp.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def list_models(self) -> list[dict]:
        client = await self._get_client()
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        return data.get("models", [])

    async def pull_model(self, model: str) -> dict:
        client = await self._get_client()
        resp = await client.post(
            "/api/pull", json={"name": model, "stream": False}
        )
        resp.raise_for_status()
        return resp.json()
