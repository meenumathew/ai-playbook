"""Acceptance tests for `ai-playbook disable` / `enable` / rollback `--dry-run`.

Disable and enable were the lightest-tested mutating
commands and lacked `--dry-run`. These tests pin the rename inverse pair,
the idempotent re-run messages, and that every dry-run leaves the
filesystem untouched.
"""

from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app

runner = CliRunner()

AGENT = "xp-pair-programmer"


def _agent_paths(tmp_path: Path) -> tuple[Path, Path]:
    active = tmp_path / ".claude" / "agents" / f"{AGENT}.agent.md"
    return active, active.parent / (active.name + ".disabled")


def _deploy(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--no-mcp"],
    )
    assert result.exit_code == 0


def test_disable_twice_reports_already_disabled_and_keeps_file(tmp_path: Path):
    _deploy(tmp_path)
    active, disabled = _agent_paths(tmp_path)

    first = runner.invoke(app, ["disable", AGENT, "--tool", "claude", "-t", str(tmp_path)])
    assert first.exit_code == 0
    assert disabled.exists() and not active.exists()

    second = runner.invoke(app, ["disable", AGENT, "--tool", "claude", "-t", str(tmp_path)])
    assert second.exit_code == 0
    assert "already disabled" in second.output
    assert disabled.exists() and not active.exists()


def test_enable_without_disable_reports_already_active(tmp_path: Path):
    _deploy(tmp_path)
    active, disabled = _agent_paths(tmp_path)

    result = runner.invoke(app, ["enable", AGENT, "--tool", "claude", "-t", str(tmp_path)])
    assert result.exit_code == 0
    assert "already active" in result.output
    assert active.exists() and not disabled.exists()


def test_disable_dry_run_renames_nothing(tmp_path: Path):
    _deploy(tmp_path)
    active, disabled = _agent_paths(tmp_path)

    result = runner.invoke(
        app, ["disable", AGENT, "--tool", "claude", "-t", str(tmp_path), "--dry-run"]
    )
    assert result.exit_code == 0
    assert "would disable" in result.output
    assert active.exists() and not disabled.exists()


def test_enable_dry_run_renames_nothing(tmp_path: Path):
    _deploy(tmp_path)
    active, disabled = _agent_paths(tmp_path)
    runner.invoke(app, ["disable", AGENT, "--tool", "claude", "-t", str(tmp_path)])
    assert disabled.exists()

    result = runner.invoke(
        app, ["enable", AGENT, "--tool", "claude", "-t", str(tmp_path), "--dry-run"]
    )
    assert result.exit_code == 0
    assert "would enable" in result.output
    assert disabled.exists() and not active.exists()


def test_rollback_dry_run_restores_nothing(tmp_path: Path):
    _deploy(tmp_path)
    _deploy(tmp_path)  # second deploy creates a backup of the first

    active, _disabled = _agent_paths(tmp_path)
    marker = "LOCAL EDIT — must survive a dry-run rollback"
    active.write_text(active.read_text(encoding="utf-8") + f"\n{marker}\n", encoding="utf-8")

    result = runner.invoke(app, ["rollback", "--tool", "claude", "-t", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0
    assert "Will restore from" in result.output
    assert "Dry run — nothing restored" in result.output
    assert marker in active.read_text(encoding="utf-8")
