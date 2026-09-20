"""Safe default construction of the controlled repository tool registry."""

from pathlib import Path

from .tools import (
    FindSymbolTool,
    InspectDependenciesTool,
    InspectGitHistoryTool,
    ListFilesTool,
    ReadFileTool,
    SearchCodeTool,
    ToolContext,
    ToolRegistry,
)


def build_tool_registry(repository_root: str | Path, *, git_history_provider=None) -> ToolRegistry:
    context = ToolContext(Path(repository_root))
    return ToolRegistry(
        [
            ListFilesTool(context),
            ReadFileTool(context),
            SearchCodeTool(context),
            FindSymbolTool(context),
            InspectDependenciesTool(context),
            InspectGitHistoryTool(context, git_history_provider),
        ]
    )
