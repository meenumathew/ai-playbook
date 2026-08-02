"""Privacy-minimal local telemetry hook configuration for supported tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.safety import (
    assert_safe_destination,
    preserve_broken_config,
    write_text_safely,
)
from deploy_ai_playbook.targets import get_target_adapter

TELEMETRY_HOOK_COMMAND = "${CLAUDE_PROJECT_DIR}/harness/telemetry.sh"
# Codex hooks run from the project directory but expose no project-root
# variable, so the command resolves the harness script itself: the local
# harness copy when the working directory has one, else the git toplevel
# (session cwd may sit below the project root), else the working directory.
# Local-first matters for a non-repo project folder nested inside an outer
# git repository: a git-first probe would resolve to the outer repo root,
# which has no harness script.
CODEX_TELEMETRY_HOOK_COMMAND = (
    '/bin/sh "$([ -f harness/telemetry.sh ] && pwd'
    ' || git rev-parse --show-toplevel 2>/dev/null || pwd)/harness/telemetry.sh" codex'
)
TELEMETRY_HARNESS_SCRIPT = Path("harness") / "telemetry.sh"
TELEMETRY_USAGE_LOG = Path(".claude") / "usage.jsonl"
CODEX_TELEMETRY_HOOKS = Path(".codex") / "hooks.json"
CODEX_TELEMETRY_USAGE_LOG = Path(".codex") / "usage.jsonl"


@dataclass(frozen=True)
class TelemetryStatus:
    """Snapshot of telemetry wiring in an adopter project."""

    settings_path: Path
    settings_exists: bool
    hook_configured: bool
    harness_script_present: bool
    usage_log_path: Path
    usage_log_exists: bool
    usage_log_bytes: int


def deploy_telemetry_hook_config(project_root: Path, tool: Tool, dry_run: bool) -> str:
    """Ensure a supported tool writes session telemetry through the starter harness."""
    if tool not in {Tool.claude, Tool.codex}:
        return f"[dim]skipped[/dim] telemetry hook ({tool.value} has no supported lifecycle hook)"
    event = "Stop" if tool is Tool.claude else "SessionEnd"
    if dry_run:
        return f"[yellow]would configure[/yellow] telemetry {event} hook"
    if tool is Tool.codex:
        return _deploy_codex_telemetry_hook(project_root)

    settings_path = _claude_settings_path(project_root)
    settings = _read_settings(settings_path, project_root)
    if isinstance(settings, str):
        return settings
    if has_telemetry_hook(settings):
        return "[dim]already configured[/dim] telemetry Stop hook"

    _append_telemetry_hook(settings)
    write_text_safely(settings_path, json.dumps(settings, indent=2) + "\n", project_root)
    return (
        "[green]configured[/green] telemetry Stop hook — local-only session log in "
        ".claude/usage.jsonl; opt out with [bold]ai-playbook telemetry disable[/bold]"
    )


def has_telemetry_hook(settings: dict[str, Any]) -> bool:
    """Return True when a Claude settings object already calls the telemetry hook."""
    return _has_command_hook(settings, "Stop", TELEMETRY_HOOK_COMMAND)


def has_codex_telemetry_hook(settings: dict[str, Any]) -> bool:
    """Return True when Codex hooks contain the AI Playbook SessionEnd hook."""
    return _has_command_hook(settings, "SessionEnd", CODEX_TELEMETRY_HOOK_COMMAND)


def telemetry_hook_configured(project_root: Path, tool: Tool = Tool.claude) -> bool:
    """Return True when the selected tool contains the AI Playbook telemetry hook."""
    if tool not in {Tool.claude, Tool.codex}:
        return False
    settings_path = _telemetry_settings_path(project_root, tool)
    if not settings_path.exists():
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return False
    if not isinstance(settings, dict):
        return False
    return (
        has_telemetry_hook(settings) if tool is Tool.claude else has_codex_telemetry_hook(settings)
    )


def disable_telemetry_hook(project_root: Path, tool: Tool = Tool.claude) -> str:
    """Remove the selected tool's AI Playbook hook, leaving other hooks intact."""
    if tool not in {Tool.claude, Tool.codex}:
        return f"[dim]not configured[/dim] telemetry hook ({tool.value} unsupported)"
    settings_path = _telemetry_settings_path(project_root, tool)
    event = "Stop" if tool is Tool.claude else "SessionEnd"
    if not settings_path.exists():
        return f"[dim]not configured[/dim] telemetry {event} hook (no config file)"

    settings = _read_settings(settings_path, project_root)
    if isinstance(settings, str):
        return settings
    configured = (
        has_telemetry_hook(settings) if tool is Tool.claude else has_codex_telemetry_hook(settings)
    )
    if not configured:
        return f"[dim]not configured[/dim] telemetry {event} hook"

    command = TELEMETRY_HOOK_COMMAND if tool is Tool.claude else CODEX_TELEMETRY_HOOK_COMMAND
    _remove_command_hook(settings, event, command)
    write_text_safely(settings_path, json.dumps(settings, indent=2) + "\n", project_root)
    return f"[green]disabled[/green] telemetry {event} hook"


def telemetry_status(
    project_root: Path,
    tool: Tool = Tool.claude,
) -> TelemetryStatus:
    """Inspect the on-disk state of telemetry wiring in an adopter project."""
    settings_path = _telemetry_settings_path(project_root, tool)
    usage_log_path = project_root / (
        CODEX_TELEMETRY_USAGE_LOG if tool is Tool.codex else TELEMETRY_USAGE_LOG
    )
    return TelemetryStatus(
        settings_path=settings_path,
        settings_exists=settings_path.exists(),
        hook_configured=telemetry_hook_configured(project_root, tool),
        harness_script_present=(project_root / TELEMETRY_HARNESS_SCRIPT).exists(),
        usage_log_path=usage_log_path,
        usage_log_exists=usage_log_path.exists(),
        usage_log_bytes=usage_log_path.stat().st_size if usage_log_path.exists() else 0,
    )


def _claude_settings_path(project_root: Path) -> Path:
    return project_root / get_target_adapter(Tool.claude).mcp_config.path


def _telemetry_settings_path(project_root: Path, tool: Tool) -> Path:
    if tool is Tool.codex:
        return project_root / CODEX_TELEMETRY_HOOKS
    return _claude_settings_path(project_root)


def _deploy_codex_telemetry_hook(project_root: Path) -> str:
    hooks_path = project_root / CODEX_TELEMETRY_HOOKS
    settings = _read_settings(hooks_path, project_root)
    if isinstance(settings, str):
        return settings
    if has_codex_telemetry_hook(settings):
        return "[dim]already configured[/dim] telemetry SessionEnd hook"
    _append_command_hook(
        settings,
        event="SessionEnd",
        command=CODEX_TELEMETRY_HOOK_COMMAND,
        timeout=3,
    )
    write_text_safely(hooks_path, json.dumps(settings, indent=2) + "\n", project_root)
    return (
        "[green]configured[/green] telemetry SessionEnd hook — local-only session log in "
        ".codex/usage.jsonl; review and trust it with [bold]/hooks[/bold]; "
        "opt out with [bold]ai-playbook telemetry disable --tool codex[/bold]"
    )


def _read_settings(settings_path: Path, safe_root: Path) -> dict[str, Any] | str:
    assert_safe_destination(settings_path, safe_root)
    if not settings_path.exists():
        return {}
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except UnicodeDecodeError:
        backup_path = preserve_broken_config(settings_path, safe_root)
        return (
            f"[red]{settings_path} is not valid UTF-8[/red]. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            "fix the file by hand or delete it and re-run deploy."
        )
    except json.JSONDecodeError as exc:
        backup_path = preserve_broken_config(settings_path, safe_root)
        return (
            f"[red]malformed JSON in {settings_path}[/red] "
            f"(line {exc.lineno}, col {exc.colno}): {exc.msg}. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            "fix the file by hand or delete it and re-run deploy."
        )
    if isinstance(settings, dict):
        return settings
    backup_path = preserve_broken_config(settings_path, safe_root)
    return (
        f"[red]{settings_path} is not a JSON object[/red] "
        f"(top level is {type(settings).__name__}, expected an object). "
        f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
        "fix the file by hand or delete it and re-run deploy."
    )


def _append_telemetry_hook(settings: dict[str, Any]) -> None:
    _append_command_hook(
        settings,
        event="Stop",
        command=TELEMETRY_HOOK_COMMAND,
        timeout=5,
        matcher="",
    )


def _append_command_hook(
    settings: dict[str, Any],
    *,
    event: str,
    command: str,
    timeout: int,
    matcher: str | None = None,
) -> None:
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        settings["hooks"] = hooks
    event_hooks = hooks.setdefault(event, [])
    if not isinstance(event_hooks, list):
        event_hooks = []
        hooks[event] = event_hooks
    entry: dict[str, Any] = {
        "hooks": [
            {
                "type": "command",
                "command": command,
                "timeout": timeout,
            }
        ]
    }
    if matcher is not None:
        entry["matcher"] = matcher
    event_hooks.append(entry)


def _remove_command_hook(settings: dict[str, Any], event: str, command: str) -> None:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    event_hooks = hooks.get(event)
    if not isinstance(event_hooks, list):
        return
    pruned_entries: list[Any] = []
    for entry in event_hooks:
        if not isinstance(entry, dict):
            pruned_entries.append(entry)
            continue
        inner = entry.get("hooks")
        if not isinstance(inner, list):
            pruned_entries.append(entry)
            continue
        kept_inner = [
            hook
            for hook in inner
            if not (isinstance(hook, dict) and hook.get("command") == command)
        ]
        if not kept_inner:
            continue
        new_entry = dict(entry)
        new_entry["hooks"] = kept_inner
        pruned_entries.append(new_entry)
    if pruned_entries:
        hooks[event] = pruned_entries
    else:
        hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)


def _has_command_hook(settings: dict[str, Any], event: str, command: str) -> bool:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    event_hooks = hooks.get(event)
    if not isinstance(event_hooks, list):
        return False
    return any(_entry_has_command_hook(entry, command) for entry in event_hooks)


def _entry_has_command_hook(entry: Any, command: str) -> bool:
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(isinstance(hook, dict) and hook.get("command") == command for hook in hooks)
