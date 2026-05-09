import httpx
import asyncio
from loguru import logger
from typing import Optional, AsyncIterator
from ai.config.settings import ai_settings
from ai.llm.models import ModelConfig


class OllamaClient:
    def __init__(self):
        self.base_url = ai_settings.ollama_host.rstrip("/")
        self.timeout = ai_settings.ollama_request_timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

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
        resp = await client.post("/api/pull", json={"name": model, "stream": False})
        resp.raise_for_status()
        return resp.json()

    async def generate(
        self,
        prompt: str,
        model_config: Optional[ModelConfig] = None,
    ) -> str:
        cfg = model_config or ModelConfig()
        payload = cfg.to_ollama_payload()
        payload["prompt"] = prompt

        client = await self._get_client()
        resp = await client.post("/api/generate", json=payload)
        resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        full_response = []
        for line in lines:
            if line.strip():
                try:
                    chunk = import_json(line)
                    full_response.append(chunk.get("response", ""))
                    if chunk.get("done"):
                        break
                except Exception:
                    continue

        return "".join(full_response)

    async def generate_stream(
        self,
        prompt: str,
        model_config: Optional[ModelConfig] = None,
    ) -> AsyncIterator[str]:
        cfg = model_config or ModelConfig()
        payload = cfg.to_ollama_payload()
        payload["prompt"] = prompt
        payload["stream"] = True

        client = await self._get_client()
        async with client.stream("POST", "/api/generate", json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                try:
                    chunk = import_json(line)
                    text = chunk.get("response", "")
                    if text:
                        yield text
                    if chunk.get("done"):
                        break
                except Exception:
                    continue

    async def chat(
        self,
        messages: list[dict],
        model_config: Optional[ModelConfig] = None,
    ) -> str:
        cfg = model_config or ModelConfig()
        payload = cfg.to_ollama_payload()
        payload["messages"] = messages

        client = await self._get_client()
        resp = await client.post("/api/chat", json=payload)
        resp.raise_for_status()

        lines = resp.text.strip().split("\n")
        full_content = []
        for line in lines:
            if line.strip():
                try:
                    chunk = import_json(line)
                    msg = chunk.get("message", {})
                    full_content.append(msg.get("content", ""))
                    if chunk.get("done"):
                        break
                except Exception:
                    continue

        return "".join(full_content)

    async def get_embedding(self, text: str, model: Optional[str] = None) -> list[float]:
        model_name = model or ai_settings.embedding_model
        client = await self._get_client()
        resp = await client.post("/api/embeddings", json={
            "model": model_name,
            "prompt": text,
        })
        resp.raise_for_status()
        data = resp.json()
        return data.get("embedding", [])

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


def import_json(s: str) -> dict:
    import json as _json
    return _json.loads(s)
