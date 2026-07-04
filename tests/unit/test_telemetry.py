"""Unit tests for Claude telemetry Stop-hook configuration."""

from __future__ import annotations

import json
from pathlib import Path

from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.telemetry import (
    TELEMETRY_HOOK_COMMAND,
    deploy_telemetry_hook_config,
    disable_telemetry_hook,
    has_telemetry_hook,
    telemetry_hook_configured,
    telemetry_status,
)


def test_deploy_telemetry_hook_config_dry_run_does_not_write(tmp_path: Path) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=True)

    assert "would configure" in status
    assert not (tmp_path / ".claude" / "settings.json").exists()


def test_deploy_telemetry_hook_config_writes_stop_hook(tmp_path: Path) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert "configured" in status
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert has_telemetry_hook(settings)


def test_deploy_telemetry_hook_config_discloses_log_destination_and_opt_out(
    tmp_path: Path,
) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert ".claude/usage.jsonl" in status
    assert "telemetry disable" in status


def test_deploy_telemetry_hook_config_preserves_existing_settings(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"mcpServers": {"custom": {"url": "https://mcp"}}}))

    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    settings = json.loads(settings_path.read_text())
    assert settings["mcpServers"] == {"custom": {"url": "https://mcp"}}
    assert has_telemetry_hook(settings)


def test_deploy_telemetry_hook_config_is_idempotent(tmp_path: Path) -> None:
    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)
    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    stop_hooks = settings["hooks"]["Stop"]
    telemetry_hooks = [
        hook
        for entry in stop_hooks
        for hook in entry.get("hooks", [])
        if hook.get("command") == "${CLAUDE_PROJECT_DIR}/harness/telemetry.sh"
    ]
    assert "already configured" in status
    assert len(telemetry_hooks) == 1


def test_deploy_telemetry_hook_config_preserves_malformed_json(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("not json {{{")

    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert "malformed JSON" in status
    assert settings_path.read_text() == "not json {{{"
    assert len(list(settings_path.parent.glob("settings.json.broken-*"))) == 1


def test_deploy_telemetry_hook_config_preserves_non_object_settings(
    tmp_path: Path,
) -> None:
    """Valid-but-non-object settings JSON must not be silently replaced by a
    hooks-only file: preserve it, save a `.broken-*` copy, report an error —
    the same contract as the malformed-JSON path."""
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("[]")

    status = deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert "not a JSON object" in status
    assert settings_path.read_text() == "[]"
    assert len(list(settings_path.parent.glob("settings.json.broken-*"))) == 1


def test_deploy_telemetry_hook_config_replaces_invalid_hooks_shape(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"hooks": "invalid"}))

    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert has_telemetry_hook(json.loads(settings_path.read_text()))


def test_deploy_telemetry_hook_config_replaces_invalid_stop_hook_shape(
    tmp_path: Path,
) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"hooks": {"Stop": "invalid"}}))

    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    assert has_telemetry_hook(json.loads(settings_path.read_text()))


def test_deploy_telemetry_hook_config_skips_non_claude_tools(tmp_path: Path) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.copilot, dry_run=False)

    assert "skipped" in status
    assert not (tmp_path / ".claude" / "settings.json").exists()


def test_has_telemetry_hook_rejects_missing_hook() -> None:
    assert not has_telemetry_hook({"hooks": {"Stop": []}})


def test_has_telemetry_hook_rejects_invalid_entries() -> None:
    assert not has_telemetry_hook({"hooks": {"Stop": ["invalid", {"hooks": "invalid"}]}})


def test_telemetry_hook_configured_handles_missing_and_malformed_settings(
    tmp_path: Path,
) -> None:
    assert not telemetry_hook_configured(tmp_path)

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("not json {{{")

    assert not telemetry_hook_configured(tmp_path)


def test_disable_telemetry_hook_removes_only_playbook_entry(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(
        json.dumps(
            {
                "mcpServers": {"custom": {"url": "https://mcp"}},
                "hooks": {
                    "Stop": [
                        {
                            "matcher": "",
                            "hooks": [
                                {"type": "command", "command": "echo team-hook"},
                                {"type": "command", "command": TELEMETRY_HOOK_COMMAND},
                            ],
                        },
                    ],
                },
            }
        )
    )

    status = disable_telemetry_hook(tmp_path)

    settings = json.loads(settings_path.read_text())
    assert "disabled" in status
    assert settings["mcpServers"] == {"custom": {"url": "https://mcp"}}
    assert settings["hooks"]["Stop"][0]["hooks"] == [
        {"type": "command", "command": "echo team-hook"}
    ]
    assert not has_telemetry_hook(settings)


def test_disable_telemetry_hook_drops_empty_stop_block(tmp_path: Path) -> None:
    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)

    disable_telemetry_hook(tmp_path)

    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "hooks" not in settings


def test_disable_telemetry_hook_when_not_configured(tmp_path: Path) -> None:
    no_settings = disable_telemetry_hook(tmp_path)
    assert "not configured" in no_settings

    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text(json.dumps({"mcpServers": {}}))

    not_configured = disable_telemetry_hook(tmp_path)
    assert "not configured" in not_configured


def test_disable_telemetry_hook_preserves_malformed_json(tmp_path: Path) -> None:
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("not json {{{")

    status = disable_telemetry_hook(tmp_path)

    assert "malformed JSON" in status
    assert settings_path.read_text() == "not json {{{"


def test_telemetry_status_reports_uninstalled(tmp_path: Path) -> None:
    info = telemetry_status(tmp_path)

    assert info.settings_exists is False
    assert info.hook_configured is False
    assert info.harness_script_present is False
    assert info.usage_log_exists is False
    assert info.usage_log_bytes == 0


def test_telemetry_status_reports_configured(tmp_path: Path) -> None:
    deploy_telemetry_hook_config(tmp_path, Tool.claude, dry_run=False)
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    (harness_dir / "telemetry.sh").write_text("#!/bin/sh\n")
    usage_log = tmp_path / ".claude" / "usage.jsonl"
    usage_log.write_text('{"ts":"now"}\n')

    info = telemetry_status(tmp_path)

    assert info.settings_exists is True
    assert info.hook_configured is True
    assert info.harness_script_present is True
    assert info.usage_log_exists is True
    assert info.usage_log_bytes == len('{"ts":"now"}\n')
