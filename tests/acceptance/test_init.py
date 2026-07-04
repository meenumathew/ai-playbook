"""Acceptance tests for `ai-playbook init` — driven through the CLI boundary.

`init` replaces the only manual step in onboarding: hand-creating the six
artifact directories and `.ai-playbook.toml`. It must be idempotent and must
never clobber an adopter's existing config.
"""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app
from deploy_ai_playbook.services.artifacts import ARTIFACT_DIRECTORIES

runner = CliRunner()


def test_ac_init_creates_artifact_directories_with_gitkeep(tmp_path: Path):
    result = runner.invoke(app, ["init", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    for directory in ARTIFACT_DIRECTORIES:
        assert (tmp_path / directory).is_dir(), f"missing {directory}/"
        assert (tmp_path / directory / ".gitkeep").exists(), f"missing {directory}/.gitkeep"


def test_ac_init_seeds_config_stub_when_absent(tmp_path: Path):
    result = runner.invoke(app, ["init", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    config = tmp_path / ".ai-playbook.toml"
    assert config.exists()
    assert "packs" in config.read_text()


def test_ac_init_keeps_existing_config_untouched(tmp_path: Path):
    existing = 'packs = [".ai-playbook/packs/django"]\n'
    (tmp_path / ".ai-playbook.toml").write_text(existing)

    result = runner.invoke(app, ["init", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / ".ai-playbook.toml").read_text() == existing
    assert "kept" in result.output


def test_ac_init_is_idempotent(tmp_path: Path):
    first = runner.invoke(app, ["init", "-t", str(tmp_path)])
    assert first.exit_code == 0, first.output

    second = runner.invoke(app, ["init", "-t", str(tmp_path)])

    assert second.exit_code == 0, second.output
    assert "exists" in second.output


def test_ac_init_does_not_overwrite_artifact_files(tmp_path: Path):
    (tmp_path / "stories").mkdir()
    story = tmp_path / "stories" / "STORY-001-existing.md"
    story.write_text("# existing story\n")

    result = runner.invoke(app, ["init", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert story.read_text() == "# existing story\n"
