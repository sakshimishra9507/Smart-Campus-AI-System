from pathlib import Path
import subprocess
import pytest

from agent_orchestration.git_automation import GitAutomation, GitAutomationError
from agent_orchestration.execution_sandbox import ExecutionResult
from agent_orchestration.patching import Patch, PatchFile


class FakeSandbox:
    def __init__(self, ok=True): self.ok = ok
    def run_tests(self, root):
        return ExecutionResult(("pytest","-q"), 0 if self.ok else 1, "", "" if self.ok else "failed", .1, "passed" if self.ok else "failed")


class FakeApplier:
    def apply(self, patch, root): return patch


def fake_ok(*args, **kwargs):
    cmd = args[0]
    if cmd[-1:] == ["--show-current"]: out = "feature/test\n"
    elif "status" in cmd: out = ""
    elif "diff" in cmd: out = ""
    else: out = "ok\n"
    return subprocess.CompletedProcess(cmd, 0, out, "")


def patch(tmp_path):
    (tmp_path / "app.py").write_text("x=1\n")
    return Patch(
        "p1", "s1", "bug", "fix",
        (PatchFile.create("app.py", "x=1\n", "x=2\n"),),
        "approved",
    )


def make(tmp_path, runner=fake_ok, gh=None):
    return GitAutomation(
        tmp_path, sandbox=FakeSandbox(), patch_applier=FakeApplier(),
        runner=runner, github_request=gh or (lambda repo, payload: {"number": 7, "html_url": "https://github.com/x/y/pull/7"})
    )


def test_branch_operation(tmp_path):
    g = make(tmp_path)
    s = g.create_branch("feature/test")
    assert s.success and s.operation == "branch"


def test_unapproved_patch_cannot_preview_or_commit(tmp_path):
    p = patch(tmp_path); p.status = "pending"
    g = make(tmp_path)
    with pytest.raises(GitAutomationError): g.preview(p, "fix")
    with pytest.raises(GitAutomationError): g.commit(p, "fix", preview=None)


def test_preview_exposes_exact_diff(tmp_path):
    g = make(tmp_path)
    plan = g.preview(patch(tmp_path), "fix")
    assert "x=1" in plan.diff and "x=2" in plan.diff
    assert plan.files == ("app.py",)


def test_commit_requires_preview_ack(tmp_path):
    p = patch(tmp_path); g = make(tmp_path)
    plan = g.preview(p, "fix")
    g._preview_ack.clear()
    with pytest.raises(GitAutomationError): g.commit(p, "fix", preview=plan)


def test_commit_operation(tmp_path):
    p = patch(tmp_path); g = make(tmp_path)
    plan = g.preview(p, "fix"); g.acknowledge_preview(plan)
    def runner(*args, **kwargs):
        cmd = args[0]
        if cmd[-1:] == ["--show-current"]: out = "feature/test\n"
        elif "diff" in cmd: out = plan.diff
        else: out = "ok\n"
        return subprocess.CompletedProcess(cmd, 0, out, "")
    g._runner = runner
    s = g.commit(p, "fix", preview=plan)
    assert s.success


def test_push_operation(tmp_path):
    s = make(tmp_path).push("feature/test")
    assert s.success and s.operation == "push"


def test_push_failure_is_audited(tmp_path):
    def fail(*args, **kwargs): return subprocess.CompletedProcess(args[0], 1, "", "push failed")
    g = make(tmp_path, fail)
    with pytest.raises(GitAutomationError): g.push("feature/test")
    assert g.audit.entries[-1].operation == "push"
    assert not g.audit.entries[-1].success


def test_pr_operation(tmp_path):
    s = make(tmp_path).create_pull_request(
        owner_repo="owner/repo", head="feature/test", base="main",
        title="Fix", body="Approved fix"
    )
    assert s.success and s.operation == "pull_request"


def test_validation_failure_stops_before_commit(tmp_path):
    g = make(tmp_path)
    g.sandbox = FakeSandbox(ok=False)
    with pytest.raises(GitAutomationError):
        g.validate()
    assert g.audit.entries[-1].operation == "validation"


def test_audit_trail_records_preview_and_operations(tmp_path):
    g = make(tmp_path)
    g.preview(patch(tmp_path), "fix")
    assert any(e.operation == "commit_preview" for e in g.audit.entries)
