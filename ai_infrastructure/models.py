"""Provider-neutral request, response, tool, and usage models."""

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping, Optional


@dataclass(frozen=True)
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str


@dataclass(frozen=True)
class ToolDefinition:
    """A declaration only; this layer never executes tools."""

    name: str
    description: str
    input_schema: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Tool name is required.")


@dataclass(frozen=True)
class ToolCall:
    """A model-requested tool invocation, kept as data for a future executor."""

    call_id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __post_init__(self) -> None:
        if min(self.prompt_tokens, self.completion_tokens, self.total_tokens) < 0:
            raise ValueError("Token counts cannot be negative.")

    @property
    def input_tokens(self) -> int:
        return self.prompt_tokens

    @property
    def output_tokens(self) -> int:
        return self.completion_tokens


@dataclass(frozen=True)
class LLMRequest:
    messages: tuple[Message, ...]
    model: str
    temperature: float
    max_output_tokens: int
    response_format: Literal["text", "json"] = "text"
    response_schema: Optional[Mapping[str, Any]] = None
    tools: tuple[ToolDefinition, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.messages:
            raise ValueError("At least one message is required.")
        if self.response_format == "json" and self.response_schema is None:
            raise ValueError("JSON responses require response_schema.")


@dataclass(frozen=True)
class LLMResponse:
    content: str
    structured_output: Optional[Mapping[str, Any]] = None
    tool_calls: tuple[ToolCall, ...] = ()
    usage: Usage = Usage()
    request_id: Optional[str] = None
    finish_reason: Optional[str] = None
