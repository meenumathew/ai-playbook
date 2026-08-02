"""Acceptance tests for `ai-playbook diff`."""

import json
from pathlib import Path

import pytest

from tests.acceptance._dsl import deploy, diff, doctor


def test_diff_shows_up_to_date_after_deploy(deployed_claude: Path):
    result = diff(deployed_claude)

    assert result.exit_code == 0
    assert "up to date" in result.output


def test_diff_respects_partial_deployment_scope(tmp_path: Path):
    deploy_result = deploy(tmp_path, agents="story-refiner", harness=False)
    assert deploy_result.exit_code == 0, deploy_result.output

    result = diff(tmp_path, exit_code=True)

    assert result.exit_code == 0, result.output
    assert "slice-planner" not in result.output
    assert "harness/" not in result.output


@pytest.mark.parametrize("tool", ["copilot", "cursor"])
def test_diff_clean_after_deploy_for_rewriting_tools(tmp_path: Path, tool: str):
    """A fresh deploy must diff clean for tools whose deploy rewrites path
    references inside command content (claude's rewrite is an identity map, so
    only copilot/cursor exercise this). Regression: the staleness comparison
    omitted the rewrite and reported commands changed forever."""
    deploy_result = deploy(tmp_path, tool=tool)
    assert deploy_result.exit_code == 0, deploy_result.output

    result = diff(tmp_path, tool=tool, exit_code=True)

    assert "changed" not in result.output
    assert result.exit_code == 0, result.output

    # doctor shares the staleness comparison; it must not report the freshly
    # deployed commands as stale either.
    doctor_result = doctor(tmp_path, tool=tool)
    assert "Commands" not in doctor_result.output, doctor_result.output


def test_diff_detects_modified_agent(deployed_claude: Path):
    agent_file = deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    agent_file.write_text("# modified locally")

    result = diff(deployed_claude)

    assert result.exit_code == 0
    assert "changed" in result.output
    assert "xp-pair-programmer" in result.output


def test_diff_detects_not_deployed(tmp_path: Path):
    result = diff(tmp_path)

    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_diff_command_handles_missing_source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When a source dir (kb/skills/templates) doesn't exist, diff skips it."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test-agent.agent.md").write_text("# test")
    (fake_source / "CLAUDE.md").write_text("# rules")

    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    target.mkdir()
    result = diff(target)

    assert result.exit_code == 0


def test_diff_source_with_no_agents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Diff when source has no agents directory: agents block is skipped."""
    fake_source = tmp_path / "fake_source"
    fake_source.mkdir()
    (fake_source / "CLAUDE.md").write_text("rules")
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    result = diff(tmp_path / "target")

    assert result.exit_code == 0


def test_diff_source_with_no_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Diff when source has no CLAUDE.md: rules block is skipped."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test.agent.md").write_text("# test")
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    result = diff(tmp_path / "target")

    assert result.exit_code == 0


def test_diff_reports_local_kb_modifications(deployed_claude: Path):
    """Diff reports KB files that have been customised locally after deploy."""
    kb_dir = deployed_claude / ".claude" / "knowledge-base"
    target = next(kb_dir.rglob("*.md"))
    target.write_text("# customised locally")

    result = diff(deployed_claude)

    assert result.exit_code == 0
    assert target.name in result.output


def test_diff_reports_modified_command_shim(deployed_claude: Path):
    command = deployed_claude / ".claude" / "commands" / "story-refiner.md"
    command.write_text("# locally modified command\n")

    result = diff(deployed_claude)

    assert result.exit_code == 0
    assert "Commands" in result.output
    assert "story-refiner.md" in result.output
    assert "changed" in result.output


# ---------------------------------------------------------------------------
# `--exit-code` opt-in for CI gating
# ---------------------------------------------------------------------------


def test_diff_exit_code_returns_1_on_drift(deployed_claude: Path):
    """`--exit-code` flips diff into a CI gate: drift -> exit 1."""
    (deployed_claude / ".claude" / "commands" / "story-refiner.md").write_text("# drifted\n")

    result = diff(deployed_claude, exit_code=True)
    assert result.exit_code == 1
    assert "changed" in result.output


def test_diff_exit_code_returns_0_when_in_sync(deployed_claude: Path):
    """`--exit-code` exits 0 when nothing has drifted."""
    result = diff(deployed_claude, exit_code=True)
    assert result.exit_code == 0
    assert "Everything up to date." in result.output


def test_diff_default_exit_unchanged_on_drift(deployed_claude: Path):
    """Default `diff` (no flag) stays exit-0 even on drift: informational only."""
    (deployed_claude / ".claude" / "commands" / "story-refiner.md").write_text("# drifted\n")

    result = diff(deployed_claude)
    assert result.exit_code == 0


def test_diff_json_reports_no_drift_when_clean(deployed_claude: Path):
    """`--json` returns a stable shape with `drift: false` when in sync."""
    result = diff(deployed_claude, as_json=True)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["drift"] is False
    assert payload["tool"] == "claude"
    assert payload["sections"] == []


def test_diff_json_reports_drift_with_change_details(deployed_claude: Path):
    """`--json` lists changed files with plain status strings, not Rich markup."""
    (deployed_claude / "CLAUDE.md").write_text("# drifted\n")

    result = diff(deployed_claude, as_json=True)
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["drift"] is True
    assert payload["sections"], "drift must produce at least one section"
    statuses = [
        change["status"] for section in payload["sections"] for change in section["changes"]
    ]
    assert all("[" not in s and "]" not in s for s in statuses), (
        "JSON status strings must be plain (no Rich markup)"
    )


def test_diff_json_with_exit_code_returns_1_on_drift(deployed_claude: Path):
    """`--json --exit-code` keeps the CI-gate semantics; JSON still emitted."""
    (deployed_claude / "CLAUDE.md").write_text("# drifted\n")

    result = diff(deployed_claude, as_json=True, exit_code=True)
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["drift"] is True
