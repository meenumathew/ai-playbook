"""Unit tests for guarded filesystem write helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.safety import (
    UnsafeDestinationError,
    WriteAccessError,
    assert_safe_destination,
    write_text_safely,
)


def test_assert_safe_destination_rejects_lexical_parent_escape(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside.txt"

    with pytest.raises(UnsafeDestinationError, match="outside target root"):
        assert_safe_destination(project_root / ".." / outside.name, project_root)


def test_write_text_safely_preserves_existing_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dst = tmp_path / "settings.json"
    dst.write_text("original", encoding="utf-8")
    original_replace = Path.replace

    def fail_replacing_destination(self: Path, target: str | Path) -> Path:
        if Path(target) == dst:
            raise OSError("simulated replace failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_replacing_destination)

    with pytest.raises(WriteAccessError, match="Cannot write"):
        write_text_safely(dst, "updated", tmp_path)

    assert dst.read_text(encoding="utf-8") == "original"
