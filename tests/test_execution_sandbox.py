from pathlib import Path
import subprocess
import pytest
from agent_orchestration.execution_sandbox import DockerSandbox, SandboxConfig, SandboxError, SandboxLimits

class FakeCompleted:
    def __init__(self, code=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = code, out, err

def fake_runner(*args, **kwargs):
    return FakeCompleted(0, "ok", "")

def make_sandbox(**kwargs):
    return DockerSandbox(SandboxConfig(limits=SandboxLimits(**kwargs)), runner=fake_runner)

def test_allowlisted_test_command_is_containerized(tmp_path: Path):
    sandbox = make_sandbox()
    result = sandbox.run_tests(tmp_path)
    assert result.ok
    argv = sandbox.build_docker_argv(tmp_path, ("python", "-m", "pytest", "-q"))
    assert argv[argv.index("--network") + 1] == "none"
    assert "--read-only" in argv
    assert argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "--memory" in argv and "--cpus" in argv and "--pids-limit" in argv

@pytest.mark.parametrize("command", [
    ("sh", "-c", "echo unsafe"),
    ("bash", "-c", "echo unsafe"),
    ("python", "-c", "print('arbitrary')"),
    ("python", "-m", "pip", "install", "anything"),
    ("curl", "https://example.com"),
])
def test_malicious_or_unapproved_command_is_rejected(tmp_path: Path, command):
    with pytest.raises(SandboxError):
        make_sandbox().run(tmp_path, command)

def test_path_traversal_is_rejected(tmp_path: Path):
    with pytest.raises(SandboxError):
        make_sandbox().run_targeted_tests(tmp_path, "../secret.py")

def test_absolute_target_is_rejected(tmp_path: Path):
    with pytest.raises(SandboxError):
        make_sandbox().run_targeted_tests(tmp_path, "/etc/passwd")

def test_failed_command_returns_structured_failure(tmp_path: Path):
    def runner(*args, **kwargs):
        return FakeCompleted(2, "test output", "assertion failed")
    result = DockerSandbox(SandboxConfig(), runner=runner).run_tests(tmp_path)
    assert result.exit_code == 2
    assert result.test_status == "failed"
    assert result.stdout == "test output"
    assert result.stderr == "assertion failed"

def test_timeout_returns_structured_timeout(tmp_path: Path):
    def runner(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="partial", stderr="hung")
    result = DockerSandbox(SandboxConfig(limits=SandboxLimits(timeout_seconds=1)), runner=runner).run_tests(tmp_path)
    assert result.timed_out is True
    assert result.test_status == "timeout"
    assert result.exit_code is None

def test_resource_limits_are_not_weakened():
    limits = SandboxLimits(memory_bytes=128 * 1024 * 1024, cpu_limit=0.5, pids_limit=16)
    sandbox = DockerSandbox(SandboxConfig(limits=limits), runner=fake_runner)
    argv = sandbox.build_docker_argv(Path("."), ("ruff", "check", "."))
    assert str(128 * 1024 * 1024) in argv
    assert "0.5" in argv
    assert "16" in argv

def test_network_is_always_disabled(tmp_path: Path):
    sandbox = make_sandbox()
    argv = sandbox.build_docker_argv(tmp_path, ("mypy", "."))
    assert argv[argv.index("--network") + 1] == "none"

def test_environment_is_minimal(tmp_path: Path):
    sandbox = make_sandbox()
    argv = sandbox.build_docker_argv(tmp_path, ("pytest", "-q"))
    assert "PATH=/usr/local/bin:/usr/bin:/bin" in argv
    assert "HOME=/tmp/home" in argv
    assert "PYTHONDONTWRITEBYTECODE=1" in argv

def test_no_host_fallback_when_docker_missing(tmp_path: Path):
    def runner(*args, **kwargs):
        raise FileNotFoundError("docker")
    with pytest.raises(Exception) as exc:
        DockerSandbox(SandboxConfig(), runner=runner).run_tests(tmp_path)
    assert "host execution" in str(exc.value)

def test_targeted_test_accepts_safe_relative_path(tmp_path: Path):
    result = make_sandbox().run_targeted_tests(tmp_path, "tests/test_example.py")
    assert result.test_status == "passed"
