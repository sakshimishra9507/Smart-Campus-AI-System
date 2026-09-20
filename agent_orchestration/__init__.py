"""Controlled agent orchestration for repository analysis and debugging workflows.

This package is read-only with respect to repository source code. It prepares
agent planning, investigation, hypothesis, patch-proposal, and validation
stages without applying code changes or executing arbitrary commands.
"""

from .orchestrator import AgentOrchestrator
from .state import AgentState, AgentEvent, AgentTask, AgentResult
from .tools import (
    ToolRegistry,
    ListFilesTool,
    ReadFileTool,
    SearchCodeTool,
    FindSymbolTool,
    InspectDependenciesTool,
    InspectGitHistoryTool,
)
from .agents import (
    PlannerAgent,
    RepositoryAnalyzer,
    CodeSearchAgent,
    DebuggerAgent,
    FixerAgent,
    ValidatorAgent,
)

__all__ = [
    "AgentOrchestrator",
    "AgentState",
    "AgentEvent",
    "AgentTask",
    "AgentResult",
    "ToolRegistry",
    "ListFilesTool",
    "ReadFileTool",
    "SearchCodeTool",
    "FindSymbolTool",
    "InspectDependenciesTool",
    "InspectGitHistoryTool",
    "PlannerAgent",
    "RepositoryAnalyzer",
    "CodeSearchAgent",
    "DebuggerAgent",
    "FixerAgent",
    "ValidatorAgent",
]

from .patching import Patch, PatchFile, PatchGenerator, PatchStore, PatchApplier, validate_patch
from .patch_review import PatchReviewService
