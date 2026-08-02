"""MCP (Model Context Protocol) configuration for the deploy CLI.

Each supported tool keeps its MCP server list in a different file with a
slightly different schema; this module hides those differences behind one
function and protects the user's existing config from being silently destroyed
by a malformed JSON parse.
"""

from __future__ import annotations

import json
import re
import tomllib
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

    if tool is Tool.codex:
        return _deploy_codex_mcp_config(config_path, project_root)

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


def _deploy_codex_mcp_config(config_path: Path, project_root: Path) -> str:
    try:
        current = config_path.read_text(encoding="utf-8") if config_path.exists() else ""
    except UnicodeDecodeError:
        backup_path = preserve_broken_config(config_path, project_root)
        return (
            f"[red]{config_path} is not valid UTF-8[/red]. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            "fix the file by hand or delete it and re-run deploy."
        )
    try:
        parsed = tomllib.loads(current) if current else {}
    except tomllib.TOMLDecodeError as exc:
        backup_path = preserve_broken_config(config_path, project_root)
        location = _toml_error_location(exc)
        return (
            f"[red]malformed TOML in {config_path}[/red] "
            f"{location}{exc}. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            f"fix the file by hand or delete it and re-run deploy."
        )

    mcp_servers = parsed.get("mcp_servers", {})
    if not isinstance(mcp_servers, dict):
        backup_path = preserve_broken_config(config_path, project_root)
        return (
            f"[red]{config_path} has non-table mcp_servers[/red]. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            f"fix the file by hand or delete it and re-run deploy."
        )
    atlassian = mcp_servers.get("atlassian", {})
    if not isinstance(atlassian, dict):
        backup_path = preserve_broken_config(config_path, project_root)
        return (
            f"[red]{config_path} has non-table mcp_servers.atlassian[/red]. "
            f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
            f"fix the file by hand or delete it and re-run deploy."
        )
    if atlassian.get("url") == ATLASSIAN_MCP_URL:
        return "[dim]already configured[/dim]"

    # The line-based upsert only rewrites the `[mcp_servers.atlassian]`
    # header form. Any other declaration shape: inline table or dotted
    # key, including EMPTY inline tables (`mcp_servers = {}`,
    # `atlassian = {}`), which TOML treats as closed and non-extendable:
    # would get a second declaration appended, producing invalid TOML.
    # Preserve the file and report instead of writing.
    lines = current.splitlines()
    if _find_toml_table(lines, "mcp_servers.atlassian") is None:
        inline_servers = "mcp_servers" in parsed and not _has_mcp_servers_header(lines)
        inline_atlassian = "atlassian" in mcp_servers
        if inline_servers or inline_atlassian:
            backup_path = preserve_broken_config(config_path, project_root)
            return (
                f"[red]{config_path} declares mcp_servers in an "
                f"unsupported TOML shape[/red] (inline table or dotted key). "
                f"Saved a copy to [cyan]{backup_path.name}[/cyan]; "
                f"rewrite it as a [mcp_servers.atlassian] table or remove it "
                f"and re-run deploy."
            )

    write_text_safely(config_path, _upsert_codex_atlassian_mcp(current), project_root)
    return "[green]configured[/green]"


def _upsert_codex_atlassian_mcp(content: str) -> str:
    block = f"[mcp_servers.atlassian]\nurl = {json.dumps(ATLASSIAN_MCP_URL)}\n"
    if not content.strip():
        return block
    lines = content.splitlines()
    start = _find_toml_table(lines, "mcp_servers.atlassian")
    if start is None:
        suffix = "" if content.endswith("\n") else "\n"
        separator = "" if content.endswith("\n\n") else "\n"
        return content + suffix + separator + block

    end = _next_toml_table(lines, start + 1)
    url_line = f"url = {json.dumps(ATLASSIAN_MCP_URL)}"
    for index in range(start + 1, end):
        # Exactly the `url` key: a prefix match would clobber unrelated
        # keys such as `url_timeout`.
        if re.match(r"url\s*=", lines[index].strip()):
            lines[index] = url_line
            return "\n".join(lines) + "\n"
    lines.insert(start + 1, url_line)
    return "\n".join(lines) + "\n"


def _has_mcp_servers_header(lines: list[str]) -> bool:
    """True when mcp_servers is declared via `[mcp_servers]`/`[mcp_servers.*]`."""
    for line in lines:
        stripped = line.strip()
        if stripped == "[mcp_servers]" or (
            stripped.startswith("[mcp_servers.") and stripped.endswith("]")
        ):
            return True
    return False


def _find_toml_table(lines: list[str], table: str) -> int | None:
    header = f"[{table}]"
    for index, line in enumerate(lines):
        if line.strip() == header:
            return index
    return None


def _next_toml_table(lines: list[str], start: int) -> int:
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            return index
    return len(lines)


def _toml_error_location(exc: tomllib.TOMLDecodeError) -> str:
    lineno = getattr(exc, "lineno", None)
    colno = getattr(exc, "colno", None)
    if lineno is None or colno is None:
        return ""
    return f"(line {lineno}, col {colno}): "
