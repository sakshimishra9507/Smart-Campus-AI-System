"""Central controller for the controlled agent workflow."""

import logging
from typing import Any, Mapping

from ai_infrastructure.service import LLMService

from .agents import (
    CodeSearchAgent,
    DebuggerAgent,
    FixerAgent,
    PlannerAgent,
    RepositoryAnalyzer,
    ValidatorAgent,
)
from .state import AgentResult, AgentState, AgentTask
from .tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Controls agent lifecycle and prevents direct/unregistered tool access."""

    def __init__(
        self,
        *,
        llm: LLMService,
        repository_analyzer: RepositoryAnalyzer,
        code_search_agent: CodeSearchAgent,
        debugger: DebuggerAgent,
        fixer: FixerAgent,
        validator: ValidatorAgent,
        tools: ToolRegistry,
    ) -> None:
        self.planner = PlannerAgent(llm)
        self.repository_analyzer = repository_analyzer
        self.code_search_agent = code_search_agent
        self.debugger = debugger
        self.fixer = fixer
        self.validator = validator
        self.tools = tools

    def run(self, task: AgentTask, *, search_query: str | None = None) -> AgentResult:
        state = AgentState(task=task)
        try:
            state.status = "running"
            state.emit("agent.started", task_id=task.task_id)

            state.emit("agent.planning")
            plan = self.planner.plan(task)
            state.values["plan"] = dict(plan)

            state.emit("agent.inspecting_file")
            analysis = self.repository_analyzer.analyze(task.repository_root)
            state.values["repository_analysis"] = dict(analysis)

            if search_query:
                state.emit("agent.searching", query=search_query)
                search_result = self.code_search_agent.search(search_query)
                state.values["search_results"] = search_result

            evidence = {
                "plan": state.values["plan"],
                "repository_analysis": state.values["repository_analysis"],
                "search_results": state.values.get("search_results", {}),
            }
            state.emit("agent.hypothesis_created")
            hypothesis = self.debugger.hypothesize(task, evidence)
            state.values["hypothesis"] = dict(hypothesis)

            state.emit("agent.testing")
            state.values["test_plan"] = {"read_only": True, "commands_executed": False}

            state.emit("agent.patch_generated")
            proposal = self.fixer.propose_fix(task, hypothesis)
            state.values["patch_proposal"] = dict(proposal)

            state.emit("agent.validation_started")
            validation = self.validator.validate_proposal(proposal)
            state.values["validation"] = validation
            state.emit("agent.validation_completed", valid=validation["valid"])

            state.complete()
        except Exception as exc:
            logger.exception("Agent run failed")
            state.fail(exc)

        return AgentResult(
            run_id=state.run_id,
            status=state.status,
            values=dict(state.values),
            events=tuple(state.events),
            errors=tuple(state.errors),
        )
