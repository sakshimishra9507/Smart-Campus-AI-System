"""Controlled, read-only repository tools.

No tool executes repository code, shell commands, subprocesses, or model-supplied
commands. All paths and arguments are validated before access.
"""

from dataclasses import dataclass
from pathlib import Path
import logging
import re
from typing import Any, Mapping, Protocol

from repository_intelligence.detectors import DependencyAnalyzer
from repository_intelligence.models import RepositoryAnalysis
from repository_intelligence.search import CodeSearchService
from repository_intelligence.symbols import SymbolIndexer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolLimits:
    max_results: int = 100
    max_query_length: int = 500
    max_file_bytes: int = 1_000_000
    max_path_length: int = 500

    def validate_results(self, value: int) -> int:
        if not isinstance(value, int) or value < 1 or value > self.max_results:
            raise ValueError(f"max_results must be between 1 and {self.max_results}.")
        return value


@dataclass(frozen=True)
class ToolContext:
    repository_root: Path
    permissions: frozenset[str] = frozenset({"repository.read"})
    limits: ToolLimits = ToolLimits()

    def __post_init__(self) -> None:
        root = self.repository_root.resolve()
        object.__setattr__(self, "repository_root", root)
        if "repository.read" not in self.permissions:
            raise PermissionError("repository.read permission is required.")

    def resolve_read_path(self, value: str) -> Path:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("path is required.")
        if len(value) > self.limits.max_path_length:
            raise ValueError("path exceeds the allowed length.")
        candidate = (self.repository_root / value).resolve()
        try:
            candidate.relative_to(self.repository_root)
        except ValueError as exc:
            raise PermissionError("Path escapes the repository workspace.") from exc
        return candidate


@dataclass(frozen=True)
class ToolResult:
    tool: str
    ok: bool
    data: Mapping[str, Any] = None
    error: str | None = None

    def __post_init__(self) -> None:
        if self.data is None:
            object.__setattr__(self, "data", {})


class RepositoryTool:
    name = "repository.tool"

    def __init__(self, context: ToolContext) -> None:
        self.context = context

    def _run(self, operation: str, **arguments: Any) -> ToolResult:
        logger.info("agent_tool.start tool=%s operation=%s", self.name, operation)
        try:
            data = self.execute(operation, **arguments)
            logger.info("agent_tool.success tool=%s operation=%s", self.name, operation)
            return ToolResult(self.name, True, data=data)
        except Exception as exc:
            logger.warning(
                "agent_tool.failure tool=%s operation=%s error=%s",
                self.name,
                operation,
                exc,
            )
            return ToolResult(self.name, False, error=str(exc))

    def execute(self, operation: str, **arguments: Any) -> Mapping[str, Any]:
        raise NotImplementedError


class ListFilesTool(RepositoryTool):
    name = "repository.list_files"

    def execute(self, operation: str = "list", *, prefix: str = "", max_results: int = 100) -> Mapping[str, Any]:
        if operation != "list":
            raise ValueError("Unsupported operation.")
        max_results = self.context.limits.validate_results(max_results)
        base = self.context.resolve_read_path(prefix) if prefix else self.context.repository_root
        if not base.is_dir():
            raise ValueError("prefix must resolve to a directory.")
        ignored = {".git", ".venv", "venv", "node_modules", "__pycache__"}
        paths = []
        for path in sorted(base.rglob("*")):
            if len(paths) >= max_results:
                break
            if path.is_file() and not any(part in ignored for part in path.parts):
                paths.append(path.relative_to(self.context.repository_root).as_posix())
        return {"paths": paths, "truncated": len(paths) >= max_results}


class ReadFileTool(RepositoryTool):
    name = "repository.read_file"

    def execute(self, operation: str = "read", *, path: str, max_bytes: int | None = None) -> Mapping[str, Any]:
        if operation != "read":
            raise ValueError("Unsupported operation.")
        target = self.context.resolve_read_path(path)
        if not target.is_file():
            raise FileNotFoundError(path)
        limit = self.context.limits.max_file_bytes if max_bytes is None else max_bytes
        if not isinstance(limit, int) or limit < 1 or limit > self.context.limits.max_file_bytes:
            raise ValueError("max_bytes is outside the allowed range.")
        if target.stat().st_size > limit:
            raise ValueError("File exceeds the configured read limit.")
        try:
            content = target.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("File is not valid UTF-8 text.") from exc
        return {"path": path, "content": content, "size": target.stat().st_size}


class SearchCodeTool(RepositoryTool):
    name = "repository.search_code"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self.searcher = CodeSearchService(str(context.repository_root))

    def execute(self, operation: str = "search", *, query: str, max_results: int = 50) -> Mapping[str, Any]:
        if operation != "search":
            raise ValueError("Unsupported operation.")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("query is required.")
        if len(query) > self.context.limits.max_query_length:
            raise ValueError("query exceeds the allowed length.")
        max_results = self.context.limits.validate_results(max_results)
        try:
            re.compile(query)
        except re.error as exc:
            raise ValueError("query must be a valid regular expression.") from exc
        return {"query": query, "results": self.searcher.search(query, max_results=max_results)}


class FindSymbolTool(RepositoryTool):
    name = "repository.find_symbol"

    def __init__(self, context: ToolContext) -> None:
        super().__init__(context)
        self.indexer = SymbolIndexer()

    def execute(self, operation: str = "find", *, name: str, max_results: int = 50) -> Mapping[str, Any]:
        if operation != "find":
            raise ValueError("Unsupported operation.")
        if not isinstance(name, str) or not name.strip() or len(name) > self.context.limits.max_query_length:
            raise ValueError("symbol name is invalid.")
        max_results = self.context.limits.validate_results(max_results)
        files, _ = __import__("repository_intelligence.scanner", fromlist=["RepositoryScanner"]).RepositoryScanner().scan(str(self.context.repository_root))
        symbols, _ = self.indexer.index(str(self.context.repository_root), files)
        matches = [s.__dict__ for s in symbols if s.name == name][:max_results]
        return {"name": name, "symbols": matches}


class InspectDependenciesTool(RepositoryTool):
    name = "repository.inspect_dependencies"

    def execute(self, operation: str = "inspect", *, max_results: int = 100) -> Mapping[str, Any]:
        if operation != "inspect":
            raise ValueError("Unsupported operation.")
        max_results = self.context.limits.validate_results(max_results)
        from repository_intelligence.scanner import RepositoryScanner
        from repository_intelligence.detectors import language_for
        files, _ = RepositoryScanner().scan(str(self.context.repository_root))
        enriched = [type(f)(f.path, f.size, language_for(f.path), f.is_binary) for f in files]
        deps = DependencyAnalyzer().analyze(str(self.context.repository_root), enriched)
        return {"dependencies": [d.__dict__ for d in deps[:max_results]], "truncated": len(deps) > max_results}


class GitHistoryProvider(Protocol):
    def history(self, *, limit: int) -> list[Mapping[str, Any]]:
        ...


class InspectGitHistoryTool(RepositoryTool):
    name = "repository.inspect_git_history"

    def __init__(self, context: ToolContext, provider: GitHistoryProvider | None = None) -> None:
        super().__init__(context)
        self.provider = provider

    def execute(self, operation: str = "inspect", *, limit: int = 20) -> Mapping[str, Any]:
        if operation != "inspect":
            raise ValueError("Unsupported operation.")
        limit = self.context.limits.validate_results(limit)
        if self.provider is None:
            return {"commits": [], "available": False, "reason": "No Git history provider configured."}
        return {"commits": list(self.provider.history(limit=limit))[:limit], "available": True}


class ToolRegistry:
    def __init__(self, tools: list[RepositoryTool] | tuple[RepositoryTool, ...]) -> None:
        self._tools = {tool.name: tool for tool in tools}
        if len(self._tools) != len(tools):
            raise ValueError("Tool names must be unique.")

    def get(self, name: str) -> RepositoryTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise PermissionError(f"Tool is not registered: {name}") from exc

    def execute(self, name: str, **arguments: Any) -> ToolResult:
        return self.get(name)._run("execute", **arguments)

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {"name": tool.name, "description": tool.__doc__ or tool.name}
            for tool in self._tools.values()
        ]
