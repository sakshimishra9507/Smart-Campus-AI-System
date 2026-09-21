import asyncio, json
from agent_orchestration.realtime_progress import AgentProgressBus, ProgressEvent

def test_event_serializes_as_sse():
    event = ProgressEvent("agent.started", 1.0, {"session_id": "s1"})
    value = event.as_sse()
    assert value.startswith("event: agent.started")
    assert '"session_id": "s1"' in value

def test_bus_delivers_events():
    async def run():
        bus = AgentProgressBus()
        stream = bus.subscribe()
        task = asyncio.create_task(stream.__anext__())
        await asyncio.sleep(0)
        assert bus.subscriber_count == 1
        await bus.publish("agent.planning", session_id="s1")
        event = await asyncio.wait_for(task, 1)
        await stream.aclose()
        assert event.event == "agent.planning"
        assert event.payload["session_id"] == "s1"
        assert bus.subscriber_count == 0
    asyncio.run(run())

def test_known_progress_events_are_stable():
    from agent_orchestration.realtime_progress import PROGRESS_EVENTS
    assert "agent.started" in PROGRESS_EVENTS
    assert "agent.waiting_for_approval" in PROGRESS_EVENTS
    assert "agent.failed" in PROGRESS_EVENTS
