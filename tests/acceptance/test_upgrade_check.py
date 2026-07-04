"""Acceptance tests for `ai-playbook upgrade-check`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app
from deploy_ai_playbook.paths import VERSION_FILE

runner = CliRunner()


def test_upgrade_check_exits_2_when_never_deployed(tmp_path: Path) -> None:
    result = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 2
    assert "not deployed" in result.output


def test_upgrade_check_exits_0_when_up_to_date(deployed_claude: Path) -> None:
    result = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "up to date" in result.output


def test_upgrade_check_json_keeps_exit_code_contract(deployed_claude: Path) -> None:
    result = runner.invoke(
        app, ["upgrade-check", "--tool", "claude", "-t", str(deployed_claude), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "up_to_date"
    assert payload["tool"] == "claude"
    assert payload["deployed_fingerprint"] == payload["source_fingerprint"]


def test_upgrade_check_exits_1_when_fingerprint_drifts(deployed_claude: Path) -> None:
    version_path = deployed_claude / VERSION_FILE
    lines = version_path.read_text().splitlines()
    rewritten = [
        ("playbook-fingerprint: 000000000000" if line.startswith("playbook-fingerprint:") else line)
        for line in lines
    ]
    version_path.write_text("\n".join(rewritten) + "\n")

    result = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 1
    assert "drift" in result.output
    assert "ai-playbook deploy --tool claude" in result.output


def test_upgrade_check_exits_1_when_tool_mismatches(deployed_claude: Path) -> None:
    result = runner.invoke(app, ["upgrade-check", "--tool", "copilot", "-t", str(deployed_claude)])

    assert result.exit_code == 1
    assert "tool mismatch" in result.output
    assert "--tool claude" in result.output
