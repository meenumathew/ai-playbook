"""Claude telemetry Stop-hook configuration helpers."""

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
TELEMETRY_HARNESS_SCRIPT = Path("harness") / "telemetry.sh"
TELEMETRY_USAGE_LOG = Path(".claude") / "usage.jsonl"


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
    """Ensure Claude Stop hook writes session telemetry through the starter harness."""
    if tool is not Tool.claude:
        return "[dim]skipped[/dim] telemetry Stop hook (Claude only)"
    settings_path = _claude_settings_path(project_root)
    if dry_run:
        return "[yellow]would configure[/yellow] telemetry Stop hook"

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
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return False
    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return False
    return any(_entry_has_telemetry_hook(entry) for entry in stop_hooks)


def telemetry_hook_configured(project_root: Path) -> bool:
    """Return True when deployed Claude settings contain the AI Playbook Stop hook."""
    settings_path = _claude_settings_path(project_root)
    if not settings_path.exists():
        return False
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return isinstance(settings, dict) and has_telemetry_hook(settings)


def disable_telemetry_hook(project_root: Path) -> str:
    """Remove the AI Playbook Stop hook from Claude settings, leaving other hooks intact."""
    settings_path = _claude_settings_path(project_root)
    if not settings_path.exists():
        return "[dim]not configured[/dim] telemetry Stop hook (no settings.json)"

    settings = _read_settings(settings_path, project_root)
    if isinstance(settings, str):
        return settings
    if not has_telemetry_hook(settings):
        return "[dim]not configured[/dim] telemetry Stop hook"

    _remove_telemetry_hook(settings)
    write_text_safely(settings_path, json.dumps(settings, indent=2) + "\n", project_root)
    return "[green]disabled[/green] telemetry Stop hook"


def telemetry_status(project_root: Path) -> TelemetryStatus:
    """Inspect the on-disk state of telemetry wiring in an adopter project."""
    settings_path = _claude_settings_path(project_root)
    usage_log_path = project_root / TELEMETRY_USAGE_LOG
    return TelemetryStatus(
        settings_path=settings_path,
        settings_exists=settings_path.exists(),
        hook_configured=telemetry_hook_configured(project_root),
        harness_script_present=(project_root / TELEMETRY_HARNESS_SCRIPT).exists(),
        usage_log_path=usage_log_path,
        usage_log_exists=usage_log_path.exists(),
        usage_log_bytes=usage_log_path.stat().st_size if usage_log_path.exists() else 0,
    )


def _claude_settings_path(project_root: Path) -> Path:
    return project_root / get_target_adapter(Tool.claude).mcp_config.path


def _read_settings(settings_path: Path, safe_root: Path) -> dict[str, Any] | str:
    assert_safe_destination(settings_path, safe_root)
    if not settings_path.exists():
        return {}
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
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
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        hooks = {}
        settings["hooks"] = hooks
    stop_hooks = hooks.setdefault("Stop", [])
    if not isinstance(stop_hooks, list):
        stop_hooks = []
        hooks["Stop"] = stop_hooks
    stop_hooks.append(_telemetry_stop_entry())


def _telemetry_stop_entry() -> dict[str, Any]:
    return {
        "matcher": "",
        "hooks": [
            {
                "type": "command",
                "command": TELEMETRY_HOOK_COMMAND,
                "timeout": 5,
            }
        ],
    }


def _remove_telemetry_hook(settings: dict[str, Any]) -> None:
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return
    stop_hooks = hooks.get("Stop")
    if not isinstance(stop_hooks, list):
        return
    pruned_entries: list[Any] = []
    for entry in stop_hooks:
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
            if not (isinstance(hook, dict) and hook.get("command") == TELEMETRY_HOOK_COMMAND)
        ]
        if not kept_inner:
            continue
        new_entry = dict(entry)
        new_entry["hooks"] = kept_inner
        pruned_entries.append(new_entry)
    if pruned_entries:
        hooks["Stop"] = pruned_entries
    else:
        hooks.pop("Stop", None)
    if not hooks:
        settings.pop("hooks", None)


def _entry_has_telemetry_hook(entry: Any) -> bool:
    if not isinstance(entry, dict):
        return False
    hooks = entry.get("hooks")
    if not isinstance(hooks, list):
        return False
    return any(
        isinstance(hook, dict) and hook.get("command") == TELEMETRY_HOOK_COMMAND for hook in hooks
    )
