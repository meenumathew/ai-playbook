"""Acceptance tests for `list`, `status`, `artifacts`, `enable`, `disable`."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from deploy_ai_playbook.cli import DISABLED_SUFFIX, app
from tests import ALL_AGENTS

runner = CliRunner()


def test_ac_list_shows_all_shipped_agents():
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    for name in ALL_AGENTS:
        assert name in result.output


def test_ac_list_json_outputs_agent_inventory(tmp_path):
    """`list --json` emits a machine-readable agent inventory."""
    result = runner.invoke(app, ["list", "--json", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    agents = {row["name"]: row for row in payload["agents"]}
    for name in ALL_AGENTS:
        assert name in agents
        assert agents[name]["file"] == f"{name}.agent.md"
        assert agents[name]["origin"] == "core"


def test_ac_list_json_includes_pack_agent_with_origin(tmp_path):
    """Pack agents appear in the JSON inventory with pack origin."""
    pack_root = tmp_path / ".ai-playbook" / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text("# Django Reviewer\n")
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/django"]\n')

    result = runner.invoke(app, ["list", "--json", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    agents = {row["name"]: row for row in payload["agents"]}
    assert agents["django-model-reviewer"]["origin"] == "pack:django"


def test_ac_list_default_table_output_unchanged(tmp_path):
    """without `--json` the table renders as before."""
    result = runner.invoke(app, ["list", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "Available Agents" in result.output
    with pytest.raises(json.JSONDecodeError):
        json.loads(result.output)


def test_ac_status_disable_enable_round_trip(deployed_claude: Path):
    disable_result = runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )
    assert disable_result.exit_code == 0
    assert (
        deployed_claude / ".claude" / "agents" / f"xp-pair-programmer.agent.md{DISABLED_SUFFIX}"
    ).exists()

    status_result = runner.invoke(app, ["status", "--tool", "claude", "-t", str(deployed_claude)])
    assert status_result.exit_code == 0
    assert "disabled" in status_result.output

    enable_result = runner.invoke(
        app,
        ["enable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )
    assert enable_result.exit_code == 0
    assert (deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md").exists()


def test_ac_enable_not_deployed_reports_hint(tmp_path: Path):
    result = runner.invoke(
        app, ["enable", "xp-pair-programmer", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_ac_status_reports_nothing_deployed(tmp_path: Path):
    result = runner.invoke(app, ["status", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "Nothing deployed" in result.output


def test_status_json_reports_not_deployed(tmp_path: Path):
    result = runner.invoke(app, ["status", "--tool", "claude", "-t", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["deployed"] is False
    assert payload["tool"] == "claude"
    assert payload["agents"] == []


def test_ac_status_shows_default_quality_tier(deployed_claude: Path):
    result = runner.invoke(app, ["status", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Quality tier" in result.output
    assert "production" in result.output


def test_ac_status_shows_per_agent_quality_tier_override(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n\n'
        '[quality_tiers.agents]\nxp-pair-programmer = "prototype"\n'
    )

    result = runner.invoke(app, ["status", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "xp-pair-programmer" in result.output
    assert "prototype" in result.output
    assert "override" in result.output


def test_status_json_reports_agent_state_and_quality_tier(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").write_text(
        '[quality_tiers.agents]\nxp-pair-programmer = "prototype"\n'
    )
    runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )

    result = runner.invoke(
        app, ["status", "--tool", "claude", "-t", str(deployed_claude), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    xp_pair = next(agent for agent in payload["agents"] if agent["agent"] == "xp-pair-programmer")
    assert xp_pair["status"] == "disabled"
    assert xp_pair["quality_tier"] == "prototype"
    assert xp_pair["quality_tier_source"] == "override"


def test_ac_artifacts_lists_resume_files_with_status(tmp_path: Path):
    story_dir = tmp_path / "stories"
    plan_dir = tmp_path / "plans"
    story_dir.mkdir()
    plan_dir.mkdir()
    (story_dir / "STORY-001-checkout.md").write_text("status: ready\n# Checkout\n")
    (plan_dir / "PLAN-001-checkout.md").write_text("status: in-progress\n# Checkout Plan\n")

    result = runner.invoke(app, ["artifacts", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "stories/STORY-001-checkout.md" in result.output
    assert "plans/PLAN-001-checkout.md" in result.output
    assert "ready" in result.output
    assert "in-progress" in result.output


def test_artifacts_json_lists_resume_files_with_status(tmp_path: Path):
    story_dir = tmp_path / "stories"
    story_dir.mkdir()
    (story_dir / "STORY-001-checkout.md").write_text("status: ready\n# Checkout\n")

    result = runner.invoke(app, ["artifacts", "-t", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["count"] == 1
    assert payload["artifacts"] == [
        {"path": "stories/STORY-001-checkout.md", "status": "ready", "type": "Story"}
    ]


def test_ac_artifacts_reads_table_status(tmp_path: Path):
    incident_dir = tmp_path / "incidents"
    incident_dir.mkdir()
    (incident_dir / "INC-2026-05-22-checkout.md").write_text(
        "# Incident\n\n| **Status** | Closed |\n"
    )

    result = runner.invoke(app, ["artifacts", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "incidents/INC-2026-05-22-checkout.md" in result.output
    assert "Closed" in result.output


def test_ac_artifacts_filters_by_content(tmp_path: Path):
    story_dir = tmp_path / "stories"
    story_dir.mkdir()
    (story_dir / "STORY-001-checkout.md").write_text("status: ready\nPayment retry\n")
    (story_dir / "STORY-002-profile.md").write_text("status: ready\nProfile update\n")

    result = runner.invoke(app, ["artifacts", "-t", str(tmp_path), "--query", "payment"])

    assert result.exit_code == 0
    assert "stories/STORY-001-checkout.md" in result.output
    assert "STORY-002-profile" not in result.output


def test_ac_artifacts_reports_empty_project(tmp_path: Path):
    result = runner.invoke(app, ["artifacts", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "No artifacts found" in result.output


def test_ac_artifact_policy_local_adds_managed_gitignore_block(tmp_path: Path):
    result = runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path)])

    assert result.exit_code == 0
    gitignore = tmp_path / ".gitignore"
    content = gitignore.read_text()
    assert "# ai-playbook artifacts (managed)" in content
    assert "stories/" in content
    assert "incidents/" in content
    # Hook state (read-budget counters, telemetry usage log + rotated
    # archives) is machine-local and belongs in the managed block too.
    assert ".claude/read-budget/" in content
    assert ".claude/usage*.jsonl*" in content


def test_ac_artifact_policy_local_uses_guarded_gitignore_write(tmp_path: Path, monkeypatch) -> None:
    original_write_text = Path.write_text

    def reject_direct_gitignore_write(self: Path, *args, **kwargs):
        if self.name == ".gitignore":
            raise AssertionError("direct .gitignore write")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", reject_direct_gitignore_write)

    result = runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path)])

    assert result.exit_code == 0, result.output
    assert "stories/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")


def test_ac_artifact_policy_shared_removes_only_managed_block(tmp_path: Path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(
        ".env\n\n# ai-playbook artifacts (managed)\nstories/\nplans/\n# end ai-playbook artifacts\n"
    )

    result = runner.invoke(app, ["artifact-policy", "shared", "-t", str(tmp_path)])

    assert result.exit_code == 0
    content = gitignore.read_text()
    assert ".env" in content
    assert "ai-playbook artifacts" not in content
    assert "stories/" not in content


def test_ac_artifact_policy_shared_warns_about_unmanaged_ignore_lines(tmp_path: Path):
    """`shared` never edits hand-written lines, but silence would be misleading
    when those lines still hide artifacts — it must warn instead."""
    (tmp_path / ".gitignore").write_text(".env\nstories/\nplans/\n")

    result = runner.invoke(app, ["artifact-policy", "shared", "-t", str(tmp_path)])

    assert result.exit_code == 0
    flattened = " ".join(result.output.split())
    assert "outside the managed block" in flattened
    # Hand-written lines stay untouched:
    assert "stories/" in (tmp_path / ".gitignore").read_text()


def test_ac_artifact_policy_dry_run_does_not_write_gitignore(tmp_path: Path):
    result = runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path), "--dry-run"])

    assert result.exit_code == 0
    assert "would update" in result.output
    assert not (tmp_path / ".gitignore").exists()


def test_ac_artifact_policy_status_reports_managed_policy(tmp_path: Path):
    runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path)])

    result = runner.invoke(app, ["artifact-policy", "status", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "Artifact policy: local" in result.output


def test_ac_artifact_policy_status_reports_shared_without_gitignore(tmp_path: Path):
    result = runner.invoke(app, ["artifact-policy", "status", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "Artifact policy: shared" in result.output


def test_ac_artifact_policy_status_reports_custom_policy(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("stories/\n")

    result = runner.invoke(app, ["artifact-policy", "status", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "Artifact policy: custom" in result.output


def test_ac_artifact_policy_shared_is_noop_without_managed_block(tmp_path: Path):
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(".env\n")

    result = runner.invoke(app, ["artifact-policy", "shared", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "already shared" in result.output
    assert gitignore.read_text() == ".env\n"


def test_ac_artifact_policy_local_is_noop_when_managed_block_exists(tmp_path: Path):
    runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path)])

    result = runner.invoke(app, ["artifact-policy", "local", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "already local" in result.output


def test_disable_not_deployed_agent(tmp_path: Path):
    """Disabling an agent that isn't deployed shows 'not deployed'."""
    result = runner.invoke(
        app, ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(tmp_path)]
    )

    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_disable_already_disabled_agent(deployed_claude: Path):
    """Disabling an already disabled agent shows 'already disabled'."""
    runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )
    result = runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )

    assert result.exit_code == 0
    assert "already disabled" in result.output


def test_enable_already_active_agent(deployed_claude: Path):
    """Enabling an agent that's already active shows 'already active'."""
    result = runner.invoke(
        app, ["enable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)]
    )

    assert result.exit_code == 0
    assert "already active" in result.output


def test_telemetry_status_reports_uninstalled(tmp_path: Path):
    result = runner.invoke(app, ["telemetry", "status", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "not configured" in result.output
    assert "no sessions logged yet" in result.output


def test_telemetry_enable_then_disable_round_trip(tmp_path: Path):
    enable_result = runner.invoke(app, ["telemetry", "enable", "-t", str(tmp_path)])
    assert enable_result.exit_code == 0
    assert "configured" in enable_result.output
    assert (tmp_path / ".claude" / "settings.json").exists()

    status_result = runner.invoke(app, ["telemetry", "status", "-t", str(tmp_path)])
    assert status_result.exit_code == 0
    assert "configured" in status_result.output

    disable_result = runner.invoke(app, ["telemetry", "disable", "-t", str(tmp_path)])
    assert disable_result.exit_code == 0
    assert "disabled" in disable_result.output

    follow_up = runner.invoke(app, ["telemetry", "status", "-t", str(tmp_path)])
    assert follow_up.exit_code == 0
    assert "not configured" in follow_up.output


def test_telemetry_enable_warns_when_harness_script_missing(tmp_path: Path):
    result = runner.invoke(app, ["telemetry", "enable", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "harness/telemetry.sh not deployed" in result.output
