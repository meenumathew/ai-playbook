"""MCP (Model Context Protocol) configuration for the deploy CLI.

Each supported tool keeps its MCP server list in a different file with a
slightly different schema; this module hides those differences behind one
function and protects the user's existing config from being silently destroyed
by a malformed JSON parse.
"""

from __future__ import annotations

import json
from pathlib import Path

from deploy_ai_playbook.paths import ATLASSIAN_MCP_URL, Tool
from deploy_ai_playbook.safety import (
    assert_safe_destination,
    preserve_broken_config,
    write_text_safely,
)
from deploy_ai_playbook.targets import get_target_adapter


def deploy_mcp_config(project_root: Path, tool: Tool, dry_run: bool) -> str:
    """Ensure Atlassian MCP server is configured for the given tool.

    Merges into existing config if present. Returns a Rich-formatted status
    string for the caller to print.

    Safety: if the existing config file contains malformed JSON, this function
    does **not** overwrite it. It saves a timestamped `.broken-<ts>` copy and
    returns an actionable error string so the user can recover.
    """
    config = get_target_adapter(tool).mcp_config
    config_path = project_root / config.path
    key = config.key

    atlassian_entry = {"type": "http", "url": ATLASSIAN_MCP_URL}

    if dry_run:
        return "[yellow]would configure[/yellow]"

    assert_safe_destination(config_path, project_root)

    existing: dict = {}
    if config_path.exists():
        try:
            parsed = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            backup_path = preserve_broken_config(config_path, project_root)
            return (
                f"[red]malformed JSON in {config_path}[/red] "
                f"(line {exc.lineno}, col {exc.colno}): {exc.msg}. "
                f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
                f"fix the file by hand or delete it and re-run deploy."
            )
        if not isinstance(parsed, dict):
            backup_path = preserve_broken_config(config_path, project_root)
            return (
                f"[red]{config_path} is not a JSON object[/red] "
                f"(top level is {type(parsed).__name__}, expected an object). "
                f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
                f"fix the file by hand or delete it and re-run deploy."
            )
        existing = parsed

    servers = existing.get(key, {})
    if not isinstance(servers, dict):
        servers = {}
    if (
        "atlassian" in servers
        and isinstance(servers["atlassian"], dict)
        and servers["atlassian"].get("url") == ATLASSIAN_MCP_URL
    ):
        return "[dim]already configured[/dim]"

    servers["atlassian"] = atlassian_entry
    existing[key] = servers

    write_text_safely(config_path, json.dumps(existing, indent=2) + "\n", project_root)
    return "[green]configured[/green]"
