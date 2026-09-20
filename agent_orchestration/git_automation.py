"""Approved-patch Git automation with an auditable, fail-closed lifecycle.

Git commands are fixed operations, never user-provided shell strings. A commit or
push is impossible unless the patch has been explicitly approved and the exact
diff to be committed was previewed and acknowledged.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import subprocess
import time
from typing import Callable, Mapping, Sequence
from urllib import request
import json
import re

from .execution_sandbox import DockerSandbox
from .patching import Patch, PatchApplier, validate_patch


class GitAutomationError(Exception):
    pass


@dataclass(frozen=True)
class GitStatus:
    branch: str
    clean: bool
    staged_diff: str
    status_text: str


@dataclass(frozen=True)
class GitOperationStatus:
    operation: str
    success: bool
    detail: str
    timestamp: float


@dataclass
class AuditTrail:
    entries: list[GitOperationStatus] = field(default_factory=list)

    def record(self, operation: str, success: bool, detail: str) -> None:
        self.entries.append(GitOperationStatus(operation, success, detail, time.time()))


@dataclass(frozen=True)
class CommitPlan:
    patch_id: str
    branch: str
    diff: str
    files: tuple[str, ...]
    commit_message: str
    user_approval_required: bool = True


@dataclass(frozen=True)
class GitAutomationResult:
    branch_status: GitOperationStatus
    commit_status: GitOperationStatus | None
    push_status: GitOperationStatus | None
    pr_status: GitOperationStatus | None
    audit: tuple[GitOperationStatus, ...]


class GitAutomation:
    """Create a PR from an explicitly approved Patch."""

    BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,99}$")

    def __init__(
        self,
        repository_root: str | Path,
        *,
        sandbox: DockerSandbox,
        patch_applier,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
        github_request: Callable[..., Mapping[str, object]] | None = None,
    ) -> None:
        self.root = Path(repository_root).resolve()
        self.sandbox = sandbox
        self.patch_applier = patch_applier
        self._runner = runner or subprocess.run
        self._github_request = github_request or self._default_github_request
        self.audit = AuditTrail()
        self._preview_ack: dict[str, str] = {}

    def _git(self, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
        allowed = {
            "status", "diff", "switch", "checkout", "add", "commit",
            "push", "rev-parse", "branch",
        }
        if not args or args[0] not in allowed or any(
            not isinstance(x, str) or "\n" in x or "\r" in x for x in args
        ):
            raise GitAutomationError("Git operation is not allowlisted.")
        return self._runner(
            ["git", *args], cwd=str(self.root), capture_output=True,
            text=True, check=False,
        )

    def _require_ok(self, result: subprocess.CompletedProcess[str], operation: str) -> str:
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            self.audit.record(operation, False, detail)
            raise GitAutomationError(f"{operation} failed: {detail}")
        return result.stdout.strip()

    def create_branch(self, branch: str, base_ref: str = "main") -> GitOperationStatus:
        self._validate_branch(branch)
        result = self._git(("switch", "-c", branch, base_ref))
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            status = GitOperationStatus("branch", False, detail, time.time())
            self.audit.entries.append(status)
            raise GitAutomationError(detail)
        status = GitOperationStatus("branch", True, branch, time.time())
        self.audit.entries.append(status)
        return status

    def preview(self, patch: Patch, commit_message: str) -> CommitPlan:
        self._require_approved(patch)
        validation = validate_patch(patch, self.root)
        if not validation["valid"]:
            raise GitAutomationError("Patch is no longer valid: " + "; ".join(validation["errors"]))
        branch = self._require_ok(self._git(("branch", "--show-current")), "branch status")
        if not branch:
            raise GitAutomationError("Detached HEAD is not allowed.")
        plan = CommitPlan(
            patch.patch_id, branch, patch.diff,
            tuple(f.path for f in patch.files), commit_message,
        )
        self._preview_ack[patch.patch_id] = self._fingerprint(plan)
        self.audit.record("commit_preview", True, f"{len(plan.files)} file(s)")
        return plan

    def acknowledge_preview(self, plan: CommitPlan) -> None:
        if self._preview_ack.get(plan.patch_id) != self._fingerprint(plan):
            raise GitAutomationError("Commit preview is missing or stale.")
        self.audit.record("preview_acknowledged", True, plan.patch_id)

    def apply_approved_patch(self, patch: Patch) -> GitOperationStatus:
        self._require_approved(patch)
        validation = validate_patch(patch, self.root)
        if not validation["valid"]:
            raise GitAutomationError("Patch failed validation: " + "; ".join(validation["errors"]))
        self.patch_applier.apply(patch, self.root)
        status = GitOperationStatus("patch_application", True, patch.patch_id, time.time())
        self.audit.entries.append(status)
        return status

    def validate(self, targeted_test: str | None = None):
        result = (
            self.sandbox.run_targeted_tests(self.root, targeted_test)
            if targeted_test else self.sandbox.run_tests(self.root)
        )
        self.audit.record("validation", result.ok, result.test_status)
        if not result.ok:
            raise GitAutomationError(
                f"Validation failed: {result.test_status}; {result.stderr or result.stdout}"
            )
        return result

    def status(self) -> GitStatus:
        branch = self._require_ok(self._git(("branch", "--show-current")), "branch status")
        text = self._require_ok(self._git(("status", "--short")), "status")
        diff = self._require_ok(self._git(("diff", "--cached")), "staged diff")
        return GitStatus(branch, not bool(text), diff, text)

    def commit(self, patch: Patch, commit_message: str, *, preview: CommitPlan) -> GitOperationStatus:
        self._require_approved(patch)
        if self._preview_ack.get(patch.patch_id) != self._fingerprint(preview):
            raise GitAutomationError("Commit requires acknowledgement of the exact preview.")
        if tuple(f.path for f in patch.files) != preview.files:
            raise GitAutomationError("Patch changed after preview.")
        for item in patch.files:
            self._require_ok(self._git(("add", "--", item.path)), "stage")
        staged = self._require_ok(self._git(("diff", "--cached")), "staged diff")
        if staged != preview.diff:
            raise GitAutomationError("Staged diff differs from the approved preview.")
        result = self._git(("commit", "-m", commit_message))
        self._require_ok(result, "commit")
        status = GitOperationStatus("commit", True, result.stdout.strip(), time.time())
        self.audit.entries.append(status)
        return status

    def push(self, branch: str) -> GitOperationStatus:
        self._validate_branch(branch)
        result = self._git(("push", "-u", "origin", branch))
        detail = result.stdout.strip() or result.stderr.strip()
        if result.returncode:
            status = GitOperationStatus("push", False, detail, time.time())
            self.audit.entries.append(status)
            raise GitAutomationError(detail)
        status = GitOperationStatus("push", True, detail, time.time())
        self.audit.entries.append(status)
        return status

    def create_pull_request(self, *, owner_repo: str, head: str, base: str, title: str, body: str) -> GitOperationStatus:
        payload = {"title": title, "body": body, "head": head, "base": base}
        response = self._github_request(owner_repo, payload)
        status = GitOperationStatus("pull_request", True, str(response.get("html_url") or response.get("number")), time.time())
        self.audit.entries.append(status)
        return status

    def run_approved_flow(
        self, patch: Patch, *, branch: str, commit_message: str,
        owner_repo: str, pr_title: str, pr_body: str,
        base_ref: str = "main", targeted_test: str | None = None,
    ) -> GitAutomationResult:
        self._require_approved(patch)
        branch_status = self.create_branch(branch, base_ref)
        self.apply_approved_patch(patch)
        self.validate(targeted_test)
        plan = self.preview(patch, commit_message)
        self.acknowledge_preview(plan)
        commit_status = self.commit(patch, commit_message, preview=plan)
        push_status = self.push(branch)
        pr_status = self.create_pull_request(
            owner_repo=owner_repo, head=branch, base=base_ref,
            title=pr_title, body=pr_body,
        )
        return GitAutomationResult(
            branch_status, commit_status, push_status, pr_status,
            tuple(self.audit.entries),
        )

    @staticmethod
    def _validate_branch(branch: str) -> None:
        if not GitAutomation.BRANCH_RE.fullmatch(branch) or ".." in branch or branch.endswith(("/", ".")):
            raise GitAutomationError("Unsafe branch name.")

    @staticmethod
    def _require_approved(patch: Patch) -> None:
        if patch.status != "approved":
            raise GitAutomationError("Git automation requires an explicitly approved patch.")

    @staticmethod
    def _fingerprint(plan: CommitPlan) -> str:
        import hashlib
        return hashlib.sha256(
            (plan.patch_id + "\0" + plan.branch + "\0" + plan.diff + "\0" + plan.commit_message).encode()
        ).hexdigest()

    @staticmethod
    def _default_github_request(owner_repo: str, payload: Mapping[str, object]) -> Mapping[str, object]:
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            raise GitAutomationError("GITHUB_TOKEN is required to create a Pull Request.")
        data = json.dumps(dict(payload)).encode()
        req = request.Request(
            f"https://api.github.com/repos/{owner_repo}/pulls",
            data=data,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GitAutomationError(f"Pull Request creation failed: {exc}") from exc
