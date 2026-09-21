"""Transport-neutral real-time agent progress event bus.

The existing agent event names are preserved. Consumers can subscribe through
an async generator and expose the stream over SSE or WebSockets without
changing debugging/business logic.
"""
from __future__ import annotations
import asyncio, json, time
from dataclasses import asdict, dataclass
from typing import Any, AsyncIterator

@dataclass(frozen=True)
class ProgressEvent:
    event: str
    timestamp: float
    payload: dict[str, Any]

    def as_sse(self) -> str:
        return f"event: {self.event}\ndata: {json.dumps(asdict(self), default=str)}\n\n"

class AgentProgressBus:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[ProgressEvent]] = set()

    async def publish(self, event: str, **payload: Any) -> ProgressEvent:
        item = ProgressEvent(event, time.time(), payload)
        for queue in tuple(self._subscribers):
            await queue.put(item)
        return item

    async def subscribe(self) -> AsyncIterator[ProgressEvent]:
        queue: asyncio.Queue[ProgressEvent] = asyncio.Queue()
        self._subscribers.add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

PROGRESS_EVENTS = (
    "agent.started", "agent.planning", "agent.searching",
    "agent.inspecting_file", "agent.hypothesis_created",
    "agent.testing", "agent.hypothesis_tested", "agent.root_cause_identified",
    "agent.patch_generated", "agent.waiting_for_approval",
    "agent.patch_applied", "agent.sandbox_started", "agent.testing_completed",
    "agent.validation_completed", "agent.completed", "agent.failed",
)
