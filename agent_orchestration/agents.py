"""Specialized agents used by AgentOrchestrator.

Agents are deliberately read-only. FixerAgent produces a patch proposal as
structured data but never writes files.
"""

from dataclasses import dataclass
from typing import Any, Mapping

from ai_infrastructure.models import Message
from ai_infrastructure.service import LLMService
from repository_intelligence.analyzer import RepositoryAnalyzer as DeterministicRepositoryAnalyzer

from .state import AgentTask
from .tools import ToolRegistry


@dataclass
class PlannerAgent:
    llm: LLMService

    def plan(self, task: AgentTask) -> Mapping[str, Any]:
        response = self.llm.complete(
            [
                Message("system", "Create a concise read-only repository investigation plan."),
                Message("user", task.description),
            ],
            response_format="json",
            response_schema={
                "type": "object",
                "properties": {
                    "steps": {"type": "array", "items": {"type": "string"}},
                    "focus": {"type": "string"},
                },
                "required": ["steps", "focus"],
            },
        )
        if response.structured_output:
            return response.structured_output
        return {"steps": [], "focus": task.description}


class RepositoryAnalyzer:
    """Adapter exposing deterministic Repository Intelligence to the agent."""

    def __init__(self, analyzer: DeterministicRepositoryAnalyzer | None = None) -> None:
        self.analyzer = analyzer

    def analyze(self, repository_root: str) -> Mapping[str, Any]:
        if self.analyzer is None:
            self.analyzer = DeterministicRepositoryAnalyzer(repository_root)
            result = self.analyzer.analyze()
        else:
            try:
                result = self.analyzer.analyze(repository_root)
            except TypeError:
                result = self.analyzer.analyze()
        return {
            "architecture_summary": result.architecture_summary,
            "languages": result.languages,
            "frameworks": result.frameworks,
            "entry_points": result.entry_points,
            "test_frameworks": result.test_frameworks,
            "api_routes": [r.__dict__ for r in result.routes],
        }


@dataclass
class CodeSearchAgent:
    tools: ToolRegistry

    def search(self, query: str, max_results: int = 20) -> Mapping[str, Any]:
        return self.tools.execute(
            "repository.search_code", query=query, max_results=max_results
        ).data


@dataclass
class DebuggerAgent:
    llm: LLMService

    def hypothesize(self, task: AgentTask, evidence: Mapping[str, Any]) -> Mapping[str, Any]:
        response = self.llm.complete(
            [
                Message("system", "Analyze evidence and return a testable debugging hypothesis. Do not propose commands."),
                Message("user", f"Task: {task.description}\nEvidence: {evidence}"),
            ],
            response_format="json",
            response_schema={
                "type": "object",
                "properties": {
                    "hypothesis": {"type": "string"},
                    "evidence": {"type": "array", "items": {"type": "string"}},
                    "confidence": {"type": "number"},
                },
                "required": ["hypothesis", "evidence", "confidence"],
            },
        )
        return response.structured_output or {}


@dataclass
class FixerAgent:
    llm: LLMService

    def propose_fix(self, task: AgentTask, hypothesis: Mapping[str, Any]) -> Mapping[str, Any]:
        response = self.llm.complete(
            [
                Message("system", "Propose a patch as data only. Never apply or execute it."),
                Message("user", f"Task: {task.description}\nHypothesis: {hypothesis}"),
            ],
            response_format="json",
            response_schema={
                "type": "object",
                "properties": {
                    "files": {"type": "array", "items": {"type": "string"}},
                    "patch": {"type": "string"},
                    "rationale": {"type": "string"},
                },
                "required": ["files", "patch", "rationale"],
            },
        )
        return response.structured_output or {}


@dataclass
class ValidatorAgent:
    def validate_proposal(self, proposal: Mapping[str, Any]) -> Mapping[str, Any]:
        required = {"files", "patch", "rationale"}
        missing = sorted(required - set(proposal))
        if missing:
            return {"valid": False, "errors": [f"Missing fields: {', '.join(missing)}"]}
        if not isinstance(proposal["files"], list) or not isinstance(proposal["patch"], str):
            return {"valid": False, "errors": ["Invalid patch proposal field types."]}
        return {
            "valid": True,
            "errors": [],
            "files": proposal["files"],
            "modification_applied": False,
        }
