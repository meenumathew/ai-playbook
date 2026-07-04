"""Acceptance tests for `ai-playbook doctor`."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from deploy_ai_playbook.cli import VERSION_FILE, Tool, app, write_version_file
from deploy_ai_playbook.telemetry import deploy_telemetry_hook_config

runner = CliRunner()
RUNTIME_DIRS = ("stories", "plans", "research", "audits", "reviews", "incidents")


def test_ac_doctor_nothing_deployed_exits_with_error(tmp_path: Path):
    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 1
    assert "Nothing deployed" in result.output


def test_doctor_json_reports_not_deployed(tmp_path: Path):
    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path), "--json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["healthy"] is False
    assert payload["status"] == "not_deployed"
    assert payload["tool"] == "claude"


def test_doctor_detects_missing_agent(deployed_claude: Path):
    (deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_doctor_detects_disabled_agent(deployed_claude: Path):
    runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "disabled" in result.output


def test_doctor_detects_stale_agent(deployed_claude: Path):
    agent_file = deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    agent_file.write_text("# outdated content")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "stale" in result.output


def test_doctor_detects_missing_rules_file(deployed_claude: Path):
    (deployed_claude / "CLAUDE.md").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "missing" in result.output


def test_doctor_detects_stale_rules_file(deployed_claude: Path):
    (deployed_claude / "CLAUDE.md").write_text("# old rules")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "stale" in result.output


def test_doctor_detects_missing_version_file(deployed_claude: Path):
    version_file = deployed_claude / VERSION_FILE
    if version_file.exists():
        version_file.unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert VERSION_FILE in result.output


def test_doctor_detects_stale_version_fingerprint(deployed_claude: Path):
    version_file = deployed_claude / VERSION_FILE
    version_file.write_text("playbook-fingerprint: 000000000000\ndeployed-at: old\ntool: claude\n")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "fingerprint mismatch" in result.output


def test_doctor_detects_missing_kb_directory(deployed_claude: Path):
    import shutil

    kb_dir = deployed_claude / ".claude" / "knowledge-base"
    if kb_dir.exists():
        shutil.rmtree(kb_dir)

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_doctor_detects_stale_kb_files(deployed_claude: Path):
    """When a KB file is modified locally, doctor reports stale files."""
    kb_dir = deployed_claude / ".claude" / "knowledge-base"
    for f in kb_dir.rglob("*.md"):
        f.write_text("# stale content")
        break

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "stale" in result.output


def test_ac_doctor_respects_deployed_language_filter(tmp_path: Path):
    """Doctor must not report KB files omitted by deploy --language as missing."""
    deploy_result = runner.invoke(
        app,
        [
            "deploy",
            "--agent",
            "all",
            "--tool",
            "claude",
            "--language",
            "python",
            "--no-mcp",
            "-t",
            str(tmp_path),
        ],
    )
    assert deploy_result.exit_code == 0, deploy_result.output

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "knowledge-base has" not in result.output
    assert "stale/missing" not in result.output


def test_doctor_warns_about_missing_runtime_dirs(deployed_claude: Path):
    """Doctor flags partial-state runtime dirs (some exist, some don't).

    On a brand-new deploy with zero artifact dirs, doctor stays quiet — that's
    the expected first-time state. The warnings exist to catch projects in a
    genuinely partial state (e.g. agents have started writing stories/ but the
    incidents/ dir was deleted manually). Seed two dirs so the heuristic fires.
    """
    (deployed_claude / "stories").mkdir()
    (deployed_claude / "plans").mkdir()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Runtime directory" in result.output
    assert "reviews" in result.output
    assert "incidents" in result.output


def test_doctor_json_reports_health_status(deployed_claude: Path):
    for directory in RUNTIME_DIRS:
        (deployed_claude / directory).mkdir(exist_ok=True)

    result = runner.invoke(
        app, ["doctor", "--tool", "claude", "-t", str(deployed_claude), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["healthy"] is True
    assert payload["status"] == "healthy"
    assert payload["issues"] == []
    assert payload["warnings"] == []


def test_doctor_json_reports_attention_with_plain_warnings(deployed_claude: Path):
    """JSON `attention` status when warnings exist.

    Triggers the partial-state runtime-dirs warning (some dirs exist, some
    don't) — same pattern test_doctor_warns_about_missing_runtime_dirs uses.
    """
    (deployed_claude / "stories").mkdir()
    (deployed_claude / "plans").mkdir()

    result = runner.invoke(
        app, ["doctor", "--tool", "claude", "-t", str(deployed_claude), "--json"]
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["healthy"] is False
    assert payload["status"] == "attention"
    assert any("reviews/" in warning for warning in payload["warnings"])


def test_doctor_warns_when_commit_msg_hook_not_installed(deployed_claude: Path):
    """The teach-back hook runs at the commit-msg stage, which `pre-commit install`
    alone does NOT wire — adopters need `pre-commit install --hook-type commit-msg`.

    Doctor must catch this silent-failure mode: hook config present, git repo
    initialised, but `.git/hooks/commit-msg` missing or not delegating to pre-commit.
    """
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    git_dir = deployed_claude / ".git"
    (git_dir / "hooks").mkdir(parents=True)
    # No commit-msg hook installed — this is the failure mode.

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "commit-msg" in result.output
    assert "pre-commit install --hook-type commit-msg" in result.output
    assert "All healthy" not in result.output


def test_doctor_warns_when_commit_msg_stage_uses_multistage_yaml(deployed_claude: Path):
    """Doctor accepts common inline YAML stage lists, not one exact string shape."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    (deployed_claude / ".git" / "hooks").mkdir(parents=True)
    config = (deployed_claude / ".pre-commit-config.yaml").read_text()
    (deployed_claude / ".pre-commit-config.yaml").write_text(
        config.replace("stages: [commit-msg]", 'stages: [pre-commit, "commit-msg"]')
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "pre-commit install --hook-type commit-msg" in result.output


def test_doctor_silent_when_commit_msg_hook_installed(deployed_claude: Path):
    """If the commit-msg hook is installed and delegates to pre-commit, no warning."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    hooks_dir = deployed_claude / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    # Real pre-commit install --hook-type commit-msg writes a shim that calls
    # `pre-commit` — recreate that shape minimally.
    (hooks_dir / "commit-msg").write_text("#!/usr/bin/env bash\nexec pre-commit hook-impl ...\n")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "pre-commit install --hook-type commit-msg" not in result.output


def test_doctor_silent_outside_git_repo(deployed_claude: Path):
    """No `.git/` directory — no warning (the hook can't fire without git anyway)."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    # Deliberately no .git/ — adopters who don't use git get no commit-msg warning.

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "pre-commit install --hook-type commit-msg" not in result.output


def test_doctor_all_healthy(deployed_claude: Path):
    """Doctor reports all-healthy when runtime dirs exist and deployment is fresh."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "healthy" in result.output


def test_doctor_detects_missing_deployed_kb_file(deployed_claude: Path):
    """Doctor detects when a source KB file is not present in deployment."""
    kb_dir = deployed_claude / ".claude" / "knowledge-base"
    for f in kb_dir.rglob("*.md"):
        f.unlink()
        break

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "stale" in result.output


def test_doctor_source_without_rules(
    deployed_claude: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Doctor when source has no CLAUDE.md — rules check is skipped."""
    import deploy_ai_playbook.cli as cli_module
    from tests import ALL_AGENTS

    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    monkeypatch.setattr(cli_module, "get_source_root", lambda: fake_source)

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0


def test_doctor_empty_version_file(deployed_claude: Path):
    """Doctor warns when version tracking exists but has no fingerprint."""
    (deployed_claude / VERSION_FILE).write_text("")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert VERSION_FILE in result.output
    assert "missing playbook-fingerprint" in result.output
    assert "All healthy" not in result.output


def test_doctor_version_file_without_fingerprint_line(deployed_claude: Path):
    """Doctor warns when version file has lines but no playbook-fingerprint entry."""
    (deployed_claude / VERSION_FILE).write_text("deployed-at: 2024-01-01\ntool: claude\n")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert VERSION_FILE in result.output
    assert "missing playbook-fingerprint" in result.output
    assert "All healthy" not in result.output


def test_doctor_warns_when_tool_flag_disagrees_with_deployed_tool(deployed_claude: Path):
    """`--tool copilot` against a target deployed with `--tool claude` must warn.

    The two tool destinations don't share files, so without this warning doctor
    can report "All healthy" against an empty .github/agents tree while the
    real deployment lives elsewhere — silent overlay corruption.
    """
    # `deployed_claude` already wrote `tool: claude` into .playbook-version. We
    # also need the copilot agents directory to exist so doctor doesn't bail
    # out with "Nothing deployed" — write a minimal stub.
    copilot_agents = deployed_claude / ".github" / "agents"
    copilot_agents.mkdir(parents=True)
    (copilot_agents / "stub.agent.md").write_text("# stub")

    result = runner.invoke(app, ["doctor", "--tool", "copilot", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Tool mismatch" in result.output, (
        f"Expected tool-mismatch warning, got:\n{result.output}"
    )
    # The hint must point at the previously-deployed tool so adopters can recover.
    assert "doctor --tool claude" in result.output


def test_doctor_no_tool_mismatch_when_tool_flag_agrees(deployed_claude: Path):
    """No mismatch warning when --tool matches the recorded tool."""
    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Tool mismatch" not in result.output


def test_doctor_warns_when_model_tier_mapping_missing(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Model tier mapping missing" in result.output
    assert "model_tiers" in result.output


def test_doctor_warns_when_model_tier_mapping_incomplete(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").write_text('[model_tiers]\nadvisor = "claude-opus"\n')

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Model tier mapping incomplete" in result.output
    assert "executor" in result.output


def test_doctor_accepts_single_model_tier_mapping(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-sonnet"\nexecutor = "claude-sonnet"\n'
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Model tier mapping" not in result.output


def test_doctor_warns_when_quality_tier_override_names_unknown_agent(deployed_claude: Path):
    (deployed_claude / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n\n'
        '[quality_tiers.agents]\nretired-agent = "prototype"\n'
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Quality tier override" in result.output
    assert "retired-agent" in result.output


def test_doctor_warns_when_claude_telemetry_stop_hook_missing(deployed_claude: Path):
    (deployed_claude / ".claude" / "settings.json").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Telemetry Stop hook" in result.output
    assert "ai-playbook deploy" in result.output


def test_doctor_issues_without_warnings(deployed_claude: Path):
    """Doctor reports issues block but skips warnings block when there are no warnings."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    (deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "not deployed" in result.output
    assert "Warnings" not in result.output


def test_doctor_warns_about_orphaned_deployed_files(deployed_claude: Path):
    """Doctor must surface orphaned files (no source counterpart) and suggest --prune.

    Regression: previously doctor only checked source-known agents and missed
    files left over from renamed/removed agents, reporting "All healthy" while
    the deployment was actually polluted.
    """
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    orphan = deployed_claude / ".claude" / "agents" / "retired-agent.agent.md"
    orphan.write_text("# left over from a previous version")

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "orphaned" in result.output
    assert "--prune" in result.output
    # Should not falsely claim healthy when an orphan exists.
    assert "All healthy" not in result.output


def test_doctor_does_not_flag_disabled_files_as_orphans(deployed_claude: Path):
    """Doctor must preserve `*.disabled` files (user-managed state)."""
    for d in RUNTIME_DIRS:
        (deployed_claude / d).mkdir(exist_ok=True)
    runner.invoke(
        app,
        ["disable", "xp-pair-programmer", "--tool", "claude", "-t", str(deployed_claude)],
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "orphaned" not in result.output
    # Disabled is reported separately as a warning, not as an orphan.
    assert "disabled" in result.output


def test_doctor_handles_missing_source_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Doctor skips checks for source dirs that don't exist."""
    import deploy_ai_playbook.cli as cli_module

    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "test-agent.agent.md").write_text("# test")
    (fake_source / "CLAUDE.md").write_text("# rules")

    monkeypatch.setattr(cli_module, "get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    deployed_agents = target / ".claude" / "agents"
    deployed_agents.mkdir(parents=True)
    (deployed_agents / "test-agent.agent.md").write_text("# test")
    (target / "CLAUDE.md").write_text("# rules")
    write_version_file(target, fake_source, Tool.claude, dry_run=False)
    for d in RUNTIME_DIRS:
        (target / d).mkdir(exist_ok=True)
    (target / "Makefile").write_text("quality:\n\t@true\n")
    (target / ".pre-commit-config.yaml").write_text("")
    (target / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (target / ".github" / "workflows" / "ci.yml").write_text("")
    (target / ".github" / "workflows" / "security.yml").write_text("")
    (target / "harness").mkdir(exist_ok=True)
    teachback = target / "harness" / "check-teachback.sh"
    teachback.write_text("#!/bin/sh\n")
    teachback.chmod(0o755)
    telemetry = target / "harness" / "telemetry.sh"
    telemetry.write_text("#!/bin/sh\n")
    telemetry.chmod(0o755)
    read_budget = target / "harness" / "read-budget.sh"
    read_budget.write_text("#!/bin/sh\n")
    read_budget.chmod(0o755)
    (target / "harness" / "settings.example.json").write_text("{}\n")
    deploy_telemetry_hook_config(target, Tool.claude, dry_run=False)
    (target / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n'
    )

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(target)])

    assert result.exit_code == 0
    assert "healthy" in result.output


def test_doctor_reports_missing_command_shim(deployed_claude: Path):
    for directory in RUNTIME_DIRS:
        (deployed_claude / directory).mkdir(exist_ok=True)
    (deployed_claude / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-sonnet"\nexecutor = "claude-sonnet"\n'
    )
    command = deployed_claude / ".claude" / "commands" / "story-refiner.md"
    command.unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])

    assert result.exit_code == 0
    assert "Commands" in result.output
    assert "stale/missing" in result.output
    assert "All healthy" not in result.output


# ---------------------------------------------------------------------------
# `--strict` exit-code contract for CI
# ---------------------------------------------------------------------------


def test_doctor_strict_exits_2_when_not_deployed(tmp_path: Path):
    """`--strict` distinguishes not-deployed (2) from issues-found (1)."""
    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path), "--strict"])
    assert result.exit_code == 2
    assert "Nothing deployed" in result.output


def test_doctor_strict_exits_1_when_issues_found(deployed_claude: Path):
    """`--strict` exits 1 when the deployment has issues or warnings."""
    (deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md").unlink()

    result = runner.invoke(
        app, ["doctor", "--tool", "claude", "-t", str(deployed_claude), "--strict"]
    )
    assert result.exit_code == 1
    assert "not deployed" in result.output


def test_doctor_strict_exits_0_when_healthy(deployed_claude: Path):
    """`--strict` exits 0 when the deployment is healthy and no warnings fire."""
    for d in ("stories", "plans", "research", "audits", "reviews", "incidents"):
        (deployed_claude / d).mkdir(exist_ok=True)
    # No git dir → silences the commit-msg-hook warning.
    result = runner.invoke(
        app, ["doctor", "--tool", "claude", "-t", str(deployed_claude), "--strict"]
    )
    assert result.exit_code == 0
    assert "healthy" in result.output


def test_doctor_default_exit_unchanged_for_issues(deployed_claude: Path):
    """Default doctor behaviour (no --strict) preserves the legacy 0-on-issues contract.

    Adopters relying on the historical contract — issues print but exit 0 — must
    not be broken when they upgrade. Only `--strict` opts into 0/1/2.
    """
    (deployed_claude / ".claude" / "agents" / "xp-pair-programmer.agent.md").unlink()

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])
    assert result.exit_code == 0
    assert "not deployed" in result.output


def test_doctor_warns_when_harness_script_loses_executable_bit(deployed_claude: Path):
    """Section-5 production-readiness fix: silent telemetry break when wheel
    re-extraction or `cp -r` strips +x from `*.sh`. Doctor must catch it."""
    telemetry = deployed_claude / "harness" / "telemetry.sh"
    assert telemetry.exists(), "fixture deploys harness/telemetry.sh"
    telemetry.chmod(0o644)  # strip the executable bit

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(deployed_claude)])
    assert result.exit_code == 0
    assert "is not executable" in result.output
    assert "harness/telemetry.sh" in result.output
    assert "chmod +x" in result.output
