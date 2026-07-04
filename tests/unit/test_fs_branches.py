"""Branch-coverage tests for fs.py — fingerprint, expected-files, prune.

These exercise edge cases in the unified discovery-driven API: empty trees,
missing subdirs, skipped knowledge-base files, harness inclusion, copilot
command renames, and prune safety. Tests use small in-memory directory
layouts via `discover_layered` rather than touching the real source tree.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.discovery import discover_layered
from deploy_ai_playbook.fs import (
    _expected_command_files,
    compute_source_fingerprint,
    copy_commands_directory,
    expected_deployed_files,
    prune_orphaned_files,
)
from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.safety import UnsafeDestinationError


def _seed_minimal_source_tree(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "agents").mkdir()
    (root / "agents" / "alpha.agent.md").write_text("# alpha")
    (root / "agents" / "beta.agent.md").write_text("# beta")

    (root / "knowledge-base").mkdir()
    (root / "knowledge-base" / "core.md").write_text("core")
    (root / "knowledge-base" / "skip.md").write_text("skip me")

    (root / "skills").mkdir()
    (root / "skills" / "tool").mkdir()
    (root / "skills" / "tool" / "SKILL.md").write_text("# tool")

    (root / "templates").mkdir()
    (root / "templates" / "story-template.md").write_text("# story")

    (root / "commands").mkdir()
    (root / "commands" / "alpha.md").write_text("/alpha")

    (root / "CLAUDE.md").write_text("rules")


def _files(root: Path) -> list:
    return discover_layered(root, packs=[]).files


def test_expected_command_files_returns_none_when_dir_absent(tmp_path: Path) -> None:
    assert _expected_command_files(tmp_path, Tool.claude) is None


def test_expected_command_files_renames_for_copilot(tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "alpha.md").write_text("/alpha")
    (commands / "beta.md").write_text("/beta")

    result = _expected_command_files(tmp_path, Tool.copilot)

    assert result == {Path("alpha.prompt.md"), Path("beta.prompt.md")}


def test_expected_command_files_keeps_md_extension_for_claude(tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "alpha.md").write_text("/alpha")

    result = _expected_command_files(tmp_path, Tool.claude)

    assert result == {Path("alpha.md")}


def test_expected_command_files_returns_none_for_target_without_commands(tmp_path: Path) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "alpha.md").write_text("/alpha")

    assert _expected_command_files(tmp_path, Tool.kiro) is None


def test_copy_commands_directory_returns_empty_for_target_without_commands(
    tmp_path: Path,
) -> None:
    commands = tmp_path / "commands"
    commands.mkdir()
    (commands / "alpha.md").write_text("/alpha")

    results = copy_commands_directory(commands, tmp_path / "out", Tool.kiro, dry_run=False)

    assert results == []
    assert not (tmp_path / "out").exists()


def test_compute_source_fingerprint_changes_with_skip(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path)

    full = compute_source_fingerprint(tmp_path, _files(tmp_path))
    skipped = compute_source_fingerprint(tmp_path, _files(tmp_path), skip_files={"skip.md"})

    assert full != skipped, "skipping a knowledge-base file should change the fingerprint"


def test_compute_source_fingerprint_includes_commands_and_rules(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path)
    baseline = compute_source_fingerprint(tmp_path, _files(tmp_path))

    (tmp_path / "commands" / "alpha.md").write_text("/alpha-changed")
    after_command_change = compute_source_fingerprint(tmp_path, _files(tmp_path))

    assert baseline != after_command_change, "command edits must change the fingerprint"

    (tmp_path / "CLAUDE.md").write_text("rules-changed")
    after_rules_change = compute_source_fingerprint(tmp_path, _files(tmp_path))

    assert after_command_change != after_rules_change, "CLAUDE.md edits must change the fingerprint"


def test_compute_source_fingerprint_includes_harness_files(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path)
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    (harness_dir / "telemetry.sh").write_text("#!/bin/sh\necho before\n")
    baseline = compute_source_fingerprint(tmp_path, _files(tmp_path))

    (harness_dir / "telemetry.sh").write_text("#!/bin/sh\necho after\n")

    assert compute_source_fingerprint(tmp_path, _files(tmp_path)) != baseline


def test_compute_source_fingerprint_handles_empty_overlay_files(tmp_path: Path) -> None:
    """An empty discovered_files list still hashes commands/harness/CLAUDE.md."""
    digest = compute_source_fingerprint(tmp_path, [])
    assert len(digest) == 12


def test_expected_deployed_files_for_claude(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path)

    expected = expected_deployed_files(tmp_path, Tool.claude, _files(tmp_path))

    assert any("agents" in str(dest) for dest in expected)
    assert any("knowledge-base" in str(dest) for dest in expected)
    commands_dest = next(d for d in expected if "commands" in str(d))
    assert Path("alpha.md") in expected[commands_dest]


def test_expected_deployed_files_skips_knowledge_base_files(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path)

    expected = expected_deployed_files(
        tmp_path, Tool.claude, _files(tmp_path), skip_files={"skip.md"}
    )
    kb_dest = next(d for d in expected if "knowledge-base" in str(d))

    assert Path("core.md") in expected[kb_dest]
    assert Path("skip.md") not in expected[kb_dest]


def test_expected_deployed_files_skips_missing_subdir(tmp_path: Path) -> None:
    """Subdirs that don't exist contribute nothing to the expected map."""
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "alpha.agent.md").write_text("# alpha")
    (tmp_path / "commands").mkdir()
    (tmp_path / "commands" / "alpha.md").write_text("/alpha")
    # Intentionally NO knowledge-base, skills, or templates dirs.

    expected = expected_deployed_files(tmp_path, Tool.claude, _files(tmp_path))

    assert all("knowledge-base" not in str(d) for d in expected) or all(
        not files for d, files in expected.items() if "knowledge-base" in str(d)
    )


def test_prune_orphaned_files_skips_missing_deployed_dir(tmp_path: Path) -> None:
    """Prune is a no-op for destinations that don't exist on disk."""
    _seed_minimal_source_tree(tmp_path / "source")

    project_root = tmp_path / "project"
    project_root.mkdir()

    results = prune_orphaned_files(
        project_root,
        tmp_path / "source",
        Tool.claude,
        dry_run=False,
        discovered_files=_files(tmp_path / "source"),
    )

    assert results == []


def test_prune_orphaned_files_removes_orphan(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path / "source")

    project_root = tmp_path / "project"
    deployed_agents = project_root / ".claude" / "agents"
    deployed_agents.mkdir(parents=True)
    (deployed_agents / "alpha.agent.md").write_text("# alpha")
    orphan = deployed_agents / "ghost.agent.md"
    orphan.write_text("# ghost")

    results = prune_orphaned_files(
        project_root,
        tmp_path / "source",
        Tool.claude,
        dry_run=False,
        discovered_files=_files(tmp_path / "source"),
    )

    assert not orphan.exists()
    assert any("ghost.agent.md" in str(p) for p, _ in results)


def test_prune_orphaned_files_rejects_symlinked_destination_dir(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path / "source")

    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside-agents"
    outside.mkdir()
    claude_dir = project_root / ".claude"
    claude_dir.mkdir()
    (claude_dir / "agents").symlink_to(outside, target_is_directory=True)

    with pytest.raises(UnsafeDestinationError, match="refuses to write through symlink"):
        prune_orphaned_files(
            project_root,
            tmp_path / "source",
            Tool.claude,
            dry_run=False,
            discovered_files=_files(tmp_path / "source"),
        )


def test_prune_orphaned_files_dry_run_keeps_orphan(tmp_path: Path) -> None:
    _seed_minimal_source_tree(tmp_path / "source")

    project_root = tmp_path / "project"
    deployed_agents = project_root / ".claude" / "agents"
    deployed_agents.mkdir(parents=True)
    orphan = deployed_agents / "ghost.agent.md"
    orphan.write_text("# ghost")

    results = prune_orphaned_files(
        project_root,
        tmp_path / "source",
        Tool.claude,
        dry_run=True,
        discovered_files=_files(tmp_path / "source"),
    )

    assert orphan.exists()
    assert any("would prune" in status for _, status in results)
