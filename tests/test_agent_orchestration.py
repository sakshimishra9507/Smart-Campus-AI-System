"""Tests for controlled agent orchestration with mocked repository data and LLM responses."""

from pathlib import Path

from ai_infrastructure.models import LLMResponse, Usage
from ai_infrastructure.providers import LLMProvider
from ai_infrastructure.service import LLMService
from ai_infrastructure.config import ModelConfig

from agent_orchestration.agents import (
    CodeSearchAgent,
    DebuggerAgent,
    FixerAgent,
    RepositoryAnalyzer,
    ValidatorAgent,
)
from agent_orchestration.factory import build_tool_registry
from agent_orchestration.orchestrator import AgentOrchestrator
from agent_orchestration.state import AgentTask
from agent_orchestration.tools import ToolContext, ReadFileTool


class MockLLM(LLMProvider):
    def __init__(self):
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        user = request.messages[-1].content
        if "investigation plan" in request.messages[0].content:
            payload = '{"steps":["inspect repository","search relevant code"],"focus":"repository evidence"}'
        elif "testable debugging hypothesis" in request.messages[0].content:
            payload = '{"hypothesis":"mock hypothesis","evidence":["mock evidence"],"confidence":0.8}'
        else:
            payload = '{"files":["app.py"],"patch":"--- a/app.py\\n+++ b/app.py","rationale":"mock proposal"}'
        import json
        return LLMResponse(
            content=payload,
            structured_output=json.loads(payload),
            usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
            request_id=f"mock-{len(self.calls)}",
        )


def make_llm():
    return LLMService(
        MockLLM(),
        ModelConfig(
            provider_name="mock",
            model_name="mock-model",
            timeout_seconds=2,
            max_retries=0,
            max_output_tokens=200,
        ),
    )


def test_tool_registry_is_controlled_and_read_only(tmp_path: Path):
    (tmp_path / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    registry = build_tool_registry(tmp_path)
    result = registry.execute("repository.read_file", path="app.py")
    assert result.ok
    assert result.data["content"].startswith("def hello")

    unknown = registry.execute("shell.execute", command="echo unsafe")
    assert not unknown.ok
    assert "not registered" in unknown.error


def test_tools_reject_path_escape(tmp_path: Path):
    tool = ReadFileTool(ToolContext(tmp_path))
    result = tool._run("execute", path="../secret.txt")
    assert not result.ok
    assert "escapes" in result.error.lower()


def test_orchestrator_emits_expected_events(tmp_path: Path):
    (tmp_path / "app.py").write_text("def hello():\n    return 1\n", encoding="utf-8")
    llm = make_llm()
    registry = build_tool_registry(tmp_path)

    class MockAnalyzer:
        def analyze(self, root):
            return {"architecture_summary": {"files": 1}, "languages": {"Python": 1}}

    orchestrator = AgentOrchestrator(
        llm=llm,
        repository_analyzer=RepositoryAnalyzer(MockAnalyzer()),
        code_search_agent=CodeSearchAgent(registry),
        debugger=DebuggerAgent(llm),
        fixer=FixerAgent(llm),
        validator=ValidatorAgent(),
        tools=registry,
    )
    result = orchestrator.run(
        AgentTask.create("Investigate the mock repository", str(tmp_path)),
        search_query="hello",
    )

    assert result.status == "completed"
    names = [event.name for event in result.events]
    assert names == [
        "agent.started",
        "agent.planning",
        "agent.inspecting_file",
        "agent.searching",
        "agent.hypothesis_created",
        "agent.testing",
        "agent.patch_generated",
        "agent.validation_started",
        "agent.validation_completed",
        "agent.completed",
    ]
    assert result.values["validation"]["modification_applied"] is False
    assert not any("shell" in str(event.payload).lower() for event in result.events)


def test_agent_event_rejects_unknown_event():
    from agent_orchestration.state import AgentEvent
    import pytest
    with pytest.raises(ValueError):
        AgentEvent.create("agent.shell_executed", "run")


def test_validator_never_applies_patch():
    validation = ValidatorAgent().validate_proposal(
        {"files": ["app.py"], "patch": "diff", "rationale": "test"}
    )
    assert validation["valid"] is True
    assert validation["modification_applied"] is False
