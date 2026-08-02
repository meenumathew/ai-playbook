"""Unit tests for privacy-minimal local telemetry hook configuration."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.telemetry import (
    CODEX_TELEMETRY_HOOK_COMMAND,
    TELEMETRY_HOOK_COMMAND,
    deploy_telemetry_hook_config,
    disable_telemetry_hook,
    has_codex_telemetry_hook,
    has_telemetry_hook,
    telemetry_hook_configured,
    telemetry_status,
)


def _run_codex_hook_command(cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the Codex hook command from `cwd` the way a hook runner would.

    The command is a POSIX one-liner (command substitution, `[ -f ]`, `||`),
    so it needs a shell. An explicit `/bin/sh -c` argv is used rather than
    `shell=True`: same interpreter, but the argument vector is fixed at the
    call site instead of assembled by Python's platform-specific shell
    handling, so there is no shell string for a caller to extend.
    """
    return subprocess.run(  # noqa: S603 - argv is a module constant, never caller input
        ["/bin/sh", "-c", CODEX_TELEMETRY_HOOK_COMMAND],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
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


def test_codex_telemetry_hook_preserves_malformed_json(tmp_path: Path) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text("not json {{{")

    status = deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)

    assert "malformed JSON" in status
    assert hooks_path.read_text() == "not json {{{"
    assert len(list(hooks_path.parent.glob("hooks.json.broken-*"))) == 1


def test_codex_telemetry_hook_preserves_non_utf8_settings(tmp_path: Path) -> None:
    """A non-UTF-8 config gets the same preserve-and-report treatment as bad JSON.

    Regression: read_text raised UnicodeDecodeError before JSON parsing, so
    deploy crashed with a traceback instead of preserving the file.
    """
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    raw = b'\xff\xfe{"hooks": {}}'
    hooks_path.write_bytes(raw)

    status = deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)

    assert "not valid UTF-8" in status
    assert hooks_path.read_bytes() == raw
    backups = list(hooks_path.parent.glob("hooks.json.broken-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == raw
    assert not telemetry_hook_configured(tmp_path, Tool.codex)


def test_deploy_telemetry_hook_config_preserves_non_object_settings(
    tmp_path: Path,
) -> None:
    """Valid-but-non-object settings JSON must not be silently replaced by a
    hooks-only file: preserve it, save a `.broken-*` copy, report an error:
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


def test_deploy_telemetry_hook_config_writes_codex_session_end_hook(tmp_path: Path) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)

    assert "configured" in status
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert has_codex_telemetry_hook(hooks)
    command_hooks = hooks["hooks"]["SessionEnd"][0]["hooks"]
    assert command_hooks == [
        {
            "type": "command",
            "command": CODEX_TELEMETRY_HOOK_COMMAND,
            "timeout": 3,
        }
    ]


def test_deploy_telemetry_hook_config_preserves_codex_hooks_and_is_idempotent(
    tmp_path: Path,
) -> None:
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(
        json.dumps(
            {
                "description": "team hooks",
                "hooks": {
                    "SessionEnd": [
                        {"hooks": [{"type": "command", "command": "python team_session_end.py"}]}
                    ],
                    "PreToolUse": [{"matcher": "Bash", "hooks": []}],
                },
            }
        ),
        encoding="utf-8",
    )

    deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)
    status = deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert status.startswith("[dim]already configured")
    assert hooks["description"] == "team hooks"
    assert hooks["hooks"]["PreToolUse"] == [{"matcher": "Bash", "hooks": []}]
    commands = [
        hook["command"] for entry in hooks["hooks"]["SessionEnd"] for hook in entry.get("hooks", [])
    ]
    assert commands.count(CODEX_TELEMETRY_HOOK_COMMAND) == 1
    assert "python team_session_end.py" in commands


def test_codex_telemetry_hook_command_resolves_outside_a_git_repo(tmp_path: Path) -> None:
    """The hook must find harness/telemetry.sh when the project root is not a git repo.

    Regression: the original command resolved the script through
    `git rev-parse --show-toplevel`, which exits non-zero outside a repo, so
    the SessionEnd hook failed on every session in non-git adopter roots.
    """
    script = tmp_path / "harness" / "telemetry.sh"
    script.parent.mkdir(parents=True)
    marker = tmp_path / "ran.txt"
    script.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\n', encoding="utf-8")
    script.chmod(0o755)

    result = _run_codex_hook_command(tmp_path)

    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8").strip() == "codex"


def test_codex_telemetry_hook_command_prefers_git_toplevel_inside_a_repo(tmp_path: Path) -> None:
    """Inside a repo the hook resolves from the repo root even when cwd is a subdir."""
    script = tmp_path / "harness" / "telemetry.sh"
    script.parent.mkdir(parents=True)
    marker = tmp_path / "ran.txt"
    script.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\n', encoding="utf-8")
    script.chmod(0o755)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    subdir = tmp_path / "sub"
    subdir.mkdir()

    result = _run_codex_hook_command(subdir)

    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8").strip() == "codex"


def test_codex_telemetry_hook_command_prefers_local_script_in_nested_non_repo_project(
    tmp_path: Path,
) -> None:
    """A non-repo project folder inside an outer git repo must resolve locally.

    Regression: with a bare git-toplevel-or-pwd fallback, `git rev-parse`
    succeeds and resolves to the OUTER repo root, which has no
    harness/telemetry.sh, so the hook failed with exit 127.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)  # noqa: S607
    project = tmp_path / "workspace"
    script = project / "harness" / "telemetry.sh"
    script.parent.mkdir(parents=True)
    marker = project / "ran.txt"
    script.write_text(f'#!/bin/sh\necho "$1" > "{marker}"\n', encoding="utf-8")
    script.chmod(0o755)

    result = _run_codex_hook_command(project)

    assert result.returncode == 0, result.stderr
    assert marker.read_text(encoding="utf-8").strip() == "codex"


def test_disable_telemetry_hook_removes_only_codex_playbook_entry(tmp_path: Path) -> None:
    deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)
    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    hooks["hooks"]["SessionEnd"][0]["hooks"].insert(
        0, {"type": "command", "command": "python team_session_end.py"}
    )
    hooks_path.write_text(json.dumps(hooks), encoding="utf-8")

    status = disable_telemetry_hook(tmp_path, Tool.codex)

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert "disabled" in status
    assert hooks["hooks"]["SessionEnd"][0]["hooks"] == [
        {"type": "command", "command": "python team_session_end.py"}
    ]
    assert not has_codex_telemetry_hook(hooks)


def test_deploy_telemetry_hook_config_skips_unsupported_tools(tmp_path: Path) -> None:
    status = deploy_telemetry_hook_config(tmp_path, Tool.copilot, dry_run=False)

    assert "skipped" in status
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert not (tmp_path / ".codex" / "hooks.json").exists()


def test_telemetry_hook_configured_is_false_for_unsupported_tools(tmp_path: Path) -> None:
    assert not telemetry_hook_configured(tmp_path, Tool.copilot)


def test_disable_telemetry_hook_reports_unsupported_tools_as_not_configured(
    tmp_path: Path,
) -> None:
    status = disable_telemetry_hook(tmp_path, Tool.copilot)

    assert "not configured" in status
    assert "copilot unsupported" in status


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


def test_telemetry_status_reports_codex_hook_and_log(tmp_path: Path) -> None:
    deploy_telemetry_hook_config(tmp_path, Tool.codex, dry_run=False)
    harness_dir = tmp_path / "harness"
    harness_dir.mkdir()
    (harness_dir / "telemetry.sh").write_text("#!/bin/sh\n")
    usage_log = tmp_path / ".codex" / "usage.jsonl"
    usage_log.write_text('{"source":"codex"}\n', encoding="utf-8")

    info = telemetry_status(tmp_path, Tool.codex)

    assert info.settings_path == tmp_path / ".codex" / "hooks.json"
    assert info.hook_configured is True
    assert info.usage_log_path == usage_log
    assert info.usage_log_bytes == len('{"source":"codex"}\n')
