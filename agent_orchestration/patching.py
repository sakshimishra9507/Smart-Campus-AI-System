"""Controlled patch generation, review, validation, and application.

Patches are data until an explicit approval action. No shell commands or
unrestricted execution are available in this subsystem.
"""
from dataclasses import dataclass, field
from difflib import unified_diff
import json
from pathlib import Path
import re
from typing import Any, Mapping
from uuid import uuid4


_SAFE_PATH = re.compile(r"^[^/\\][^:]*$")


@dataclass(frozen=True)
class PatchFile:
    path: str
    original_content: str
    proposed_content: str
    diff: str

    @classmethod
    def create(cls, path: str, original_content: str, proposed_content: str) -> "PatchFile":
        if not _valid_relative_path(path):
            raise ValueError(f"Unsafe patch path: {path!r}")
        diff = "".join(
            unified_diff(
                original_content.splitlines(keepends=True),
                proposed_content.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
        )
        return cls(path, original_content, proposed_content, diff)


@dataclass
class Patch:
    patch_id: str
    session_id: str
    problem: str
    rationale: str
    files: tuple[PatchFile, ...]
    status: str = "pending"
    validation: Mapping[str, Any] = field(default_factory=dict)

    @property
    def diff(self) -> str:
        return "".join(item.diff for item in self.files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "patch_id": self.patch_id,
            "session_id": self.session_id,
            "problem": self.problem,
            "rationale": self.rationale,
            "status": self.status,
            "validation": dict(self.validation),
            "files": [
                {
                    "path": f.path,
                    "original_content": f.original_content,
                    "proposed_content": f.proposed_content,
                    "diff": f.diff,
                }
                for f in self.files
            ],
            "diff": self.diff,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Patch":
        files = tuple(
            PatchFile(
                str(item["path"]),
                str(item["original_content"]),
                str(item["proposed_content"]),
                str(item["diff"]),
            )
            for item in data["files"]
        )
        return cls(
            patch_id=str(data["patch_id"]),
            session_id=str(data["session_id"]),
            problem=str(data["problem"]),
            rationale=str(data["rationale"]),
            files=files,
            status=str(data.get("status", "pending")),
            validation=dict(data.get("validation", {})),
        )


def _valid_relative_path(path: str) -> bool:
    p = Path(path)
    return bool(path and _SAFE_PATH.match(path) and not p.is_absolute() and ".." not in p.parts)


def validate_patch(patch: Patch, repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    errors: list[str] = []
    if patch.status not in {"pending", "approved", "rejected"}:
        errors.append("Invalid patch status.")
    if not patch.files:
        errors.append("Patch must contain at least one file.")

    for item in patch.files:
        if not _valid_relative_path(item.path):
            errors.append(f"Unsafe path: {item.path}")
            continue
        target = (root / item.path).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            errors.append(f"Path escapes repository root: {item.path}")
            continue
        current = target.read_text(encoding="utf-8") if target.exists() else ""
        if current != item.original_content:
            errors.append(f"Original content mismatch: {item.path}")
        regenerated = PatchFile.create(item.path, item.original_content, item.proposed_content).diff
        if regenerated != item.diff:
            errors.append(f"Diff mismatch: {item.path}")

    return {"valid": not errors, "errors": errors}


class PatchStore:
    """Durable JSON store for proposed patches, separate from source files."""

    def __init__(self, storage_dir: str | Path):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save(self, patch: Patch) -> Patch:
        (self.storage_dir / f"{patch.patch_id}.json").write_text(
            json.dumps(patch.to_dict(), indent=2),
            encoding="utf-8",
        )
        return patch

    def get(self, patch_id: str) -> Patch:
        path = self.storage_dir / f"{patch_id}.json"
        if not path.exists():
            raise KeyError(f"Unknown patch: {patch_id}")
        return Patch.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def set_status(self, patch_id: str, status: str) -> Patch:
        if status not in {"approved", "rejected"}:
            raise ValueError("Status must be approved or rejected.")
        patch = self.get(patch_id)
        if patch.status != "pending":
            raise ValueError(f"Patch is already {patch.status}.")
        patch.status = status
        return self.save(patch)


class PatchGenerator:
    @staticmethod
    def from_ai_output(
        *,
        session_id: str,
        problem: str,
        output: Mapping[str, Any],
        repository_root: str | Path,
    ) -> Patch:
        if not isinstance(output, Mapping):
            raise ValueError("AI patch output must be an object.")
        rationale = output.get("rationale")
        raw_files = output.get("files")
        if not isinstance(rationale, str) or not rationale.strip():
            raise ValueError("AI patch output requires a non-empty rationale.")
        if not isinstance(raw_files, list) or not raw_files:
            raise ValueError("AI patch output requires a non-empty files list.")

        files: list[PatchFile] = []
        for item in raw_files:
            if not isinstance(item, Mapping):
                raise ValueError("Each patch file must be an object.")
            for key in ("path", "original_content", "proposed_content"):
                if not isinstance(item.get(key), str):
                    raise ValueError(f"Patch file requires string field: {key}")
            files.append(PatchFile.create(item["path"], item["original_content"], item["proposed_content"]))

        patch = Patch(uuid4().hex, session_id, problem, rationale.strip(), tuple(files))
        result = validate_patch(patch, repository_root)
        patch.validation = result
        if not result["valid"]:
            raise ValueError("Invalid generated patch: " + "; ".join(result["errors"]))
        return patch


class PatchApplier:
    """Applies only an explicitly approved, revalidated patch."""

    def apply(self, patch: Patch, repository_root: str | Path) -> Patch:
        if patch.status != "approved":
            raise PermissionError("Only an approved patch may be applied.")
        validation = validate_patch(patch, repository_root)
        if not validation["valid"]:
            raise ValueError("Approved patch failed validation: " + "; ".join(validation["errors"]))

        root = Path(repository_root).resolve()
        for item in patch.files:
            target = (root / item.path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item.proposed_content, encoding="utf-8")
        patch.validation = {**validation, "applied": True}
        return patch
