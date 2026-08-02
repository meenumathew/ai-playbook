"""Acceptance tests for `ai-playbook upgrade-check`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from deploy_ai_playbook.cli import app
from deploy_ai_playbook.paths import VERSION_FILE
from tests import ALL_AGENTS
from tests.acceptance._dsl import deploy, runner


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


def test_partial_deployment_record_reports_exact_scope(tmp_path: Path) -> None:
    deploy_result = deploy(tmp_path, agents="story-refiner", mcp=False, harness=False)
    assert deploy_result.exit_code == 0, deploy_result.output

    record = (tmp_path / VERSION_FILE).read_text()
    assert "scope: partial" in record
    assert "agent: story-refiner" in record
    assert "mcp: false" in record
    assert "harness: false" in record

    result = runner.invoke(
        app, ["upgrade-check", "--tool", "claude", "-t", str(tmp_path), "--json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "partial"
    assert payload["deployment_scope"]["agents"] == ["story-refiner"]
    assert payload["deployment_scope"]["mcp"] is False
    assert payload["deployment_scope"]["harness"] is False


def test_selective_update_reports_drift_when_carried_files_are_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selective deploy merges the previous scope into the record, but only
    rewrites the selected files. When the source moved since the previous
    deploy, the carried-over files are stale: upgrade-check must NOT report
    up to date."""
    fake_source = tmp_path / "fake_source"
    (fake_source / "agents").mkdir(parents=True)
    (fake_source / "agents" / "alpha.agent.md").write_text("# alpha v1\n")
    (fake_source / "agents" / "beta.agent.md").write_text("# beta v1\n")
    project = tmp_path / "adopter"
    project.mkdir()
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)
    monkeypatch.setattr("deploy_ai_playbook.upgrade.get_source_root", lambda: fake_source)

    full = deploy(project, rules=False, mcp=False, harness=False)
    assert full.exit_code == 0, full.output

    # The source moves upstream: beta changes after the full deploy.
    (fake_source / "agents" / "beta.agent.md").write_text("# beta v2\n")

    partial = deploy(project, agents="alpha", rules=False, mcp=False, harness=False)
    assert partial.exit_code == 0, partial.output
    deployed_beta = project / ".claude" / "agents" / "beta.agent.md"
    assert deployed_beta.read_text() == "# beta v1\n", "beta was not rewritten by this deploy"

    check = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(project)])

    assert check.exit_code == 1, (
        f"deployed beta is stale — upgrade-check must report drift, not up to date:\n{check.output}"
    )


def test_selective_update_of_unchanged_source_stays_up_to_date(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When the source has NOT moved, a selective redeploy keeps the truthful
    up-to-date/partial status: the stale-carryover guard must not fire."""
    fake_source = tmp_path / "fake_source"
    (fake_source / "agents").mkdir(parents=True)
    (fake_source / "agents" / "alpha.agent.md").write_text("# alpha v1\n")
    (fake_source / "agents" / "beta.agent.md").write_text("# beta v1\n")
    project = tmp_path / "adopter"
    project.mkdir()
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)
    monkeypatch.setattr("deploy_ai_playbook.upgrade.get_source_root", lambda: fake_source)

    full = deploy(project, rules=False, mcp=False, harness=False)
    assert full.exit_code == 0, full.output

    partial = deploy(project, agents="alpha", rules=False, mcp=False, harness=False)
    assert partial.exit_code == 0, partial.output

    check = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(project)])

    assert check.exit_code == 0, check.output


def test_partial_update_of_full_deployment_preserves_installed_scope(tmp_path: Path) -> None:
    full = deploy(tmp_path)
    assert full.exit_code == 0, full.output

    partial = deploy(tmp_path, agents="story-refiner", rules=False, harness=False, mcp=False)
    assert partial.exit_code == 0, partial.output

    assert (tmp_path / ".claude" / "agents" / "slice-planner.agent.md").exists()
    record = (tmp_path / VERSION_FILE).read_text()
    assert "scope: full" in record
    assert record.count("\nagent:") == len(ALL_AGENTS)
    assert "agent: story-refiner" in record
    assert "rules: true" in record
    assert "harness: true" in record
    assert "mcp: true" in record

    check = runner.invoke(app, ["upgrade-check", "--tool", "claude", "-t", str(tmp_path), "--json"])
    assert check.exit_code == 0, check.output
    assert json.loads(check.output)["status"] == "up_to_date"
