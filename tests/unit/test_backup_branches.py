"""Branch-coverage tests for backup.py — exercises rotation, timestamp
collisions, and restore-failure cleanup paths that the integration tests miss.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import patch

import pytest

from deploy_ai_playbook.backup import (
    BACKUP_METADATA_FILE,
    MAX_BACKUPS,
    _rotate_backups,
    backup_deployed_files,
    latest_backup_for_tool,
    restore_backup,
)
from deploy_ai_playbook.paths import BACKUP_DIR, TOOL_DESTINATIONS, Tool
from deploy_ai_playbook.safety import UnsafeDestinationError


def _seed_deployment(project_root: Path, tool: Tool) -> None:
    """Create the four deployed dirs + rules file so backup_deployed_files has work to do."""
    destinations = TOOL_DESTINATIONS[tool]
    for key in ("agents", "knowledge-base", "skills", "templates"):
        d = project_root / destinations[key]
        d.mkdir(parents=True)
        (d / "placeholder.md").write_text(f"# {key}")
    if "commands" in destinations:
        d = project_root / destinations["commands"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "alpha.md").write_text("/alpha")
    rules_path = project_root / destinations["rules"]
    rules_path.parent.mkdir(parents=True, exist_ok=True)
    rules_path.write_text("rules content")


def test_rotate_backups_no_op_when_dir_missing(tmp_path: Path) -> None:
    """If the backup dir doesn't exist yet, rotation must not raise."""
    _rotate_backups(tmp_path)  # no .playbook-backup dir present
    assert not (tmp_path / BACKUP_DIR).exists()


def test_rotate_backups_keeps_only_max_backups(tmp_path: Path) -> None:
    backup_dir = tmp_path / BACKUP_DIR
    backup_dir.mkdir()
    # Create more backups than MAX_BACKUPS (5).
    for i in range(8):
        d = backup_dir / f"20260520-000000-{i:06d}"
        d.mkdir()
        (d / "marker").write_text(str(i))

    _rotate_backups(tmp_path)

    remaining = sorted([p.name for p in backup_dir.iterdir() if p.is_dir()])
    assert len(remaining) == 5, f"expected 5 backups, found {len(remaining)}: {remaining}"
    # Newest five (highest suffix) should remain. Sorted descending, slice [:5].
    assert remaining[0].endswith("000003")  # oldest of the kept set
    assert remaining[-1].endswith("000007")  # newest


def test_rotate_backups_keeps_max_backups_per_tool(tmp_path: Path) -> None:
    backup_dir = tmp_path / BACKUP_DIR
    backup_dir.mkdir()
    copilot_backup = backup_dir / "20260519-000000-000000"
    copilot_backup.mkdir()
    (copilot_backup / BACKUP_METADATA_FILE).write_text("tool: copilot\n")
    for i in range(MAX_BACKUPS + 1):
        backup_root = backup_dir / f"20260520-000000-{i:06d}"
        backup_root.mkdir()
        (backup_root / BACKUP_METADATA_FILE).write_text("tool: claude\n")

    _rotate_backups(tmp_path)

    assert copilot_backup.exists()
    claude_backups = [
        backup_root
        for backup_root in backup_dir.iterdir()
        if backup_root.is_dir()
        and "tool: claude" in (backup_root / BACKUP_METADATA_FILE).read_text()
    ]
    assert len(claude_backups) == MAX_BACKUPS
    assert not (backup_dir / "20260520-000000-000000").exists()


def test_backup_deployed_files_returns_none_when_nothing_deployed(tmp_path: Path) -> None:
    """No deployed dirs → no backup needed."""
    result = backup_deployed_files(tmp_path, Tool.claude)
    assert result is None
    assert not (tmp_path / BACKUP_DIR).exists()


def test_backup_deployed_files_creates_microsecond_dir(tmp_path: Path) -> None:
    _seed_deployment(tmp_path, Tool.claude)

    backup_root = backup_deployed_files(tmp_path, Tool.claude)

    assert backup_root is not None
    assert backup_root.exists()
    # Microsecond format: YYYYMMDD-HHMMSS-uuuuuu (15 digits + 2 dashes = 22 chars).
    assert len(backup_root.name) == 22
    assert f"tool: {Tool.claude.value}" in (backup_root / BACKUP_METADATA_FILE).read_text()


def test_backup_deployed_files_writes_metadata_after_complete_backup(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_deployment(tmp_path, Tool.claude)
    original_copytree = shutil.copytree

    def fail_on_knowledge_base_copy(
        src: str | Path, dst: str | Path, *args: object, **kwargs: object
    ):
        if Path(src).name == "knowledge-base":
            raise OSError("simulated copy failure")
        return original_copytree(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copytree", fail_on_knowledge_base_copy)

    with pytest.raises(OSError, match="simulated copy failure"):
        backup_deployed_files(tmp_path, Tool.claude)

    backup_roots = list((tmp_path / BACKUP_DIR).iterdir())
    assert len(backup_roots) == 1
    assert not (backup_roots[0] / BACKUP_METADATA_FILE).exists()


def test_backup_deployed_files_rejects_symlinked_destination_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside-agents"
    outside.mkdir()
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()
    (claude_dir / "agents").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeDestinationError, match="refuses to write through symlink"):
        backup_deployed_files(project_root, Tool.claude)


def test_backup_deployed_files_rejects_symlink_inside_destination_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    deployed_agents = project_root / ".claude" / "agents"
    deployed_agents.mkdir(parents=True)
    secret_file = tmp_path / "outside-secret.md"
    secret_file.write_text("token = should-not-be-backed-up")
    (deployed_agents / "leaked.agent.md").symlink_to(secret_file)

    with pytest.raises(UnsafeDestinationError, match="refuses to back up through symlink"):
        backup_deployed_files(project_root, Tool.claude)


def test_latest_backup_for_tool_ignores_other_tool_backups(tmp_path: Path) -> None:
    _seed_deployment(tmp_path, Tool.claude)
    claude_backup = backup_deployed_files(tmp_path, Tool.claude)
    assert claude_backup is not None

    _seed_deployment(tmp_path, Tool.copilot)
    copilot_backup = backup_deployed_files(tmp_path, Tool.copilot)
    assert copilot_backup is not None

    assert latest_backup_for_tool(tmp_path, Tool.claude) == claude_backup
    assert latest_backup_for_tool(tmp_path, Tool.copilot) == copilot_backup


def test_latest_backup_for_tool_uses_version_file_for_legacy_backups(tmp_path: Path) -> None:
    backup_dir = tmp_path / BACKUP_DIR
    legacy_backup = backup_dir / "20260520-120000-000001"
    legacy_backup.mkdir(parents=True)
    (legacy_backup / ".playbook-version").write_text("tool: claude\n")

    assert latest_backup_for_tool(tmp_path, Tool.claude) == legacy_backup


def test_backup_deployed_files_handles_timestamp_collision(tmp_path: Path) -> None:
    """When microsecond timestamps collide, a numeric suffix disambiguates."""
    _seed_deployment(tmp_path, Tool.claude)

    fixed_timestamp = "20260520-120000-000001"
    backup_dir = tmp_path / BACKUP_DIR
    backup_dir.mkdir()
    # Pre-create the dir we expect the backup code to want.
    (backup_dir / fixed_timestamp).mkdir()

    with patch("deploy_ai_playbook.backup.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = fixed_timestamp
        # Need UTC import to remain valid.
        from datetime import UTC

        mock_dt.UTC = UTC

        result = backup_deployed_files(tmp_path, Tool.claude)

    assert result is not None
    assert result.name == f"{fixed_timestamp}-1", f"expected suffix -1, got {result.name}"
    assert result.exists()


def test_backup_deployed_files_increments_suffix_on_repeated_collision(tmp_path: Path) -> None:
    _seed_deployment(tmp_path, Tool.claude)

    fixed_timestamp = "20260520-120000-000002"
    backup_dir = tmp_path / BACKUP_DIR
    backup_dir.mkdir()
    (backup_dir / fixed_timestamp).mkdir()
    (backup_dir / f"{fixed_timestamp}-1").mkdir()

    with patch("deploy_ai_playbook.backup.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = fixed_timestamp
        from datetime import UTC

        mock_dt.UTC = UTC

        result = backup_deployed_files(tmp_path, Tool.claude)

    assert result is not None
    assert result.name == f"{fixed_timestamp}-2"


def test_restore_backup_cleans_staging_on_stage_failure(tmp_path: Path) -> None:
    """If staging raises, the temp dir must be removed and the error re-raised."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    backup_root = tmp_path / "broken-backup"
    backup_root.mkdir()
    (backup_root / "agents").mkdir()
    (backup_root / "agents" / "alpha.agent.md").write_text("# alpha")

    with (
        patch("deploy_ai_playbook.backup._stage_backup", side_effect=RuntimeError("boom")),
        pytest.raises(RuntimeError, match="boom"),
    ):
        restore_backup(project_root, Tool.claude, backup_root)

    # No leftover playbook-restore-* dirs in project_root.
    leftovers = [p for p in project_root.iterdir() if p.name.startswith("playbook-restore-")]
    assert leftovers == [], f"staging dir leaked: {leftovers}"


def test_restore_backup_rejects_symlinked_destination_dir(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside-claude"
    outside.mkdir()
    (project_root / ".claude").symlink_to(outside, target_is_directory=True)

    backup_root = tmp_path / "backup"
    backup_agents = backup_root / "agents"
    backup_agents.mkdir(parents=True)
    (backup_agents / "restored.agent.md").write_text("# restored agents")

    with pytest.raises(UnsafeDestinationError, match="refuses to write through symlink"):
        restore_backup(project_root, Tool.claude, backup_root)

    leftovers = [
        path for path in project_root.iterdir() if path.name.startswith("playbook-restore-")
    ]
    assert leftovers == []


def test_restore_backup_preserves_current_deployment_on_swap_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A mid-swap rollback failure must leave the current deployment intact."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    destinations = TOOL_DESTINATIONS[Tool.claude]

    current_agents = project_root / destinations["agents"]
    current_agents.mkdir(parents=True)
    (current_agents / "current.agent.md").write_text("# current agents")
    current_kb = project_root / destinations["knowledge-base"]
    current_kb.mkdir(parents=True)
    (current_kb / "current.md").write_text("# current kb")

    backup_root = tmp_path / "backup"
    backup_agents = backup_root / "agents"
    backup_agents.mkdir(parents=True)
    (backup_agents / "restored.agent.md").write_text("# restored agents")
    backup_kb = backup_root / "knowledge-base"
    backup_kb.mkdir(parents=True)
    (backup_kb / "restored.md").write_text("# restored kb")

    original_rename = Path.rename

    def fail_on_knowledge_base_rename(self: Path, target: str | Path) -> Path:
        target_path = Path(target)
        if target_path == project_root / destinations["knowledge-base"]:
            raise OSError("simulated rename failure")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", fail_on_knowledge_base_rename)

    with pytest.raises(OSError, match="simulated rename failure"):
        restore_backup(project_root, Tool.claude, backup_root)

    assert (current_agents / "current.agent.md").read_text() == "# current agents"
    assert not (current_agents / "restored.agent.md").exists()
    assert (current_kb / "current.md").read_text() == "# current kb"
    assert not (current_kb / "restored.md").exists()
    leftovers = [
        path for path in project_root.iterdir() if path.name.startswith("playbook-restore-")
    ]
    assert leftovers == [], f"staging dir leaked: {leftovers}"


def test_restore_backup_preserves_current_file_target_on_swap_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    destinations = TOOL_DESTINATIONS[Tool.claude]

    current_agents = project_root / destinations["agents"]
    current_agents.mkdir(parents=True)
    (current_agents / "current.agent.md").write_text("# current agents")
    rules_dst = project_root / destinations["rules"]
    rules_dst.write_text("# current rules")

    backup_root = tmp_path / "backup"
    backup_agents = backup_root / "agents"
    backup_agents.mkdir(parents=True)
    (backup_agents / "restored.agent.md").write_text("# restored agents")
    (backup_root / rules_dst.name).write_text("# restored rules")

    original_copy2 = shutil.copy2

    def fail_on_rules_copy(src: str | Path, dst: str | Path, *args: object, **kwargs: object):
        if Path(dst) == rules_dst and Path(src).read_text() == "# restored rules":
            raise OSError("simulated file copy failure")
        return original_copy2(src, dst, *args, **kwargs)

    monkeypatch.setattr(shutil, "copy2", fail_on_rules_copy)

    with pytest.raises(OSError, match="simulated file copy failure"):
        restore_backup(project_root, Tool.claude, backup_root)

    assert (current_agents / "current.agent.md").read_text() == "# current agents"
    assert not (current_agents / "restored.agent.md").exists()
    assert rules_dst.read_text() == "# current rules"


def test_restore_backup_round_trip(tmp_path: Path) -> None:
    """End-to-end: backup, wipe, restore — deployment ends up identical."""
    project_root = tmp_path / "project"
    project_root.mkdir()
    _seed_deployment(project_root, Tool.claude)

    destinations = TOOL_DESTINATIONS[Tool.claude]
    agents_dst = project_root / destinations["agents"]
    rules_dst = project_root / destinations["rules"]
    assert agents_dst.exists()
    assert rules_dst.exists()

    backup_root = backup_deployed_files(project_root, Tool.claude)
    assert backup_root is not None

    # Wipe deployment.
    shutil.rmtree(agents_dst)
    rules_dst.unlink()
    assert not agents_dst.exists()

    restore_backup(project_root, Tool.claude, backup_root)

    assert agents_dst.exists()
    assert (agents_dst / "placeholder.md").read_text() == "# agents"
    assert rules_dst.exists()
    assert rules_dst.read_text() == "rules content"
