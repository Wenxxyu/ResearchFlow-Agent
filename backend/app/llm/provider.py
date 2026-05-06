from abc import ABC, abstractmethod
from typing import Literal, TypedDict

from app.core.config import get_settings


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        """Generate a response from chat messages."""


class MockLLMProvider(BaseLLMProvider):
    """Local deterministic provider for development and tests."""

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        user_messages = [message["content"] for message in messages if message["role"] == "user"]
        prompt = user_messages[-1] if user_messages else ""
        compact = " ".join(prompt.split())
        preview = compact[: min(len(compact), 360)]
        return (
            "MockLLM answer: I reviewed the provided evidence and generated a grounded response. "
            f"Question/context preview: {preview}"
        )


class OpenAICompatibleLLMProvider(BaseLLMProvider):
    """Chat completions provider for OpenAI-compatible APIs."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        timeout_seconds: float = 30,
    ) -> None:
        from openai import OpenAI

        kwargs = {"api_key": api_key, "timeout": timeout_seconds}
        if base_url:
            kwargs["base_url"] = base_url
        self.client = OpenAI(**kwargs)
        self.model = model

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content or ""


class OpenAIProvider(OpenAICompatibleLLMProvider):
    pass


class QwenProvider(OpenAICompatibleLLMProvider):
    pass


class DeepSeekProvider(OpenAICompatibleLLMProvider):
    pass


def get_llm_provider() -> BaseLLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower()

    if provider == "mock":
        return MockLLMProvider()

    if provider in {"openai", "openai_compatible", "qwen", "deepseek"}:
        if not settings.llm_api_key:
            raise RuntimeError("RESEARCHFLOW_LLM_API_KEY is required for real LLM providers.")
        return OpenAICompatibleLLMProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    raise RuntimeError(f"Unsupported LLM provider: {settings.llm_provider}")
