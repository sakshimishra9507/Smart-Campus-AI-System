"""Minimal serializable state container for future agent orchestration."""

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class AgentState:
    """State only; orchestration and autonomous debugging are intentionally absent."""

    run_id: str
    values: dict[str, Any] = field(default_factory=dict)
    history: list[Mapping[str, Any]] = field(default_factory=list)
    pending_tool_calls: list[Mapping[str, Any]] = field(default_factory=list)

    def set(self, key: str, value: Any) -> None:
        self.values[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    def add_event(self, event: Mapping[str, Any]) -> None:
        self.history.append(dict(event))
