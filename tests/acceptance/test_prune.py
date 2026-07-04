"""Acceptance tests for `ai-playbook deploy --prune` — driven through the CLI boundary.

The prune flow is the only deploy path that deletes adopter files, so every
branch of its preview → confirm → delete contract gets a CLI-level test:
dry-run previews without deleting, the confirmation prompt blocks deletion,
`--yes` skips the prompt, and dropping a pack from `.ai-playbook.toml`
surfaces the removed-packs warning before its files are deleted.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app

runner = CliRunner()


def _deploy(tmp_path: Path, *extra: str, input: str | None = None):
    return runner.invoke(
        app,
        ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), *extra],
        input=input,
    )


def _orphan(tmp_path: Path) -> Path:
    """Plant a deployed agent file with no corresponding source — a prune target."""
    orphan = tmp_path / ".claude" / "agents" / "removed-agent.agent.md"
    orphan.write_text("# Removed Agent\n")
    return orphan


def test_ac_prune_dry_run_previews_orphan_without_deleting(tmp_path: Path):
    assert _deploy(tmp_path).exit_code == 0
    orphan = _orphan(tmp_path)

    result = _deploy(tmp_path, "--prune", "--dry-run")

    assert result.exit_code == 0, result.output
    assert "would prune" in result.output
    assert "removed-agent.agent.md" in result.output
    assert orphan.exists()


def test_ac_prune_declined_confirmation_keeps_files(tmp_path: Path):
    assert _deploy(tmp_path).exit_code == 0
    orphan = _orphan(tmp_path)

    result = _deploy(tmp_path, "--prune", input="n\n")

    assert result.exit_code == 0, result.output
    assert "Prune aborted" in result.output
    assert orphan.exists()


def test_ac_prune_confirmed_deletes_orphan(tmp_path: Path):
    assert _deploy(tmp_path).exit_code == 0
    orphan = _orphan(tmp_path)

    result = _deploy(tmp_path, "--prune", input="y\n")

    assert result.exit_code == 0, result.output
    assert "pruned" in result.output
    assert not orphan.exists()


def test_ac_prune_yes_skips_confirmation_prompt(tmp_path: Path):
    assert _deploy(tmp_path).exit_code == 0
    orphan = _orphan(tmp_path)

    result = _deploy(tmp_path, "--prune", "--yes")

    assert result.exit_code == 0, result.output
    assert "Delete" not in result.output  # no typer.confirm prompt rendered
    assert not orphan.exists()


def test_ac_prune_with_no_orphans_prints_no_prune_section(tmp_path: Path):
    assert _deploy(tmp_path).exit_code == 0

    result = _deploy(tmp_path, "--prune", "--yes")

    assert result.exit_code == 0, result.output
    assert "Prune" not in result.output


def test_ac_prune_keeps_disabled_agent_files(tmp_path: Path):
    """`*.disabled` files are user-managed state — prune must never touch them."""
    assert _deploy(tmp_path).exit_code == 0
    disable = runner.invoke(app, ["disable", "story-refiner", "-t", str(tmp_path)])
    assert disable.exit_code == 0, disable.output
    disabled = tmp_path / ".claude" / "agents" / "story-refiner.agent.md.disabled"
    assert disabled.exists()

    result = _deploy(tmp_path, "--agent", "xp-pair-programmer", "--prune", "--yes")

    assert result.exit_code == 0, result.output
    assert disabled.exists()


def test_ac_prune_warns_when_pack_removed_from_config(tmp_path: Path):
    """Dropping a pack from `.ai-playbook.toml` explains *why* files became orphans."""
    pack_root = tmp_path / ".ai-playbook" / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    (pack_root / "agents" / "django-reviewer.agent.md").write_text("# Django Reviewer\n")
    pack_root.joinpath("pack.toml").write_text(
        'name = "django"\nversion = "1.0.0"\nmin_playbook_version = "1.0.0"\n'
    )
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/django"]\n')
    assert _deploy(tmp_path).exit_code == 0
    deployed_pack_agent = tmp_path / ".claude" / "agents" / "django-reviewer.agent.md"
    assert deployed_pack_agent.exists()

    (tmp_path / ".ai-playbook.toml").write_text("packs = []\n")
    result = _deploy(tmp_path, "--prune", "--yes")

    assert result.exit_code == 0, result.output
    flattened = " ".join(result.output.split())
    assert "packs no longer in .ai-playbook.toml" in flattened
    assert "django" in flattened
    assert not deployed_pack_agent.exists()
