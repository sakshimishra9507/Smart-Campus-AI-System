"""Comprehensive mocked tests for the read-only debugging workflow."""

import json
from pathlib import Path

from ai_infrastructure.config import ModelConfig
from ai_infrastructure.models import LLMResponse, Usage
from ai_infrastructure.providers import LLMProvider
from ai_infrastructure.service import LLMService

from agent_orchestration.agents import RepositoryAnalyzer
from agent_orchestration.debugging import AutonomousDebuggingWorkflow
from agent_orchestration.factory import build_tool_registry


class MockProvider(LLMProvider):
    def complete(self, request):
        system = request.messages[0].content
        if "investigation plan" in system:
            data = {
                "steps": ["inspect metadata", "search login route", "inspect files", "inspect dependencies", "inspect tests"],
                "focus": "POST /login",
                "search_queries": ["login", "/login"],
            }
        elif "Perform read-only debugging diagnosis" in system:
            data = {
                "hypotheses": [
                    {
                        "statement": "Login handler raises an unhandled exception.",
                        "evidence": ["login handler appears in search evidence"],
                        "supported": True,
                        "reason": "Evidence points to the handler.",
                    },
                    {
                        "statement": "Database credentials are definitely wrong.",
                        "evidence": [],
                        "supported": False,
                        "reason": "No repository evidence supports this.",
                    },
                ],
                "root_cause": {
                    "statement": "Unhandled exception in the login handler.",
                    "evidence": ["login handler evidence"],
                },
                "affected_files": ["app.py"],
                "uncertainty": ["Runtime logs were not available."],
            }
        else:
            data = {
                "files": ["app.py"],
                "patch": "diff -- proposal only",
                "rationale": "Handle the exception.",
            }
        payload = json.dumps(data)
        return LLMResponse(
            content=payload,
            structured_output=data,
            usage=Usage(prompt_tokens=20, completion_tokens=20, total_tokens=40),
            request_id="mock",
        )


def llm():
    return LLMService(
        MockProvider(),
        ModelConfig(provider_name="mock", model_name="mock", timeout_seconds=2, max_retries=0, max_output_tokens=500),
    )


def test_debugging_workflow_returns_required_result_and_timeline(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "def login(request):\n    return 'error'\n", encoding="utf-8"
    )
    (tmp_path / "test_login.py").write_text(
        "def test_login():\n    assert True\n", encoding="utf-8"
    )
    workflow = AutonomousDebuggingWorkflow(
        llm=llm(),
        repository_analyzer=RepositoryAnalyzer(),
        tools=build_tool_registry(tmp_path),
    )

    result = workflow.run("POST /login returns HTTP 500", str(tmp_path))

    assert result.problem == "POST /login returns HTTP 500"
    assert result.investigation_plan["focus"] == "POST /login"
    assert result.evidence
    assert result.hypotheses
    assert result.root_cause["statement"]
    assert result.affected_files == ("app.py",)
    assert result.proposed_solution["modification_applied"] is False
    assert result.uncertainty
    names = [event.name for event in result.timeline]
    assert names[0] == "agent.started"
    assert "agent.planning" in names
    assert "agent.searching" in names
    assert "agent.inspecting_file" in names
    assert "agent.testing" in names
    assert "agent.patch_generated" in names
    assert names[-1] == "agent.completed"


def test_unsupported_hypotheses_are_identified_and_never_executed(tmp_path: Path):
    (tmp_path / "app.py").write_text("def login(): pass\n", encoding="utf-8")
    workflow = AutonomousDebuggingWorkflow(
        llm=llm(),
        repository_analyzer=RepositoryAnalyzer(),
        tools=build_tool_registry(tmp_path),
    )
    result = workflow.run("POST /login returns HTTP 500", str(tmp_path))
    unsupported = [h for h in result.hypotheses if h["supported"] is False]
    assert unsupported
    assert "Database credentials are definitely wrong." in [
        h["statement"] for h in unsupported
    ]
    assert result.proposed_solution["modification_applied"] is False


def test_empty_problem_is_rejected(tmp_path: Path):
    workflow = AutonomousDebuggingWorkflow(
        llm=llm(),
        repository_analyzer=RepositoryAnalyzer(),
        tools=build_tool_registry(tmp_path),
    )
    import pytest
    with pytest.raises(ValueError):
        workflow.run("", str(tmp_path))
