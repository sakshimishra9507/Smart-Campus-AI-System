"""State, task, and event models for controlled agent runs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Optional
from uuid import uuid4


EVENT_NAMES = (
    "agent.started",
    "agent.planning",
    "agent.searching",
    "agent.inspecting_file",
    "agent.hypothesis_created",
    "agent.testing",
    "agent.patch_generated",
    "agent.validation_started",
    "agent.validation_completed",
    "agent.completed",
    "agent.failed",
)


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    description: str
    repository_root: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def create(cls, description: str, repository_root: str, **metadata: Any) -> "AgentTask":
        if not description.strip():
            raise ValueError("Task description is required.")
        return cls(uuid4().hex, description, repository_root, metadata)


@dataclass(frozen=True)
class AgentEvent:
    name: str
    run_id: str
    timestamp: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.name not in EVENT_NAMES:
            raise ValueError(f"Unsupported agent event: {self.name}")

    @classmethod
    def create(cls, name: str, run_id: str, **payload: Any) -> "AgentEvent":
        return cls(
            name=name,
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            payload=payload,
        )


@dataclass
class AgentState:
    run_id: str = field(default_factory=lambda: uuid4().hex)
    task: Optional[AgentTask] = None
    status: str = "created"
    current_step: str = "created"
    values: dict[str, Any] = field(default_factory=dict)
    events: list[AgentEvent] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def emit(self, name: str, **payload: Any) -> AgentEvent:
        event = AgentEvent.create(name, self.run_id, **payload)
        self.events.append(event)
        self.current_step = name
        return event

    def fail(self, error: Exception | str) -> None:
        message = str(error)
        self.errors.append(message)
        self.status = "failed"
        self.emit("agent.failed", error=message)

    def complete(self, **payload: Any) -> None:
        self.status = "completed"
        self.emit("agent.completed", **payload)


@dataclass(frozen=True)
class AgentResult:
    run_id: str
    status: str
    values: Mapping[str, Any]
    events: tuple[AgentEvent, ...]
    errors: tuple[str, ...] = ()
