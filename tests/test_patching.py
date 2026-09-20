import json
from pathlib import Path

import pytest

from agent_orchestration.patching import (
    PatchApplier,
    PatchFile,
    PatchGenerator,
    PatchStore,
    validate_patch,
)


def make_output(original: str, proposed: str):
    return {
        "rationale": "Fix the failing handler.",
        "files": [{"path": "app.py", "original_content": original, "proposed_content": proposed}],
    }


def test_valid_patch_is_generated_and_has_diff(tmp_path: Path):
    original = "def login():\n    return 500\n"
    proposed = "def login():\n    return 200\n"
    (tmp_path / "app.py").write_text(original, encoding="utf-8")
    patch = PatchGenerator.from_ai_output(
        session_id="session-1",
        problem="login returns 500",
        output=make_output(original, proposed),
        repository_root=tmp_path,
    )
    assert patch.status == "pending"
    assert "--- a/app.py" in patch.diff
    assert "+++ b/app.py" in patch.diff
    assert patch.validation["valid"] is True


def test_invalid_patch_is_rejected_by_validation(tmp_path: Path):
    (tmp_path / "app.py").write_text("safe\n", encoding="utf-8")
    output = make_output("wrong\n", "changed\n")
    with pytest.raises(ValueError, match="Invalid generated patch"):
        PatchGenerator.from_ai_output(
            session_id="s", problem="p", output=output, repository_root=tmp_path
        )


def test_rejected_patch_cannot_be_applied(tmp_path: Path):
    original = "safe\n"
    (tmp_path / "app.py").write_text(original, encoding="utf-8")
    patch = PatchGenerator.from_ai_output(
        session_id="s", problem="p", output=make_output(original, "changed\n"), repository_root=tmp_path
    )
    store = PatchStore(tmp_path / ".patches")
    store.save(patch)
    rejected = store.set_status(patch.patch_id, "rejected")
    with pytest.raises(PermissionError):
        PatchApplier().apply(rejected, tmp_path)
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == original


def test_approved_patch_can_be_applied_only_after_approval(tmp_path: Path):
    original = "safe\n"
    (tmp_path / "app.py").write_text(original, encoding="utf-8")
    patch = PatchGenerator.from_ai_output(
        session_id="s", problem="p", output=make_output(original, "changed\n"), repository_root=tmp_path
    )
    store = PatchStore(tmp_path / ".patches")
    store.save(patch)
    with pytest.raises(PermissionError):
        PatchApplier().apply(patch, tmp_path)
    approved = store.set_status(patch.patch_id, "approved")
    PatchApplier().apply(approved, tmp_path)
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "changed\n"


@pytest.mark.parametrize(
    "output",
    [
        {},
        {"rationale": "x", "files": []},
        {"rationale": "x", "files": [{"path": "app.py"}]},
        {"rationale": "x", "files": "not-a-list"},
        {"rationale": "x", "files": [{"path": "../secret", "original_content": "", "proposed_content": "x"}]},
    ],
)
def test_malformed_ai_output(output, tmp_path: Path):
    (tmp_path / "app.py").write_text("safe\n", encoding="utf-8")
    with pytest.raises(ValueError):
        PatchGenerator.from_ai_output(
            session_id="s", problem="p", output=output, repository_root=tmp_path
        )


def test_patch_store_persists_proposal(tmp_path: Path):
    original = "safe\n"
    (tmp_path / "app.py").write_text(original, encoding="utf-8")
    patch = PatchGenerator.from_ai_output(
        session_id="s", problem="p", output=make_output(original, "changed\n"), repository_root=tmp_path
    )
    store = PatchStore(tmp_path / ".patches")
    store.save(patch)
    loaded = store.get(patch.patch_id)
    assert loaded.diff == patch.diff
    assert json.loads((tmp_path / ".patches" / f"{patch.patch_id}.json").read_text())["status"] == "pending"
