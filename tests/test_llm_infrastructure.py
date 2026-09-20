from concurrent.futures import TimeoutError as FutureTimeoutError

import pytest

from ai_infrastructure.config import ModelConfig, Pricing
from ai_infrastructure.errors import (
    InvalidLLMResponseError,
    LLMTimeoutError,
    RetryExhaustedError,
    TokenLimitExceededError,
    TransientLLMError,
)
from ai_infrastructure.models import LLMRequest, LLMResponse, Message, ToolCall, ToolDefinition, Usage
from ai_infrastructure.prompts import PromptManager, PromptTemplate
from ai_infrastructure.providers import LLMProvider
from ai_infrastructure.service import LLMService
from ai_infrastructure.state import AgentState
from ai_infrastructure.usage import UsageTracker


class MockProvider(LLMProvider):
    def __init__(self, responses=None, errors=None):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        if self.errors:
            error = self.errors.pop(0)
            raise error
        return self.responses.pop(0)


def config(**kwargs):
    values = dict(
        provider_name="mock",
        model_name="mock-model",
        timeout_seconds=1,
        max_retries=2,
        retry_backoff_seconds=0,
        pricing=Pricing(input_per_million=2, output_per_million=4),
    )
    values.update(kwargs)
    return ModelConfig(**values)


def test_provider_abstraction_and_usage_tracking():
    provider = MockProvider(
        responses=[LLMResponse("hello", usage=Usage(10, 5, 15), request_id="r1")]
    )
    tracker = UsageTracker()
    service = LLMService(provider, config(), tracker)

    result = service.complete([Message("user", "hello")])

    assert result.content == "hello"
    assert len(provider.calls) == 1
    snapshot = tracker.snapshot()
    assert snapshot.total_tokens == 15
    assert snapshot.estimated_cost_usd == pytest.approx(0.00004)


def test_retry_on_transient_error():
    provider = MockProvider(
        responses=[LLMResponse("ok", usage=Usage(1, 1, 2))],
        errors=[TransientLLMError("temporary")],
    )
    service = LLMService(provider, config())

    assert service.complete([Message("user", "retry")]).content == "ok"
    assert len(provider.calls) == 2


def test_retry_exhaustion():
    provider = MockProvider(errors=[TransientLLMError("a"), TransientLLMError("b"), TransientLLMError("c")])
    service = LLMService(provider, config(max_retries=2))

    with pytest.raises(RetryExhaustedError):
        service.complete([Message("user", "fail")])
    assert len(provider.calls) == 3


def test_timeout_is_converted_to_llm_error(monkeypatch):
    provider = MockProvider(responses=[LLMResponse("never")])

    def slow_result(self, timeout=None):
        raise FutureTimeoutError()

    monkeypatch.setattr("ai_infrastructure.service.FutureTimeoutError", FutureTimeoutError)
    monkeypatch.setattr("concurrent.futures.Future.result", slow_result)
    service = LLMService(provider, config(max_retries=0))

    with pytest.raises(LLMTimeoutError):
        service.complete([Message("user", "slow")])


def test_structured_output_and_tool_call_are_data_only():
    tool = ToolDefinition("lookup_repo", "Look up repository metadata.", {"type": "object"})
    response = LLMResponse(
        '{"answer":"ok"}',
        structured_output={"answer": "ok"},
        tool_calls=(ToolCall("c1", "lookup_repo", {"repo": "x"}),),
    )
    provider = MockProvider(responses=[response])
    service = LLMService(provider, config())

    result = service.complete(
        [Message("user", "structured")],
        response_format="json",
        response_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        tools=[tool],
    )

    assert result.structured_output == {"answer": "ok"}
    assert result.tool_calls[0].name == "lookup_repo"
    assert provider.calls[0].tools[0].name == "lookup_repo"


def test_invalid_json_is_rejected():
    provider = MockProvider(responses=[LLMResponse("not json")])
    service = LLMService(provider, config())

    with pytest.raises(InvalidLLMResponseError):
        service.complete(
            [Message("user", "json")],
            response_format="json",
            response_schema={"type": "object"},
        )


def test_token_budget_is_enforced():
    provider = MockProvider(responses=[LLMResponse("too much", usage=Usage(8, 5, 13))])
    service = LLMService(provider, config(max_total_tokens=10))

    with pytest.raises(TokenLimitExceededError):
        service.complete([Message("user", "budget")])


def test_prompt_manager():
    manager = PromptManager()
    manager.register(PromptTemplate("greeting", system="You are {role}.", user="Hello {name}."))
    assert manager.get("greeting").render({"role": "assistant", "name": "Sakshi"}) == (
        "You are assistant.",
        "Hello Sakshi.",
    )
    with pytest.raises(KeyError):
        manager.get("greeting").render({"role": "assistant"})


def test_agent_state():
    state = AgentState("run-1")
    state.set("phase", "analysis")
    state.add_event({"type": "started"})
    assert state.get("phase") == "analysis"
    assert state.history == [{"type": "started"}]
