"""Acceptance tests for adopter-side pack support — driven through the CLI boundary.

Pack ATs layer a tmp pack on top of the real playbook core. The core is the
substrate; the pack is what's under test. This mirrors the pattern used by
`tests/acceptance/test_deploy.py` (real source root, tmp project root).

Tests that need to mutate the source mid-test (e.g. the core-upgrade flow)
monkeypatch `get_source_root()` to a synthetic fake core, following the
pattern in `tests/acceptance/test_doctor.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from deploy_ai_playbook.cli import app, get_source_root

runner = CliRunner()


def _write_pack_config(project_root: Path, packs: list[str]) -> None:
    """Helper — write `.ai-playbook.toml` with a packs list."""
    quoted = ", ".join(f'"{p}"' for p in packs)
    (project_root / ".ai-playbook.toml").write_text(f"packs = [{quoted}]\n")


def _make_pack(project_root: Path, name: str) -> Path:
    """Helper — create an empty pack directory under .ai-playbook/packs/<name>."""
    pack_root = project_root / ".ai-playbook" / "packs" / name
    pack_root.mkdir(parents=True)
    return pack_root


def _write_pack_metadata(
    pack_root: Path,
    name: str,
    version: str,
    min_playbook_version: str = "1.0.0",
) -> None:
    pack_root.joinpath("pack.toml").write_text(
        f'name = "{name}"\nversion = "{version}"\nmin_playbook_version = "{min_playbook_version}"\n'
    )


def _read_version_fingerprint(project_root: Path) -> str:
    """Read the deployed playbook fingerprint from `.playbook-version`."""
    for line in (project_root / ".playbook-version").read_text().splitlines():
        if line.startswith("playbook-fingerprint:"):
            return line.split(":", 1)[1].strip()
    raise AssertionError("missing playbook-fingerprint line")


def test_ac1_deploy_layers_pack_files_over_core(tmp_path: Path) -> None:
    """AC 1: With a pack listed in `.ai-playbook.toml`, deploy outputs core + pack files."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text(
        "# Django Model Reviewer\n\nProject-specific agent for the Django pack.\n"
    )
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, f"deploy failed:\n{result.output}"
    agents_dir = tmp_path / ".claude" / "agents"
    # Pack file deployed:
    assert (agents_dir / "django-model-reviewer.agent.md").exists()
    # Core files still deployed (sanity — pack didn't replace core):
    assert (agents_dir / "story-refiner.agent.md").exists()
    assert (agents_dir / "xp-pair-programmer.agent.md").exists()


def test_deploy_reports_pack_metadata_and_records_versions(tmp_path: Path) -> None:
    pack_root = _make_pack(tmp_path, "django")
    _write_pack_metadata(pack_root, name="django", version="1.2.3")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text(
        "# Django Model Reviewer\n"
    )
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "Pack metadata" in result.output
    assert "django 1.2.3" in result.output
    version_file = (tmp_path / ".playbook-version").read_text()
    assert "pack: django@1.2.3" in version_file


def test_deploy_stops_when_pack_requires_newer_playbook(tmp_path: Path) -> None:
    pack_root = _make_pack(tmp_path, "future")
    _write_pack_metadata(pack_root, name="future", version="1.0.0", min_playbook_version="999.0.0")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "future.agent.md").write_text("# Future\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/future"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 1
    # Rich wraps long lines to terminal width; collapse whitespace to keep the
    # assertion stable regardless of `COLUMNS` in the test environment.
    flattened = " ".join(result.output.split())
    assert "requires ai-playbook >= 999.0.0" in flattened
    assert not (tmp_path / ".claude").exists()


def test_ac2_deploy_warns_when_pack_overrides_core(tmp_path: Path) -> None:
    """AC 2: When a pack file overrides a core file, deploy warns AND uses pack content."""
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    pack_override = pack_root / "agents" / "story-refiner.agent.md"
    override_marker = "# OVERRIDDEN by pack:internal — testing\n"
    pack_override.write_text(override_marker)
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, f"deploy failed:\n{result.output}"

    # Warning identifies the override (path + pack name):
    assert "override" in result.output.lower()
    assert "agents/story-refiner.agent.md" in result.output
    assert "pack:internal" in result.output

    # Deployed file content matches the pack's version, not core's:
    deployed = (tmp_path / ".claude" / "agents" / "story-refiner.agent.md").read_text()
    assert override_marker in deployed


def test_pack_agent_gets_generated_command_shim(tmp_path: Path) -> None:
    """Pack agents have no core `commands/` shim — deploy generates a standard
    one so pack agents are slash-invocable like core agents."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# Django Reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "generated" in result.output, "deploy output should mark the shim as generated"
    shim = tmp_path / ".claude" / "commands" / "django-model-reviewer.md"
    assert shim.exists(), "pack agent should get a generated slash-command shim"
    content = shim.read_text()
    assert "django-model-reviewer" in content
    assert "$ARGUMENTS" in content


def test_pack_agent_shim_generation_respects_dry_run(tmp_path: Path) -> None:
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# Django Reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "--dry-run", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    assert "would generate" in result.output
    assert not (tmp_path / ".claude").exists()


def test_pack_agent_generated_shim_transforms_for_copilot(tmp_path: Path) -> None:
    """Generated shims go through the same tool transform as core shims."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# Django Reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "copilot", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    shim = tmp_path / ".github" / "prompts" / "django-model-reviewer.prompt.md"
    assert shim.exists()
    content = shim.read_text()
    assert "${input:arguments}" in content
    assert "$ARGUMENTS" not in content


def test_generated_pack_shim_survives_prune(tmp_path: Path) -> None:
    """Prune must treat generated shims as expected files, not orphans."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# Django Reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])
    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert first.exit_code == 0, first.output

    result = runner.invoke(
        app,
        ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--prune", "--yes"],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".claude" / "commands" / "django-model-reviewer.md").exists()


def test_core_agents_keep_authored_shims_not_generated(tmp_path: Path) -> None:
    """Core agents have authored shims — generation must never replace them."""
    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, result.output
    shim = (tmp_path / ".claude" / "commands" / "story-refiner.md").read_text()
    source = (get_source_root() / "commands" / "story-refiner.md").read_text()
    assert shim == source


def test_path_rewrite_applied_to_pack_files_too(tmp_path: Path) -> None:
    """Pack KB files referencing `knowledge-base/` get the same path rewrite as core files.

    Tool-specific deploy paths (e.g. `.claude/knowledge-base/`) must apply to pack
    content too, otherwise pack docs would carry broken relative refs.
    """
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "knowledge-base").mkdir()
    (pack_root / "knowledge-base" / "django-patterns.md").write_text(
        "See knowledge-base/style-guide.md for naming.\n"
    )
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, f"deploy failed:\n{result.output}"
    deployed = (tmp_path / ".claude" / "knowledge-base" / "django-patterns.md").read_text()
    # Path rewrite happened (raw `knowledge-base/` → `.claude/knowledge-base/`):
    assert ".claude/knowledge-base/style-guide.md" in deployed


def test_deploy_handles_no_packs_no_toml_unchanged(tmp_path: Path) -> None:
    """Regression: existing core-only flow still works when no `.ai-playbook.toml` exists."""
    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0, f"deploy failed:\n{result.output}"
    # No override warning (no packs configured):
    assert "Pack overrides" not in result.output
    # Core files deployed normally:
    assert (tmp_path / ".claude" / "agents" / "story-refiner.agent.md").exists()


def test_ac3_doctor_recognizes_pack_files_as_expected(tmp_path: Path) -> None:
    """AC 3: After deploying a pack, doctor reports clean — pack files are NOT orphans/stale."""
    # Setup: pack with one new agent file
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    # Contract-valid frontmatter: doctor now names files that
    # break the agent contract, and this test asserts the filename is absent.
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text(
        """---
name: Django Model Reviewer
description: Pack test fixture agent
argument-hint: Describe the change
model: executor
id: django-model-reviewer
load_when: pack fixture
inputs: a request
outputs: guidance
handoff: diff-reviewer
escalation: humans
verified: 2026-06-12
---

# Django Model Reviewer
"""
    )
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    deploy_result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert deploy_result.exit_code == 0, f"deploy failed:\n{deploy_result.output}"

    # Doctor should see the pack file as expected, not orphaned, not stale
    doctor_result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])
    assert doctor_result.exit_code == 0, f"doctor failed:\n{doctor_result.output}"
    # AC 3 contract: the pack file is NOT flagged as orphaned in doctor output.
    output = doctor_result.output
    assert "django-model-reviewer.agent.md" not in output, (
        "AC 3 violated — pack file appears in doctor output as orphan/stale:\n" + output
    )
    assert "orphaned" not in output.lower(), (
        "AC 3 violated — orphan warning appeared with pack:\n" + output
    )


def test_doctor_staleness_uses_pack_source_for_overrides(tmp_path: Path) -> None:
    """When a pack overrides a core file, doctor compares deployed against pack source.

    Setup: pack overrides story-refiner; deploy; modify the deployed copy.
    Doctor must flag it as stale (deviates from pack source), NOT silently
    consider it fresh because the deployed copy happens to differ from core.
    """
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    pack_override = pack_root / "agents" / "story-refiner.agent.md"
    pack_override.write_text("# pack version of story-refiner\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    deploy_result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert deploy_result.exit_code == 0

    # Hand-edit the deployed copy to simulate drift from pack source:
    deployed = tmp_path / ".claude" / "agents" / "story-refiner.agent.md"
    deployed.write_text("# manually edited — drift from pack\n")

    doctor_result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])

    # Doctor must flag story-refiner as stale (against pack source):
    assert "story-refiner" in doctor_result.output
    assert "stale" in doctor_result.output.lower()


def test_doctor_detects_pack_knowledge_base_source_drift(tmp_path: Path) -> None:
    """Pack KB edits after deploy must be reported as stale deployment drift."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "knowledge-base").mkdir()
    pack_kb = pack_root / "knowledge-base" / "django-patterns.md"
    pack_kb.write_text("# Django patterns v1\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    deploy_result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert deploy_result.exit_code == 0, deploy_result.output

    pack_kb.write_text("# Django patterns v2\n")
    doctor_result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])

    assert doctor_result.exit_code == 0, doctor_result.output
    assert "knowledge-base" in doctor_result.output
    assert "stale/missing" in doctor_result.output


def test_diff_detects_pack_knowledge_base_source_drift(tmp_path: Path) -> None:
    """`diff` must compare deployed pack files against their pack source."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "knowledge-base").mkdir()
    pack_kb = pack_root / "knowledge-base" / "django-patterns.md"
    pack_kb.write_text("# Django patterns v1\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    deploy_result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert deploy_result.exit_code == 0, deploy_result.output

    pack_kb.write_text("# Django patterns v2\n")
    diff_result = runner.invoke(app, ["diff", "--tool", "claude", "-t", str(tmp_path)])

    assert diff_result.exit_code == 0, diff_result.output
    assert "django-patterns.md" in diff_result.output
    assert "changed" in diff_result.output


def test_deployed_version_fingerprint_includes_pack_content(tmp_path: Path) -> None:
    """A redeploy after a pack edit must write a different source fingerprint."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "knowledge-base").mkdir()
    pack_kb = pack_root / "knowledge-base" / "django-patterns.md"
    pack_kb.write_text("# Django patterns v1\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert first.exit_code == 0, first.output
    first_fingerprint = _read_version_fingerprint(tmp_path)

    pack_kb.write_text("# Django patterns v2\n")
    second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert second.exit_code == 0, second.output
    second_fingerprint = _read_version_fingerprint(tmp_path)

    assert first_fingerprint != second_fingerprint


def test_doctor_reports_pack_override_in_summary(tmp_path: Path) -> None:
    """Doctor surfaces pack overrides in its health report — operational visibility.

    Without this, a pack silently masking a core update would never be flagged
    in routine health checks.
    """
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "story-refiner.agent.md").write_text("# pack override\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    runner.invoke(app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)])
    doctor_result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])

    # Override visible in doctor output:
    output = doctor_result.output.lower()
    assert "override" in output, f"doctor must surface overrides:\n{doctor_result.output}"
    assert "pack:internal" in output, (
        f"doctor must name the overriding pack:\n{doctor_result.output}"
    )


def test_ac4_prune_preserves_pack_files(tmp_path: Path) -> None:
    """AC 4: After deploying a pack, deploy --prune does NOT remove pack-deployed files."""
    pack_root = _make_pack(tmp_path, "django")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# pack agent\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/django"])

    # First deploy — installs pack file alongside core.
    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert first.exit_code == 0
    deployed_pack_file = tmp_path / ".claude" / "agents" / "django-model-reviewer.agent.md"
    assert deployed_pack_file.exists()

    # Re-deploy with --prune --yes — pack file MUST survive (not flagged as orphan).
    second = runner.invoke(
        app,
        ["deploy", "--agent", "all", "--tool", "claude", "--prune", "--yes", "-t", str(tmp_path)],
    )
    assert second.exit_code == 0, f"prune deploy failed:\n{second.output}"
    assert deployed_pack_file.exists(), (
        f"AC 4 violated — pack file pruned as orphan:\n{second.output}"
    )


def test_ac5_core_upgrade_propagates_to_non_overridden_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC 5: After a core upgrade, non-overridden core files refresh; pack overrides hold.

    Simulates the Project A / Project B story:
      1. Adopter has v1 core deployed with one pack-overridden agent.
      2. Core upgrades — the overridden agent AND a non-overridden agent change.
      3. Adopter runs `ai-playbook deploy` again.
      4. Expected: overridden agent still has pack content; non-overridden agent has v2.
    """
    import deploy_ai_playbook.cli as cli_module

    # Build synthetic v1 core under fake_source/.
    fake_source = tmp_path / "fake_source"
    (fake_source / "agents").mkdir(parents=True)
    overridden_core_v1 = fake_source / "agents" / "overridden.agent.md"
    overridden_core_v1.write_text("# core overridden v1\n")
    untouched_core_v1 = fake_source / "agents" / "untouched.agent.md"
    untouched_core_v1.write_text("# core untouched v1\n")

    # Build the adopter project with one pack overriding 'overridden.agent.md'.
    project_root = tmp_path / "adopter"
    project_root.mkdir()
    pack_root = project_root / ".ai-playbook" / "packs" / "internal"
    (pack_root / "agents").mkdir(parents=True)
    pack_override = pack_root / "agents" / "overridden.agent.md"
    pack_override.write_text("# PACK override (sticky)\n")
    (project_root / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/internal"]\n')

    monkeypatch.setattr(cli_module, "get_source_root", lambda: fake_source)

    # First deploy — v1 core + pack.
    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(project_root)]
    )
    assert first.exit_code == 0, f"first deploy failed:\n{first.output}"
    deployed_overridden = project_root / ".claude" / "agents" / "overridden.agent.md"
    deployed_untouched = project_root / ".claude" / "agents" / "untouched.agent.md"
    assert "PACK override" in deployed_overridden.read_text()
    assert "untouched v1" in deployed_untouched.read_text()

    # Simulate core upgrade: both files change in core.
    overridden_core_v1.write_text("# core overridden v2 (newer than pack)\n")
    untouched_core_v1.write_text("# core untouched v2\n")

    # Second deploy.
    second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(project_root)]
    )
    assert second.exit_code == 0, f"second deploy failed:\n{second.output}"

    # Pack override still wins — adopter's customisation survives core upgrade:
    assert "PACK override" in deployed_overridden.read_text(), (
        "AC 5 violated — pack override lost on core upgrade"
    )
    # Non-overridden core file refreshes to v2:
    assert "untouched v2" in deployed_untouched.read_text(), (
        "AC 5 violated — non-overridden core file did not refresh"
    )


def test_two_packs_with_cross_pack_override_resolves_by_list_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integration: two packs both modify the same file — last-in-list wins.

    Documents and protects the cross-pack precedence rule end-to-end through
    the CLI boundary (the unit test in test_discovery covers the discovery
    layer alone).
    """
    import deploy_ai_playbook.cli as cli_module

    fake_source = tmp_path / "fake_source"
    (fake_source / "agents").mkdir(parents=True)
    (fake_source / "agents" / "shared.agent.md").write_text("# core shared\n")

    project_root = tmp_path / "adopter"
    project_root.mkdir()
    pack_a = project_root / ".ai-playbook" / "packs" / "alpha"
    (pack_a / "agents").mkdir(parents=True)
    (pack_a / "agents" / "shared.agent.md").write_text("# alpha override\n")
    pack_b = project_root / ".ai-playbook" / "packs" / "beta"
    (pack_b / "agents").mkdir(parents=True)
    (pack_b / "agents" / "shared.agent.md").write_text("# beta override (last in list)\n")
    (project_root / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/alpha", ".ai-playbook/packs/beta"]\n'
    )

    monkeypatch.setattr(cli_module, "get_source_root", lambda: fake_source)

    result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(project_root)]
    )
    assert result.exit_code == 0, f"deploy failed:\n{result.output}"

    deployed = (project_root / ".claude" / "agents" / "shared.agent.md").read_text()
    assert "beta override" in deployed, (
        f"last-pack-wins violated — expected beta to win, got:\n{deployed}"
    )


def test_list_includes_pack_only_agents(tmp_path: Path) -> None:
    """Pack-only agents must appear in `ai-playbook list` output, labelled 'pack'."""
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "custom-reviewer.agent.md").write_text("# custom reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    result = runner.invoke(app, ["list", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "custom-reviewer" in result.output
    assert "pack" in result.output
    # Core agents are still listed and labelled correctly:
    assert "story-refiner" in result.output
    assert "core" in result.output


def test_list_shows_pack_origin_for_core_agent_override(tmp_path: Path) -> None:
    """A pack override of a core agent must not be labelled as core in list output."""
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "story-refiner.agent.md").write_text("# internal story refiner\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    result = runner.invoke(app, ["list", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "story-refiner" in result.output
    assert "pack:internal" in result.output


def test_list_without_pack_config_shows_only_core_agents(tmp_path: Path) -> None:
    """Without `.ai-playbook.toml`, list must show core agents only."""
    result = runner.invoke(app, ["list", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "story-refiner" in result.output
    # No pack label when there are no packs:
    assert "pack" not in result.output


def test_rollback_after_pack_deploy_leaves_pack_config_intact(tmp_path: Path) -> None:
    """Rollback restores deployed overlay files; `.ai-playbook.toml` and pack source are untouched.

    After rollback the deployment may pre-date the pack being added, leaving the pack
    agent absent from disk while `.ai-playbook.toml` still declares it. Doctor must flag
    the missing agent as an issue — confirming the redeploy discipline documented in
    cli-reference.md § Rollback.
    """
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    pack_agent = pack_root / "agents" / "custom-reviewer.agent.md"
    pack_agent.write_text("# custom reviewer\n")

    # First deploy — core only (no pack config yet); creates a backup of the empty state.
    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert first.exit_code == 0, first.output

    # Second deploy — now with the pack; backup created = core-only state from first deploy.
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])
    second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert second.exit_code == 0, second.output
    deployed_pack_agent = tmp_path / ".claude" / "agents" / "custom-reviewer.agent.md"
    assert deployed_pack_agent.exists(), "pack agent should be present after second deploy"

    # Rollback — restores the core-only snapshot saved before the second deploy.
    rollback_result = runner.invoke(
        app, ["rollback", "--tool", "claude", "-t", str(tmp_path), "--force"]
    )
    assert rollback_result.exit_code == 0, rollback_result.output
    assert "Rollback complete" in rollback_result.output

    # Pack agent is gone from the deployment (restored to pre-pack snapshot):
    assert not deployed_pack_agent.exists(), (
        "pack agent should be absent after rollback to pre-pack snapshot"
    )

    # `.ai-playbook.toml` and pack source are untouched:
    assert (tmp_path / ".ai-playbook.toml").exists()
    assert pack_agent.exists()

    # Doctor flags the missing pack agent as an issue — the mismatch is visible.
    doctor_result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])
    assert "custom-reviewer" in doctor_result.output, (
        "doctor must flag missing pack agent after rollback to pre-pack snapshot:\n"
        + doctor_result.output
    )
    assert "not deployed" in doctor_result.output.lower(), (
        "doctor must report the pack agent as not deployed:\n" + doctor_result.output
    )


def test_disable_enable_pack_only_agent(tmp_path: Path) -> None:
    """Pack-only agents must participate in the same enable/disable flow as core agents."""
    pack_root = _make_pack(tmp_path, "internal")
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "custom-reviewer.agent.md").write_text("# custom reviewer\n")
    _write_pack_config(tmp_path, [".ai-playbook/packs/internal"])

    deploy_result = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert deploy_result.exit_code == 0, deploy_result.output

    disable_result = runner.invoke(
        app, ["disable", "custom-reviewer", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert disable_result.exit_code == 0, disable_result.output
    assert (tmp_path / ".claude" / "agents" / "custom-reviewer.agent.md.disabled").exists()

    enable_result = runner.invoke(
        app, ["enable", "custom-reviewer", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert enable_result.exit_code == 0, enable_result.output
    assert (tmp_path / ".claude" / "agents" / "custom-reviewer.agent.md").exists()
