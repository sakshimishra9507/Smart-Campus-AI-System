"""Patch review orchestration for FixerAgent output."""
from typing import Any, Mapping
from .agents import FixerAgent
from .patching import Patch, PatchGenerator, PatchStore, PatchApplier


class PatchReviewService:
    """Turns FixerAgent's structured output into a stored, reviewable patch."""

    def __init__(self, fixer: FixerAgent, store: PatchStore):
        self.fixer = fixer
        self.store = store

    def generate(
        self, task, *, investigation: Mapping[str, Any], root_cause: Mapping[str, Any],
        relevant_files: list[str], relevant_code: Mapping[str, Any],
        tests: Mapping[str, Any], repository_root: str,
    ) -> Patch:
        output = self.fixer.propose_fix(
            task,
            {"root_cause": root_cause, "affected_files": relevant_files, "evidence": investigation},
        )
        patch = PatchGenerator.from_ai_output(
            session_id=task.task_id, problem=task.description,
            output=output, repository_root=repository_root,
        )
        return self.store.save(patch)

    def approve(self, patch_id: str) -> Patch:
        return self.store.set_status(patch_id, "approved")

    def reject(self, patch_id: str) -> Patch:
        return self.store.set_status(patch_id, "rejected")

    def apply_approved(self, patch_id: str, repository_root: str) -> Patch:
        patch = self.store.get(patch_id)
        return PatchApplier().apply(patch, repository_root)
