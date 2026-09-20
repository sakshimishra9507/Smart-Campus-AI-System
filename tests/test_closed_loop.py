"""Tests for the closed-loop debugging workflow."""

from pathlib import Path
from agent_orchestration.closed_loop import ClosedLoopDebuggingWorkflow, WorkflowTimeline
from agent_orchestration.execution_sandbox import ExecutionResult
from agent_orchestration.patching import Patch, PatchFile


class FakeSandbox:
    def __init__(self, result):
        self.result = result
    def run_tests(self, root):
        return self.result
    def run_targeted_tests(self, root, target):
        return self.result


class FakeApplier:
    def __init__(self):
        self.applied = []
    def apply(self, patch, root):
        self.applied.append(patch.patch_id)


class FakeStore:
    pass


def result(ok, code=0):
    return ExecutionResult(("pytest", "-q"), code, "ok" if ok else "", "" if ok else "failure", 0.1, "passed" if ok else "failed")


def approved_patch(tmp_path: Path):
    path = tmp_path / "app.py"
    path.write_text("x = 1\n")
    return Patch(
        patch_id="p1",
            session_id="s1",
            problem="bug",
            status="approved",
        rationale="fix",
        files=(PatchFile.create("app.py", "x = 1\n", "x = 2\n"),),
    )


def test_approved_patch_passes_validation(tmp_path):
    p = approved_patch(tmp_path)
    applier = FakeApplier()
    wf = ClosedLoopDebuggingWorkflow(
        patch_store=FakeStore(),
        sandbox=FakeSandbox(result(True)),
        patch_applier=applier,
    )
    timeline = WorkflowTimeline()
    report = wf.validate_approved_patch(
        repository_root=str(tmp_path), patch=p, reported_problem="bug", timeline=timeline
    )
    assert report.resolved is True
    assert report.requires_approval is False
    assert applier.applied == ["p1"]
    assert any(e["event"] == "validation_completed" for e in timeline.events)


def test_failed_validation_is_analyzed_and_revision_requires_approval(tmp_path):
    p = approved_patch(tmp_path)
    applier = FakeApplier()
    proposed = {"patch": "new proposal"}
    wf = ClosedLoopDebuggingWorkflow(
        patch_store=FakeStore(),
        sandbox=FakeSandbox(result(False, 1)),
        patch_applier=applier,
        failure_analyzer=lambda context, execution: {
            "patch_caused_failure": True,
            "reason": "regression",
        },
        revision_proposer=lambda context: proposed,
    )
    report = wf.validate_approved_patch(
        repository_root=str(tmp_path), patch=p, reported_problem="bug"
    )
    assert report.resolved is False
    assert report.failure_analysis["patch_caused_failure"] is True
    assert report.revision_proposal == proposed
    assert report.requires_approval is True
    assert applier.applied == ["p1"]


def test_unapproved_patch_never_applies(tmp_path):
    p = approved_patch(tmp_path)
    object.__setattr__(p, "status", "pending")
    applier = FakeApplier()
    wf = ClosedLoopDebuggingWorkflow(
        patch_store=FakeStore(), sandbox=FakeSandbox(result(True)), patch_applier=applier
    )
    try:
        wf.validate_approved_patch(repository_root=str(tmp_path), patch=p, reported_problem="bug")
    except ValueError:
        pass
    else:
        raise AssertionError("pending patch must be rejected")
    assert applier.applied == []
