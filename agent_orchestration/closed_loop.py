"""Closed-loop execution and validation for approved patches.

This module connects diagnosis, approval, patch application, sandbox execution,
failure analysis, and final validation without ever auto-approving a revision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .execution_sandbox import DockerSandbox, ExecutionResult
from .patching import Patch, PatchApplier, PatchStore, validate_patch


@dataclass(frozen=True)
class ValidationReport:
    resolved: bool
    initial_test: ExecutionResult
    regression_test: ExecutionResult | None
    failure_analysis: Mapping[str, Any] | None
    revision_proposal: Mapping[str, Any] | None
    requires_approval: bool
    summary: str


@dataclass
class WorkflowTimeline:
    events: list[dict[str, Any]] = field(default_factory=list)

    def emit(self, name: str, **payload: Any) -> None:
        self.events.append({"event": name, "payload": payload})


class ClosedLoopDebuggingWorkflow:
    """Orchestrate the complete approved-fix -> sandbox -> validation loop."""

    def __init__(
        self,
        *,
        patch_store: PatchStore,
        sandbox: DockerSandbox,
        patch_applier: PatchApplier,
        failure_analyzer: Callable[[Mapping[str, Any], ExecutionResult], Mapping[str, Any]] | None = None,
        revision_proposer: Callable[[Mapping[str, Any]], Mapping[str, Any]] | None = None,
    ) -> None:
        self.patch_store = patch_store
        self.sandbox = sandbox
        self.patch_applier = patch_applier
        self.failure_analyzer = failure_analyzer
        self.revision_proposer = revision_proposer

    def validate_approved_patch(
        self,
        *,
        repository_root: str,
        patch: Patch,
        reported_problem: str,
        targeted_test: str | None = None,
        timeline: WorkflowTimeline | None = None,
    ) -> ValidationReport:
        timeline = timeline or WorkflowTimeline()
        timeline.emit("patch_application_started", patch_id=patch.patch_id)

        if patch.status != "approved":
            raise ValueError("Only explicitly approved patches may be applied.")
        validation = validate_patch(patch, repository_root)
        if not validation["valid"]:
            raise ValueError("Patch failed validation before application: " + "; ".join(validation["errors"]))

        self.patch_applier.apply(patch, repository_root)
        timeline.emit("patch_applied", patch_id=patch.patch_id)

        timeline.emit("sandbox_started", phase="targeted_test")
        initial = (
            self.sandbox.run_targeted_tests(repository_root, targeted_test)
            if targeted_test
            else self.sandbox.run_tests(repository_root)
        )
        timeline.emit(
            "tests_completed",
            status=initial.test_status,
            exit_code=initial.exit_code,
        )

        if initial.ok:
            timeline.emit("validation_completed", resolved=True)
            return ValidationReport(
                True, initial, None, None, None, False,
                "The approved patch passed the configured validation test.",
            )

        timeline.emit("test_failure_captured", stderr=initial.stderr, stdout=initial.stdout)
        failure = (
            self.failure_analyzer(
                {"reported_problem": reported_problem, "patch_id": patch.patch_id},
                initial,
            )
            if self.failure_analyzer
            else {"cause": "validation_failure", "patch_caused_failure": "unknown"}
        )
        timeline.emit("failure_analyzed", analysis=dict(failure))

        revision = self.revision_proposer(
            {"reported_problem": reported_problem, "patch_id": patch.patch_id, "failure": failure}
        ) if self.revision_proposer else None
        if revision is not None:
            timeline.emit("revised_proposal_created", proposal=revision)
        timeline.emit("approval_required", reason="every new modification requires user approval")

        return ValidationReport(
            False, initial, initial, failure, revision, True,
            "The approved patch did not resolve validation. Any revised proposal requires separate user approval.",
        )
