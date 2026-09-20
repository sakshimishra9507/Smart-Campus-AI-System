from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

@dataclass(frozen=True)
class RepositoryFile:
    path: str
    size: int
    language: Optional[str] = None
    is_binary: bool = False

@dataclass(frozen=True)
class Dependency:
    name: str
    version: Optional[str]
    manager: str
    source_file: str
    dev: bool = False

@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str
    path: str
    line: int
    end_line: int
    parent: Optional[str] = None

@dataclass(frozen=True)
class ImportRelation:
    source: str
    target: str
    imported_name: Optional[str] = None

@dataclass(frozen=True)
class Route:
    path: str
    method: str
    source: str
    handler: Optional[str] = None

@dataclass
class RepositoryAnalysis:
    root: str
    files: list[RepositoryFile] = field(default_factory=list)
    directories: list[str] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    frameworks: list[str] = field(default_factory=list)
    package_managers: list[str] = field(default_factory=list)
    dependencies: list[Dependency] = field(default_factory=list)
    configurations: list[str] = field(default_factory=list)
    entry_points: list[str] = field(default_factory=list)
    test_frameworks: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[ImportRelation] = field(default_factory=list)
    architecture_summary: dict = field(default_factory=dict)
