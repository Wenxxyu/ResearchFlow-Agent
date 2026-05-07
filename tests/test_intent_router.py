from app.agent.router import IntentRouter
from app.llm.provider import BaseLLMProvider, ChatMessage


class StaticLLMProvider(BaseLLMProvider):
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def generate(
        self,
        messages: list[ChatMessage],
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str:
        self.calls += 1
        return self.response


def test_intent_router_uses_llm_for_ambiguous_query() -> None:
    provider = StaticLLMProvider(
        '{"task_type":"paper_qa","needs_retrieval":true,"confidence":0.88,'
        '"reason":"The user asks about uploaded paper evidence."}'
    )

    result = IntentRouter(provider).classify("Can you explain the main contribution?")

    assert provider.calls == 1
    assert result.task_type == "paper_qa"
    assert result.needs_retrieval is True
    assert result.confidence == 0.88
    assert result.source == "llm"
    assert "uploaded paper" in result.reason


def test_intent_router_strong_rule_bypasses_llm() -> None:
    provider = StaticLLMProvider(
        '{"task_type":"paper_qa","needs_retrieval":true,"confidence":0.99,"reason":"wrong"}'
    )

    result = IntentRouter(provider).classify("RuntimeError: CUDA out of memory")

    assert provider.calls == 0
    assert result.task_type == "log_debug"
    assert result.needs_retrieval is False
    assert result.source == "rule"


def test_intent_router_falls_back_when_llm_output_is_invalid() -> None:
    provider = StaticLLMProvider("MockLLM answer without JSON")

    result = IntentRouter(provider).classify("Can you help with the next task?")

    assert provider.calls == 1
    assert result.task_type == "general_qa"
    assert result.needs_retrieval is False
    assert result.source == "fallback"


def test_intent_router_rejects_low_confidence_llm() -> None:
    provider = StaticLLMProvider(
        '{"task_type":"repo_qa","needs_retrieval":true,"confidence":0.2,'
        '"reason":"Low confidence guess."}'
    )

    result = IntentRouter(provider).classify("Can you help me decide?")

    assert provider.calls == 1
    assert result.task_type == "general_qa"
    assert result.needs_retrieval is False
    assert result.source == "fallback"
    assert "LLM intent confidence too low" in result.reason


def test_intent_router_does_not_match_hi_inside_other_words() -> None:
    provider = StaticLLMProvider(
        '{"task_type":"paper_qa","needs_retrieval":true,"confidence":0.87,'
        '"reason":"Project-specific retrieval question."}'
    )

    result = IntentRouter(provider).classify("What retrieval methods does this project use?")

    assert provider.calls == 0
    assert result.needs_retrieval is True
    assert result.source == "rule"
