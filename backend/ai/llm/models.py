import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, TypeVar, Type, Any

from pydantic import BaseModel


class LLMModel:
    QWEN2_5_7B = "qwen2.5:7b"
    QWEN2_5_3B = "qwen2.5:3b"
    QWEN2_5_14B = "qwen2.5:14b"
    QWEN2_5_32B = "qwen2.5:32b"
    LLAMA3_2_3B = "llama3.2:3b"
    LLAMA3_2_1B = "llama3.2:1b"


@dataclass
class ModelConfig:
    model: str = LLMModel.QWEN2_5_7B
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 0.9
    top_k: int = 40
    repeat_penalty: float = 1.1
    stop: Optional[list[str]] = None
    system_prompt: Optional[str] = None
    context_length: int = 32768

    def to_ollama_payload(self) -> dict:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
        }
        if self.stop:
            payload["stop"] = self.stop
        if self.system_prompt:
            payload["system"] = self.system_prompt
        return payload


CHAT_CONFIGS = {
    "default": ModelConfig(),
    "creative": ModelConfig(temperature=0.9, top_p=0.95),
    "precise": ModelConfig(temperature=0.1, top_p=0.5, max_tokens=1024),
    "analysis": ModelConfig(temperature=0.3, max_tokens=4096),
    "reflection": ModelConfig(temperature=0.5, max_tokens=2048),
}


T = TypeVar("T", bound=BaseModel)


class ResponseParser:
    """Extract structured content from LLM text responses."""

    @staticmethod
    def extract_json(text: str) -> dict:
        text = text.strip()
        code_block = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
        )
        if code_block:
            text = code_block.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        return json.loads(text)

    @staticmethod
    def extract_json_array(text: str) -> list:
        text = text.strip()
        code_block = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL
        )
        if code_block:
            text = code_block.group(1).strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        return json.loads(text)

    @staticmethod
    def parse_as(model_class: Type[T], text: str) -> T:
        data = ResponseParser.extract_json(text)
        return model_class.model_validate(data)

    @staticmethod
    def try_extract_json(text: str) -> Optional[dict]:
        try:
            return ResponseParser.extract_json(text)
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def safe_parse(model_class: Type[T], text: str) -> Optional[T]:
        try:
            return ResponseParser.parse_as(model_class, text)
        except Exception:
            return None


@dataclass
class InferenceRecord:
    model: str
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    success: bool = True
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    call_type: str = "generate"

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


@dataclass
class InferenceMetricsSummary:
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_latency_ms: float = 0.0
    total_tokens: int = 0
    model_usage: dict[str, int] = field(default_factory=dict)

    @property
    def avg_latency_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 1.0
        return self.successful_calls / self.total_calls

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "total_tokens": self.total_tokens,
            "success_rate": round(self.success_rate, 4),
            "model_usage": dict(
                sorted(self.model_usage.items(), key=lambda x: -x[1])
            ),
        }
