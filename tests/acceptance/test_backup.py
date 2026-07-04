"""Acceptance tests for backup, rollback, and restore behaviour."""

from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import (
    BACKUP_DIR,
    VERSION_FILE,
    Tool,
    app,
    backup_deployed_files,
    restore_backup,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# backup_deployed_files
# ---------------------------------------------------------------------------


def test_backup_and_restore_round_trip(deployed_claude: Path):
    agent_file = deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    original_content = agent_file.read_text()

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)

    assert backup_path is not None
    assert backup_path.exists()

    agent_file.write_text("# corrupted")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert agent_file.read_text() == original_content


def test_restore_backup_overwrites_existing_dirs(deployed_claude: Path):
    """restore_backup removes existing deployed dirs before restoring."""
    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None

    rogue = deployed_claude / ".claude" / "agents" / "rogue.md"
    rogue.write_text("rogue")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert not rogue.exists()


def test_backup_without_rules_file(deployed_claude: Path):
    """backup_deployed_files when rules file doesn't exist."""
    (deployed_claude / "CLAUDE.md").unlink()

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)

    assert backup_path is not None
    assert not (backup_path / "CLAUDE.md").exists()


def test_backup_without_version_file(deployed_claude: Path):
    """backup_deployed_files when version file doesn't exist."""
    version_file = deployed_claude / VERSION_FILE
    if version_file.exists():
        version_file.unlink()

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)

    assert backup_path is not None


# ---------------------------------------------------------------------------
# restore_backup branches
# ---------------------------------------------------------------------------


def test_restore_skips_missing_backup_subdir(deployed_claude: Path):
    """restore_backup skips a key whose backup subdir is missing."""
    import shutil

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    shutil.rmtree(backup_path / "skills")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert (deployed_claude / ".claude" / "agents").exists()


def test_restore_when_deploy_dir_missing(deployed_claude: Path):
    """restore_backup copies without rmtree when the deploy dir doesn't exist."""
    import shutil

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    shutil.rmtree(deployed_claude / ".claude" / "agents")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert (deployed_claude / ".claude" / "agents").exists()


def test_restore_kiro_no_commands(tmp_path: Path):
    """restore_backup with kiro tool — commands not in destinations."""
    result = runner.invoke(app, ["deploy", "--agent", "all", "--tool", "kiro", "-t", str(tmp_path)])
    assert result.exit_code == 0

    backup_path = backup_deployed_files(tmp_path, Tool.kiro)
    assert backup_path is not None

    restore_backup(tmp_path, Tool.kiro, backup_path)

    assert (tmp_path / ".kiro" / "agents").exists()


def test_restore_without_commands_in_backup(deployed_claude: Path):
    """restore_backup when commands dir is absent from backup."""
    import shutil

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    commands_backup = backup_path / "commands"
    if commands_backup.exists():
        shutil.rmtree(commands_backup)

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert (deployed_claude / ".claude" / "agents").exists()


def test_restore_commands_when_deploy_dir_missing(deployed_claude: Path):
    """restore_backup copies commands without rmtree when deploy commands dir doesn't exist."""
    import shutil

    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    deploy_commands = deployed_claude / ".claude" / "commands"
    if deploy_commands.exists():
        shutil.rmtree(deploy_commands)

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert (deployed_claude / ".claude" / "commands").exists()


def test_restore_without_rules_in_backup(deployed_claude: Path):
    """restore_backup when rules file is absent from backup."""
    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    rules_backup = backup_path / "CLAUDE.md"
    if rules_backup.exists():
        rules_backup.unlink()
    rules_file = deployed_claude / "CLAUDE.md"
    rules_file.write_text("# current rules\n")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert rules_file.read_text() == "# current rules\n"


def test_restore_without_version_in_backup(deployed_claude: Path):
    """restore_backup when version file is absent from backup."""
    backup_path = backup_deployed_files(deployed_claude, Tool.claude)
    assert backup_path is not None
    version_backup = backup_path / VERSION_FILE
    if version_backup.exists():
        version_backup.unlink()
    version_file = deployed_claude / VERSION_FILE
    version_file.write_text("current-version\n")

    restore_backup(deployed_claude, Tool.claude, backup_path)

    assert version_file.read_text() == "current-version\n"


# ---------------------------------------------------------------------------
# rollback CLI
# ---------------------------------------------------------------------------


def test_ac_rollback_no_backup_exits_with_error(tmp_path: Path):
    result = runner.invoke(app, ["rollback", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 1
    assert "No backups found" in result.output


def test_rollback_empty_backup_dir_exits_with_error(tmp_path: Path):
    (tmp_path / BACKUP_DIR).mkdir(parents=True)

    result = runner.invoke(app, ["rollback", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 1
    assert "No backups found" in result.output


def test_rollback_no_backup_for_requested_tool_exits_with_error(tmp_path: Path):
    first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert first.exit_code == 0, first.output
    second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert second.exit_code == 0, second.output

    result = runner.invoke(app, ["rollback", "--tool", "copilot", "-t", str(tmp_path)])

    assert result.exit_code == 1
    assert "No copilot backups found" in result.output


def test_rollback_decline_confirmation_restores_nothing(deployed_claude: Path):
    agent_file = deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    original_content = agent_file.read_text()
    deploy = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(deployed_claude)]
    )
    assert deploy.exit_code == 0, deploy.output
    agent_file.write_text("# corrupted")

    result = runner.invoke(
        app,
        ["rollback", "--tool", "claude", "-t", str(deployed_claude)],
        input="n\n",
    )

    assert result.exit_code == 0
    assert "Aborted" in result.output
    assert agent_file.read_text() == "# corrupted"
    assert agent_file.read_text() != original_content


def test_ac_rollback_restores_from_latest_backup(deployed_claude: Path):
    agent_file = deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    original_content = agent_file.read_text()

    runner.invoke(app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(deployed_claude)])

    agent_file.write_text("# corrupted")
    assert agent_file.read_text() == "# corrupted"

    result = runner.invoke(
        app, ["rollback", "--tool", "claude", "-t", str(deployed_claude), "--force"]
    )

    assert result.exit_code == 0
    assert "Rollback complete" in result.output
    assert agent_file.read_text() == original_content


def test_rollback_restores_latest_backup_for_requested_tool_only(tmp_path: Path):
    """Rollback must not restore a newer backup created for another tool."""
    claude_first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert claude_first.exit_code == 0, claude_first.output
    claude_agent = tmp_path / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    original_claude_content = claude_agent.read_text()

    # Creates the latest claude backup.
    claude_second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert claude_second.exit_code == 0, claude_second.output
    claude_agent.write_text("# corrupted claude deployment")

    # Create a newer copilot backup with unmistakably different content.
    copilot_first = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "copilot", "-t", str(tmp_path)]
    )
    assert copilot_first.exit_code == 0, copilot_first.output
    copilot_agent = tmp_path / ".github" / "agents" / "xp-pair-programmer.agent.md"
    copilot_agent.write_text("# copilot-only backup content")
    copilot_second = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "copilot", "-t", str(tmp_path)]
    )
    assert copilot_second.exit_code == 0, copilot_second.output

    result = runner.invoke(app, ["rollback", "--tool", "claude", "-t", str(tmp_path), "--force"])

    assert result.exit_code == 0, result.output
    assert claude_agent.read_text() == original_claude_content
