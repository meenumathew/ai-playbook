"""Unit tests for guarded filesystem write helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.safety import (
    UnsafeDestinationError,
    WriteAccessError,
    assert_safe_destination,
    rename_safely,
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


def test_write_text_safely_creates_missing_parent(tmp_path: Path) -> None:
    dst = tmp_path / "nested" / "settings.json"

    write_text_safely(dst, "created", tmp_path)

    assert dst.read_text(encoding="utf-8") == "created"


def test_rename_safely_moves_nested_file(tmp_path: Path) -> None:
    src = tmp_path / "nested" / "active.agent.md"
    src.parent.mkdir()
    src.write_text("agent")
    dst = src.with_name("active.agent.md.disabled")

    rename_safely(src, dst, tmp_path)

    assert not src.exists()
    assert dst.read_text() == "agent"


def test_rename_safely_refuses_to_overwrite_existing_destination(tmp_path: Path) -> None:
    src = tmp_path / "active.agent.md"
    dst = tmp_path / "active.agent.md.disabled"
    src.write_text("active")
    dst.write_text("preserve disabled copy")

    with pytest.raises(WriteAccessError, match="already exists"):
        rename_safely(src, dst, tmp_path)

    assert src.read_text() == "active"
    assert dst.read_text() == "preserve disabled copy"


def test_rename_safely_reports_an_unusable_destination_parent(tmp_path: Path) -> None:
    """A filesystem refusal surfaces as WriteAccessError with the source intact.

    Callers catch WriteAccessError to report a path they cannot write; letting
    the raw OSError escape would abort a deploy with a traceback instead.
    """
    src = tmp_path / "active.agent.md"
    src.write_text("active")
    blocker = tmp_path / "blocker"
    blocker.write_text("a file where a directory is needed")

    with pytest.raises(WriteAccessError, match="Cannot rename"):
        rename_safely(src, blocker / "active.agent.md.disabled", tmp_path)

    assert src.read_text() == "active"


def test_write_text_preserves_existing_destination_mode(tmp_path: Path) -> None:
    """The atomic temp-sibling is created at 0600; replace() would clobber a
    pre-existing 0644 and make deployed files unreadable to other users."""
    import stat

    from deploy_ai_playbook.safety import write_text_safely

    dst = tmp_path / "CLAUDE.md"
    dst.write_text("old\n", encoding="utf-8")
    dst.chmod(0o644)

    write_text_safely(dst, "new\n", tmp_path)

    assert stat.S_IMODE(dst.stat().st_mode) == 0o644


def test_write_text_new_file_honors_umask_not_tempfile_0600(tmp_path: Path) -> None:
    import os
    import stat

    from deploy_ai_playbook.safety import write_text_safely

    dst = tmp_path / "fresh.md"

    write_text_safely(dst, "content\n", tmp_path)

    umask = os.umask(0)
    os.umask(umask)
    assert stat.S_IMODE(dst.stat().st_mode) == 0o666 & ~umask


def test_write_bytes_preserves_existing_destination_mode(tmp_path: Path) -> None:
    import stat

    from deploy_ai_playbook.safety import write_bytes_safely

    dst = tmp_path / "hook.bin"
    dst.write_bytes(b"old")
    dst.chmod(0o640)

    write_bytes_safely(dst, b"new", tmp_path)

    assert stat.S_IMODE(dst.stat().st_mode) == 0o640
