"""Isolated repository command execution using a Docker boundary."""
from __future__ import annotations
from dataclasses import dataclass
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Callable, Sequence

class SandboxError(Exception):
    """Base error for sandbox validation or execution."""

class SandboxUnavailable(SandboxError):
    """Raised when Docker cannot be used."""

@dataclass(frozen=True)
class SandboxLimits:
    timeout_seconds: float = 30.0
    memory_bytes: int = 512 * 1024 * 1024
    cpu_limit: float = 1.0
    pids_limit: int = 64
    max_output_bytes: int = 1_000_000
    def __post_init__(self) -> None:
        if not 0.1 <= self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be between 0.1 and 300.")
        if not 16 * 1024 * 1024 <= self.memory_bytes <= 8 * 1024**3:
            raise ValueError("memory_bytes is outside the safe range.")
        if not 0.1 <= self.cpu_limit <= 8:
            raise ValueError("cpu_limit is outside the safe range.")
        if not 8 <= self.pids_limit <= 512:
            raise ValueError("pids_limit is outside the safe range.")
        if not 1024 <= self.max_output_bytes <= 10_000_000:
            raise ValueError("max_output_bytes is outside the safe range.")

@dataclass(frozen=True)
class ExecutionResult:
    command: tuple[str, ...]
    exit_code: int | None
    stdout: str
    stderr: str
    duration: float
    test_status: str
    timed_out: bool = False
    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and self.test_status == "passed"

@dataclass(frozen=True)
class SandboxConfig:
    image: str = os.getenv("REPOSITORY_SANDBOX_IMAGE", "repository-sandbox:latest")
    docker_binary: str = "docker"
    limits: SandboxLimits = SandboxLimits()

@dataclass(frozen=True)
class CommandPolicy:
    executable: str
    prefix: tuple[str, ...]
    max_args: int = 20
    def accepts(self, argv: Sequence[str]) -> bool:
        return bool(argv) and tuple(argv[:1]) == (self.executable,) and tuple(argv[:len(self.prefix)]) == self.prefix and len(argv) <= self.max_args and all(_safe_arg(a) for a in argv)

_SHELL_META = re.compile(r"[;&|$><\n\r]")
def _safe_arg(value: str) -> bool:
    return isinstance(value, str) and bool(value) and not _SHELL_META.search(value)

class DockerSandbox:
    """Run only approved developer tools inside a hardened container."""
    POLICIES = (
        CommandPolicy("python", ("python", "-m", "pytest")),
        CommandPolicy("pytest", ("pytest",)),
        CommandPolicy("ruff", ("ruff", "check")),
        CommandPolicy("mypy", ("mypy",)),
    )
    def __init__(self, config: SandboxConfig | None = None, *, runner: Callable[..., subprocess.CompletedProcess[str]] | None = None) -> None:
        self.config = config or SandboxConfig()
        self._runner = runner or subprocess.run

    def _policy(self, argv: Sequence[str]) -> CommandPolicy:
        for policy in self.POLICIES:
            if policy.accepts(argv):
                return policy
        raise SandboxError("Command is not allowlisted.")

    def _workspace(self, repository_root: str | Path) -> Path:
        root = Path(repository_root).resolve()
        if not root.is_dir():
            raise SandboxError("Repository workspace must be an existing directory.")
        return root

    def build_docker_argv(self, repository_root: str | Path, command: Sequence[str]) -> list[str]:
        root = self._workspace(repository_root)
        argv = tuple(command)
        self._policy(argv)
        limits = self.config.limits
        return [
            self.config.docker_binary, "run", "--rm",
            "--network", "none", "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true",
            "--pids-limit", str(limits.pids_limit),
            "--memory", str(limits.memory_bytes),
            "--memory-swap", str(limits.memory_bytes),
            "--cpus", str(limits.cpu_limit),
            "--ulimit", "nofile=256:256",
            "--mount", f"type=bind,src={root},dst=/workspace,readonly",
            "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m",
            "--workdir", "/workspace",
            "--env", "PATH=/usr/local/bin:/usr/bin:/bin",
            "--env", "HOME=/tmp/home",
            "--env", "LANG=C.UTF-8",
            "--env", "LC_ALL=C.UTF-8",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            self.config.image, *argv,
        ]

    def run(self, repository_root: str | Path, command: Sequence[str]) -> ExecutionResult:
        docker_argv = self.build_docker_argv(repository_root, command)
        started = time.monotonic()
        try:
            completed = self._runner(
                docker_argv, capture_output=True, text=True,
                timeout=self.config.limits.timeout_seconds, check=False,
                env={"PATH": os.environ.get("PATH", ""), "DOCKER_CONFIG": os.environ.get("DOCKER_CONFIG", "")},
            )
        except FileNotFoundError as exc:
            raise SandboxUnavailable("Docker CLI is unavailable; refusing host execution.") from exc
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(tuple(command), None, _bounded(exc.stdout), _bounded(exc.stderr), time.monotonic() - started, "timeout", True)
        return ExecutionResult(tuple(command), completed.returncode, _bounded(completed.stdout), _bounded(completed.stderr), time.monotonic() - started, "passed" if completed.returncode == 0 else "failed")

    def run_tests(self, repository_root: str | Path) -> ExecutionResult:
        return self.run(repository_root, ("python", "-m", "pytest", "-q", "-p", "no:cacheprovider"))

    def run_targeted_tests(self, repository_root: str | Path, target: str) -> ExecutionResult:
        self._validate_target(target)
        return self.run(repository_root, ("python", "-m", "pytest", "-q", "-p", "no:cacheprovider", target))

    def run_linter(self, repository_root: str | Path) -> ExecutionResult:
        return self.run(repository_root, ("ruff", "check", "."))

    def run_type_checker(self, repository_root: str | Path) -> ExecutionResult:
        return self.run(repository_root, ("mypy", "."))

    @staticmethod
    def _validate_target(target: str) -> None:
        if not _safe_arg(target) or target.startswith("/") or target.startswith("~") or ".." in Path(target).parts:
            raise SandboxError("Target path is unsafe.")

def _bounded(value: str | bytes | None, limit: int = 1_000_000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value[:limit]
