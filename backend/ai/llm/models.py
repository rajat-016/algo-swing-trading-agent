from dataclasses import dataclass, field
from typing import Optional


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
