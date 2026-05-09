from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from typing import Optional
from pathlib import Path


class AISettings(BaseSettings):
    model_config = ConfigDict(
        extra="ignore",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
    )

    ai_copilot_enabled: bool = Field(default=False)

    ollama_host: str = Field(default="http://localhost:11434")
    ollama_request_timeout: int = Field(default=120)

    llm_model: str = Field(default="qwen2.5:7b")
    llm_temperature: float = Field(default=0.7)
    llm_max_tokens: int = Field(default=2048)
    llm_top_p: float = Field(default=0.9)

    embedding_model: str = Field(default="nomic-embed-text")
    embedding_dimension: int = Field(default=768)
    embedding_batch_size: int = Field(default=16)

    chromadb_persist_path: str = Field(default="data/chromadb")
    chromadb_collection_prefix: str = Field(default="swing_")

    duckdb_path: str = Field(default="data/analytics.duckdb")

    inference_max_retries: int = Field(default=3)
    inference_circuit_breaker_threshold: int = Field(default=5)
    inference_circuit_breaker_reset_seconds: int = Field(default=60)

    max_prompt_context_length: int = Field(default=4096)

    @property
    def chromadb_persist_directory(self) -> str:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        path = self.chromadb_persist_path
        if not Path(path).is_absolute():
            path = str(backend_dir / path)
        return path

    @property
    def duckdb_absolute_path(self) -> str:
        backend_dir = Path(__file__).resolve().parent.parent.parent
        path = self.duckdb_path
        if not Path(path).is_absolute():
            path = str(backend_dir / path)
        return path


_ai_settings_instance = None


def get_ai_settings() -> AISettings:
    global _ai_settings_instance
    if _ai_settings_instance is None:
        _ai_settings_instance = AISettings()
    return _ai_settings_instance


ai_settings = get_ai_settings()
