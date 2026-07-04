"""CLI for deploying ai-playbook agents to Claude, Copilot, Cursor, or Kiro.

Implementation is split across small modules — `paths`/`config`/`safety`/
`console` (foundation), `targets`/`discovery`/`fs`/`mcp`/`telemetry`
(middle), `backup`/`upgrade`/`doctor`/`services/*` (service), and
`deploy_render` (deploy presentation) — see tests/unit/test_architecture.py
for the layer map. This module wires up the Typer commands and re-exports
the public symbols so existing callers that import from
`deploy_ai_playbook.cli` keep working.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.table import Table
from rich.text import Text

# Aliased so the `--version` callback below reads as `PACKAGE_VERSION` instead
# of `__version__` at the call site (clearer, and `__version__` collides with
# Python's dunder convention for module-level attributes that this module does
# not actually own). N812 flags lowercase→non-lowercase renames, but the
# casing here is deliberate.
from deploy_ai_playbook import __version__ as PACKAGE_VERSION  # noqa: N812

# Re-exports — keep public API stable for tests and external callers.
# `__all__` documents the public surface and lets ruff understand that
# imports below which look unused at this module level are intentional
# re-exports for tests/external callers.
from deploy_ai_playbook.backup import (
    backup_deployed_files,
    latest_backup_for_tool,
    restore_backup,
    write_version_file,
)
from deploy_ai_playbook.config import (
    PACK_CONFIG_FILE,
    QUALITY_TIER_VALUES,
    ConfigError,
    QualityTierConfig,
    Source,
    load_model_tier_config,
    load_pack_config,
    load_quality_tier_config,
)
from deploy_ai_playbook.console import console, error_console
from deploy_ai_playbook.deploy_render import (
    DeployStepError,
)
from deploy_ai_playbook.deploy_render import (
    backup_existing_deployment as _backup_existing_deployment,
)
from deploy_ai_playbook.deploy_render import (
    deploy_commands as _deploy_commands,
)
from deploy_ai_playbook.deploy_render import (
    deploy_harness as _deploy_harness,
)
from deploy_ai_playbook.deploy_render import (
    deploy_layered as _deploy_layered,
)
from deploy_ai_playbook.deploy_render import (
    deploy_mcp as _deploy_mcp,
)
from deploy_ai_playbook.deploy_render import (
    deploy_rules as _deploy_rules,
)
from deploy_ai_playbook.deploy_render import (
    print_pack_metadata as _print_pack_metadata,
)
from deploy_ai_playbook.deploy_render import (
    print_rollback_hint as _print_rollback_hint,
)
from deploy_ai_playbook.deploy_render import (
    prune_deployment as _prune_deployment,
)
from deploy_ai_playbook.deploy_render import (
    write_deploy_version as _write_deploy_version,
)
from deploy_ai_playbook.discovery import (
    OVERLAY_DIRS,
    OVERLAY_TITLES,
    DeployableFile,
    UnknownAgentError,
    discover_agents,
    discover_layered,
    find_deployed_agent,
    get_agents_dir,
    get_source_root,
    resolve_agent_names,
    standard_agent_names,
)
from deploy_ai_playbook.doctor import DeploymentNotFoundError, DoctorReport, DoctorService
from deploy_ai_playbook.fs import (
    compute_source_fingerprint,
    copy_commands_directory,
    copy_directory,
    copy_file,
    diff_file,
    expected_deployed_files,
    prune_orphaned_files,
)
from deploy_ai_playbook.mcp import deploy_mcp_config
from deploy_ai_playbook.paths import (
    ATLASSIAN_MCP_URL,
    BACKUP_DIR,
    DISABLED_SUFFIX,
    HARNESS_FILES,
    LANGUAGE_FILES,
    MCP_CONFIG,
    ORIGINAL_PWD,
    RULES_SOURCE_FILE,
    TOOL_DESTINATIONS,
    VERSION_FILE,
    Tool,
    resolve_project_root,
)
from deploy_ai_playbook.safety import (
    UnsafeDestinationError,
    WriteAccessError,
    write_text_safely,
)
from deploy_ai_playbook.services.artifacts import (
    ARTIFACT_DIRECTORIES,
    ARTIFACT_IGNORE_LINES,
    ArtifactPolicy,
    artifact_gitignore_content,
    artifact_policy_status,
    collect_artifact_rows,
)
from deploy_ai_playbook.services.deploy import (
    AGENT_FILE_SUFFIX,
    language_skip_files,
    normalize_language_filter,
    path_rewrite,
)
from deploy_ai_playbook.services.diff import compute_diff
from deploy_ai_playbook.services.pack_validation import validate_pack_content
from deploy_ai_playbook.targets import get_target_adapter
from deploy_ai_playbook.telemetry import (
    deploy_telemetry_hook_config,
    disable_telemetry_hook,
    telemetry_status,
)
from deploy_ai_playbook.upgrade import (
    UpgradeReport,
    UpgradeStatus,
    check_upgrade,
    read_version_file,
)

__all__ = [
    "ATLASSIAN_MCP_URL",
    "BACKUP_DIR",
    "DISABLED_SUFFIX",
    "DONE_MESSAGE",
    "HARNESS_FILES",
    "LANGUAGE_FILES",
    "MCP_CONFIG",
    "ORIGINAL_PWD",
    "OVERLAY_DIRS",
    "OVERLAY_TITLES",
    "PACK_CONFIG_FILE",
    "RULES_SOURCE_FILE",
    "TOOL_DESTINATIONS",
    "VERSION_FILE",
    "DeploymentNotFoundError",
    "DoctorReport",
    "DoctorService",
    "Tool",
    "UpgradeReport",
    "UpgradeStatus",
    "app",
    "backup_deployed_files",
    "check_upgrade",
    "compute_source_fingerprint",
    "copy_commands_directory",
    "copy_directory",
    "copy_file",
    "deploy_mcp_config",
    "deploy_telemetry_hook_config",
    "diff_file",
    "disable_telemetry_hook",
    "discover_agents",
    "discover_layered",
    "expected_deployed_files",
    "find_deployed_agent",
    "get_agents_dir",
    "get_source_root",
    "latest_backup_for_tool",
    "load_model_tier_config",
    "load_pack_config",
    "load_quality_tier_config",
    "prune_orphaned_files",
    "resolve_agent_names",
    "resolve_project_root",
    "restore_backup",
    "standard_agent_names",
    "telemetry_status",
    "write_version_file",
]


DONE_MESSAGE = "\n[bold green]Done.[/bold green]"


app = typer.Typer(
    name="ai-playbook",
    help="Deploy ai-playbook agents and knowledge base to Claude, Copilot, Cursor, or Kiro",
    epilog=(
        "Quick start: ai-playbook deploy --tool claude --dry-run  "
        "(then drop --dry-run when the preview looks right). "
        "See docs/cli-reference.md for the full reference."
    ),
    add_completion=False,
)


def _print_version_and_exit(value: bool) -> None:
    """Typer eager callback for `--version`. Prints the version and exits 0.

    Standard Unix CLI convention: every binary answers `--version`. The
    string is the package's `importlib.metadata` version (declared in
    `pyproject.toml [project] version`), exposed as `__version__` from
    `deploy_ai_playbook.__init__`.
    """
    if value:
        console.print(f"ai-playbook {PACKAGE_VERSION}")
        raise typer.Exit(0)


@app.callback()
def _root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-V",
            callback=_print_version_and_exit,
            is_eager=True,
            help="Show the ai-playbook version and exit.",
        ),
    ] = False,
) -> None:
    """ai-playbook — deploy AI workflow agents to Claude, Copilot, Cursor, or Kiro."""


# Back-compat alias — the canonical implementation lives in paths.resolve_project_root.
_resolve_project_root = resolve_project_root


def _resolve_agent_names_or_exit(
    agent: str, all_agents: dict[str, Path], label: str = "agent"
) -> list[str]:
    """CLI wrapper around `discovery.resolve_agent_names`.

    The library raises `UnknownAgentError` so it stays presentation-free; this
    wrapper renders the error with Rich and exits the CLI with code 1.
    """
    try:
        return resolve_agent_names(agent, all_agents, label=label)
    except UnknownAgentError as exc:
        error_console.print(f"[red]Error:[/red] Unknown {exc.label}(s): {', '.join(exc.unknown)}")
        error_console.print(f"Available: {', '.join(exc.available)}")
        raise typer.Exit(1) from None


def _validate_language_filter(language: str | None) -> str | None:
    """Wrap normalize_language_filter with Typer-aware error handling."""
    try:
        return normalize_language_filter(language)
    except ValueError as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from None


def _exit_config_error(exc: ConfigError) -> NoReturn:
    error_console.print(f"[red]Error:[/red] {exc}")
    raise typer.Exit(1) from None


def _load_pack_config_or_exit(project_root: Path) -> list[Source]:
    try:
        return load_pack_config(project_root)
    except ConfigError as exc:
        _exit_config_error(exc)


def _load_quality_tier_config_or_exit(project_root: Path) -> QualityTierConfig:
    try:
        return load_quality_tier_config(project_root)
    except ConfigError as exc:
        _exit_config_error(exc)


def _deployed_language_filter(project_root: Path) -> str | None:
    """Read the language filter recorded by the last deploy, if any."""
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None or parsed.language is None:
        return None
    value = parsed.language.lower()
    if value in ("", "all"):
        return None
    return value if value in LANGUAGE_FILES else None


def _print_change_section(title: str, location: Path, changes: list[tuple[str, str]]) -> bool:
    if not changes:
        return False
    console.print(f"\n[bold]{title}[/bold] — {location}")
    for filename, status in changes:
        console.print(f"  {status} {filename}")
    return True


def _print_doctor_report(
    project_root: Path, tool: Tool, issues: list[str], warnings: list[str]
) -> None:
    console.print(f"\n[bold]Playbook Doctor[/bold] — {project_root} ({tool.value})\n")
    if not issues and not warnings:
        console.print("[bold green]✓ All healthy[/bold green]: deployment is up to date\n")
        return
    _print_problem_list("Issues", "red", "✗", issues)
    _print_problem_list("Warnings", "yellow", "⚠", warnings)
    console.print(f"\n[dim]Fix with: ai-playbook deploy --agent all --tool {tool.value}[/dim]")


def _print_problem_list(title: str, color: str, marker: str, items: list[str]) -> None:
    if not items:
        return
    prefix = "" if title == "Issues" else "\n"
    console.print(f"{prefix}[bold {color}]{title} ({len(items)}):[/bold {color}]")
    for item in items:
        console.print(f"  {marker} {item}")


# ---------------------------------------------------------------------------
# CLI commands — each does one thing
# ---------------------------------------------------------------------------

# Shared options reused across commands
_tool_option = typer.Option(
    Tool.claude, "--tool", "-T", help="Target tool: claude, copilot, cursor, kiro"
)
_target_dir_option = typer.Option(
    None, "--target-dir", "-t", help="Target project directory (defaults to current directory)"
)
_json_option = typer.Option(False, "--json", help="Print machine-readable JSON")


def _print_json(payload: object) -> None:
    typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _plain_markup(value: str) -> str:
    return Text.from_markup(value).plain


INIT_CONFIG_STUB = """\
# AI Playbook adopter configuration.
# Full reference: docs/cli-reference.md (deployed with the playbook).
# Every key is optional — an empty file means a core-only deploy.

# Adopter-local packs, deployed in declared order (last pack wins on collisions):
# packs = [".ai-playbook/packs/<name>"]

# Per-agent quality tier overrides ("production" or "prototype"):
# [quality_tiers.agents]
# docs-maintainer = "prototype"
"""


@app.command()
def init(
    target_dir: str | None = _target_dir_option,
) -> None:
    """Scaffold the artifact directories and a starter .ai-playbook.toml.

    Idempotent: existing directories and config are kept, never overwritten.
    """
    project_root = _resolve_project_root(target_dir)
    console.print(f"\n[bold]Init →[/bold] {project_root}\n")
    for directory in ARTIFACT_DIRECTORIES:
        keep_file = project_root / directory / ".gitkeep"
        if keep_file.exists():
            console.print(f"  [dim]exists, kept[/dim] {directory}/")
            continue
        keep_file.parent.mkdir(parents=True, exist_ok=True)
        keep_file.write_text("", encoding="utf-8")
        console.print(f"  [green]created[/green] {directory}/")
    config_path = project_root / PACK_CONFIG_FILE
    if config_path.exists():
        console.print(f"  [dim]exists, kept[/dim] {PACK_CONFIG_FILE}")
    else:
        config_path.write_text(INIT_CONFIG_STUB, encoding="utf-8")
        console.print(f"  [green]created[/green] {PACK_CONFIG_FILE}")
    console.print(
        "\nNext: [bold]ai-playbook deploy --agent all --tool <tool>[/bold] to deploy the playbook."
    )


@app.command(name="list")
def list_agents(
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
) -> None:
    """List all available agents (core + any configured pack agents)."""
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    all_agents = _discover_configured_agent_entries(source_root, project_root)
    if as_json:
        _print_json(
            {
                "agents": [
                    {"name": name, "file": entry.src_path.name, "origin": entry.origin}
                    for name, entry in all_agents.items()
                ]
            }
        )
        return
    table = Table(title="Available Agents")
    table.add_column("Name", style="cyan")
    table.add_column("File", style="green")
    table.add_column("Origin", style="dim")
    for name, entry in all_agents.items():
        table.add_row(name, entry.src_path.name, entry.origin)
    console.print(table)


@app.command()
def status(
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
) -> None:
    """Show what is currently deployed in the target directory."""
    project_root = _resolve_project_root(target_dir)
    agents_dir = get_agents_dir(project_root, tool)
    if not agents_dir.exists():
        if as_json:
            _print_json(
                {
                    "agents": [],
                    "deployed": False,
                    "project_root": str(project_root),
                    "tool": tool.value,
                }
            )
            return
        console.print(f"[yellow]Nothing deployed at {agents_dir}[/yellow]")
        return
    quality_tiers = _load_quality_tier_config_or_exit(project_root)
    default_quality_tier = _deployed_quality_tier(project_root, tool)
    all_files = sorted(
        [
            *agents_dir.glob(f"*{AGENT_FILE_SUFFIX}"),
            *agents_dir.glob(f"*{AGENT_FILE_SUFFIX}{DISABLED_SUFFIX}"),
        ]
    )
    rows: list[dict[str, str]] = []
    for f in all_files:
        name = f.name.replace(f"{AGENT_FILE_SUFFIX}{DISABLED_SUFFIX}", "").replace(
            AGENT_FILE_SUFFIX, ""
        )
        quality_tier, quality_tier_source, quality_tier_label = _agent_quality_tier_details(
            name,
            quality_tiers.agent_overrides,
            default_quality_tier,
        )
        status_text = "disabled" if f.name.endswith(DISABLED_SUFFIX) else "active"
        rows.append(
            {
                "agent": name,
                "quality_tier": quality_tier,
                "quality_tier_source": quality_tier_source,
                "status": status_text,
                "status_label": (
                    "[yellow]disabled[/yellow]"
                    if status_text == "disabled"
                    else "[green]active[/green]"
                ),
                "quality_tier_label": quality_tier_label,
            }
        )
    if as_json:
        _print_json(
            {
                "agents": [
                    {
                        "agent": row["agent"],
                        "quality_tier": row["quality_tier"],
                        "quality_tier_source": row["quality_tier_source"],
                        "status": row["status"],
                    }
                    for row in rows
                ],
                "deployed": True,
                "project_root": str(project_root),
                "tool": tool.value,
            }
        )
        return
    table = Table(title=f"Deployed agents — {project_root} ({tool.value})")
    table.add_column("Agent", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Quality tier", style="white")
    for row in rows:
        table.add_row(row["agent"], row["status_label"], row["quality_tier_label"])
    console.print(table)


def _deployed_quality_tier(project_root: Path, tool: Tool) -> str:
    rules_path = project_root / get_target_adapter(tool).destination("rules")
    if not rules_path.exists():
        return ""
    for line in rules_path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("quality-tier:"):
            continue
        tier_words = line.split(":", 1)[1].strip().split(maxsplit=1)
        if not tier_words:
            continue
        quality_tier = tier_words[0].lower()
        if quality_tier in QUALITY_TIER_VALUES:
            return quality_tier
    return ""


def _agent_quality_tier_details(
    agent_name: str,
    agent_overrides: Mapping[str, str],
    default_quality_tier: str,
) -> tuple[str, str, str]:
    override = agent_overrides.get(agent_name)
    if override is not None:
        return override, "override", f"[magenta]{override}[/magenta] (override)"
    if default_quality_tier:
        return default_quality_tier, "default", default_quality_tier
    return "", "", ""


@app.command()
def artifacts(
    target_dir: str | None = _target_dir_option,
    query: str | None = typer.Option(
        None,
        "--query",
        "-q",
        help="Filter artifacts by path or file content",
    ),
    as_json: bool = _json_option,
) -> None:
    """List story, plan, research, audit, review, and incident artifacts."""
    project_root = _resolve_project_root(target_dir)
    artifact_rows = collect_artifact_rows(project_root, query)
    if as_json:
        _print_json(
            {
                "artifacts": [
                    {"path": path, "status": status, "type": kind}
                    for kind, path, status in artifact_rows
                ],
                "count": len(artifact_rows),
                "project_root": str(project_root),
                "query": query,
            }
        )
        return
    if not artifact_rows:
        if query:
            console.print(f"[yellow]No artifacts match query:[/yellow] {query}")
        else:
            console.print(f"[yellow]No artifacts found under {project_root}[/yellow]")
        return

    table = Table(title=f"Artifacts — {project_root}")
    table.add_column("Type", style="cyan")
    table.add_column("Path", style="green")
    table.add_column("Status", style="white")
    for kind, relative_path, status_text in artifact_rows:
        table.add_row(kind, relative_path, status_text)
    console.print(table)
    console.print(f"[dim]{len(artifact_rows)} artifact(s)[/dim]")


@app.command(name="artifact-policy")
def artifact_policy(
    policy: Annotated[
        ArtifactPolicy,
        typer.Argument(
            help=(
                "Artifact tracking policy: local ignores generated artifacts, shared removes "
                "the managed ignore block, status reports current policy"
            )
        ),
    ],
    target_dir: str | None = _target_dir_option,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would change without writing .gitignore"),
    ] = False,
) -> None:
    """Manage the target project's `.gitignore` policy for playbook artifacts."""
    project_root = _resolve_project_root(target_dir)
    gitignore_path = project_root / ".gitignore"
    if policy is ArtifactPolicy.status:
        console.print(artifact_policy_status(gitignore_path))
        return

    current = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
    updated = artifact_gitignore_content(current, policy)
    if updated == current:
        console.print(f"[dim]Artifact policy already {policy.value}[/dim]")
    else:
        action = "would update" if dry_run else "updated"
        console.print(f"[green]{action}[/green] {gitignore_path}")
        if not dry_run:
            write_text_safely(gitignore_path, updated, project_root)
    if policy is ArtifactPolicy.shared and any(
        line.strip() in ARTIFACT_IGNORE_LINES for line in updated.splitlines()
    ):
        console.print(
            "[yellow]note:[/yellow] artifact paths are still ignored by hand-written "
            ".gitignore lines outside the managed block — remove them manually if "
            "artifacts should be committed."
        )


@app.command()
def diff(
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
    exit_code_on_drift: bool = typer.Option(
        False,
        "--exit-code",
        help="Exit 1 when drift is detected. Off by default; useful in CI to gate "
        "merges on `.playbook-version` going stale.",
    ),
) -> None:
    """Show what changed between the playbook source and the deployed copy.

    Default exit code is always 0 (informational). Pass `--exit-code` to fail
    with 1 on drift, suitable for CI checks. Pass `--json` for machine-readable
    output with stable keys (drift, tool, sections[].title, sections[].location,
    sections[].changes[].file, sections[].changes[].status).
    """
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    try:
        report = compute_diff(source_root, project_root, tool)
    except ConfigError as exc:
        _exit_config_error(exc)

    if as_json:
        payload: dict[str, object] = {
            "drift": report.has_changes,
            "tool": tool.value,
            "sections": [
                {
                    "title": section.title,
                    "location": str(section.location),
                    "changes": [
                        {"file": filename, "status": _plain_markup(status)}
                        for filename, status in section.changes
                    ],
                }
                for section in report.sections
                if section.changes
            ],
        }
        _print_json(payload)
        if exit_code_on_drift and report.has_changes:
            raise typer.Exit(1)
        return

    for section in report.sections:
        _print_change_section(section.title, section.location, section.changes)
    if not report.has_changes:
        console.print("\n[green]Everything up to date.[/green]")
        return
    console.print(
        f"\n[dim]Run 'ai-playbook deploy --agent all --tool {tool.value}' to update.[/dim]"
    )
    if exit_code_on_drift:
        raise typer.Exit(1)


@app.command()
def disable(
    agent: str = typer.Argument(
        help="Agent(s) to disable — 'all' or comma-separated names e.g. xp-pair-programmer,planner",
    ),
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview which agents would be disabled without renaming any files",
    ),
) -> None:
    """Disable deployed agent(s) without removing them."""
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    agents_dir = get_agents_dir(project_root, tool)
    all_agents = _discover_configured_agents(source_root, project_root)
    names = _resolve_agent_names_or_exit(agent, all_agents, label="agent")

    console.print(f"\n[bold]Disabling agents[/bold] ({tool.value})\n")
    if dry_run:
        console.print("[yellow]Dry run — no files will be renamed[/yellow]\n")
    for name in names:
        path, is_disabled = find_deployed_agent(agents_dir, name)
        if path is None:
            console.print(f"  [yellow]not deployed[/yellow] {name}")
        elif is_disabled:
            console.print(f"  [dim]already disabled[/dim] {name}")
        elif dry_run:
            console.print(f"  [yellow]would disable[/yellow] {name}")
        else:
            disabled_path = path.parent / (path.name + DISABLED_SUFFIX)
            path.rename(disabled_path)
            console.print(f"  [yellow]disabled[/yellow] {name}")
    console.print(DONE_MESSAGE)
    console.print(f"[dim]Re-enable with: ai-playbook enable {agent} --tool {tool.value}[/dim]")


@app.command()
def enable(
    agent: str = typer.Argument(
        help="Agent(s) to enable — 'all' or comma-separated names e.g. xp-pair-programmer,planner",
    ),
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview which agents would be enabled without renaming any files",
    ),
) -> None:
    """Re-enable previously disabled agent(s)."""
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    agents_dir = get_agents_dir(project_root, tool)
    all_agents = _discover_configured_agents(source_root, project_root)
    names = _resolve_agent_names_or_exit(agent, all_agents, label="agent")

    console.print(f"\n[bold]Enabling agents[/bold] ({tool.value})\n")
    if dry_run:
        console.print("[yellow]Dry run — no files will be renamed[/yellow]\n")
    for name in names:
        path, is_disabled = find_deployed_agent(agents_dir, name)
        if path is None:
            hint = f"ai-playbook deploy --agent {name} --tool {tool.value}"
            console.print(f"  [yellow]not deployed[/yellow] {name} — run: {hint}")
        elif not is_disabled:
            console.print(f"  [dim]already active[/dim] {name}")
        elif dry_run:
            console.print(f"  [green]would enable[/green] {name}")
        else:
            active_path = agents_dir / f"{name}{AGENT_FILE_SUFFIX}"
            path.rename(active_path)
            console.print(f"  [green]enabled[/green] {name}")
    console.print("\n[bold green]Done.[/bold green]")


def _discover_configured_agents(source_root: Path, project_root: Path) -> dict[str, Path]:
    return {
        name: entry.src_path
        for name, entry in _discover_configured_agent_entries(source_root, project_root).items()
    }


def _discover_configured_agent_entries(
    source_root: Path, project_root: Path
) -> dict[str, DeployableFile]:
    packs = _load_pack_config_or_exit(project_root)
    discovered = discover_layered(source_root, packs)
    return {
        entry.relative.name.removesuffix(AGENT_FILE_SUFFIX): entry
        for entry in discovered.files
        if entry.relative.parts[0] == "agents"
    }


config_app = typer.Typer(
    name="config",
    help="Validate and inspect .ai-playbook.toml configuration",
    add_completion=False,
    no_args_is_help=True,
)
app.add_typer(config_app)


@config_app.command("validate")
def config_validate(
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
) -> None:
    """Validate .ai-playbook.toml, pack paths, pack metadata, overrides, and pack content."""
    project_root = _resolve_project_root(target_dir)
    report = _config_validation_report(project_root)
    errors_field = report["errors"]
    errors = errors_field if isinstance(errors_field, list) else []
    has_errors = bool(errors)
    if as_json:
        _print_json(report)
        if has_errors:
            raise typer.Exit(1)
        return

    table = Table(title=f"Config validation — {project_root}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    table.add_row("Status", "[red]invalid[/red]" if has_errors else "[green]valid[/green]")
    config_path_value = str(report["config_path"]) if report["config_present"] else "missing"
    table.add_row("Config file", config_path_value)
    packs_report = report["packs"]
    packs_count = len(packs_report) if isinstance(packs_report, list) else 0
    table.add_row("Packs", str(packs_count))
    model_tiers = report["model_tiers"]
    if isinstance(model_tiers, dict):
        table.add_row(
            "Model tiers",
            ", ".join(f"{name}={value}" for name, value in model_tiers.items() if value is not None)
            or "configured, but empty",
        )
    else:
        table.add_row("Model tiers", "not configured")
    overrides_report = report["quality_tier_overrides"]
    overrides_count = len(overrides_report) if isinstance(overrides_report, dict) else 0
    table.add_row("Quality tier overrides", str(overrides_count))
    console.print(table)
    warnings = report["warnings"]
    if isinstance(warnings, list) and warnings:
        _print_problem_list("Warnings", "yellow", "⚠", [str(warning) for warning in warnings])
    if has_errors:
        _print_problem_list("Errors", "red", "✗", [str(error) for error in errors])
        raise typer.Exit(1)


def _config_validation_report(project_root: Path) -> dict[str, object]:
    config_path = project_root / PACK_CONFIG_FILE
    source_root = get_source_root()
    try:
        packs = load_pack_config(project_root)
        model_tiers = load_model_tier_config(project_root)
        quality_tiers = load_quality_tier_config(project_root)
        discovered = discover_layered(source_root, packs)
    except ConfigError as exc:
        return {
            "config_path": str(config_path),
            "config_present": config_path.exists(),
            "model_tiers": None,
            "packs": [],
            "project_root": str(project_root),
            "quality_tier_overrides": {},
            "valid": False,
            "errors": [str(exc)],
            "warnings": [],
        }
    agent_names = {
        entry.relative.name.removesuffix(AGENT_FILE_SUFFIX)
        for entry in discovered.files
        if entry.relative.parts[0] == "agents"
    }

    warnings: list[str] = []
    if model_tiers is not None:
        missing_model_tiers = [
            tier_name
            for tier_name, tier_value in {
                "advisor": model_tiers.advisor,
                "executor": model_tiers.executor,
            }.items()
            if tier_value is None
        ]
        if missing_model_tiers:
            warnings.append("Model tier mapping incomplete: " + ", ".join(missing_model_tiers))

    unknown_overrides = sorted(set(quality_tiers.agent_overrides) - agent_names)
    if unknown_overrides:
        warnings.append(
            "Quality tier override names unknown agent(s): " + ", ".join(unknown_overrides)
        )

    # Pack content findings are errors here (pre-deploy gate); doctor reports
    # the same findings as warnings (deployed-state health).
    errors = validate_pack_content(packs)

    return {
        "config_path": str(config_path),
        "config_present": config_path.exists(),
        "model_tiers": (
            None
            if model_tiers is None
            else {"advisor": model_tiers.advisor, "executor": model_tiers.executor}
        ),
        "packs": [
            {
                "max_playbook_version": (
                    pack.metadata.max_playbook_version if pack.metadata else None
                ),
                "min_playbook_version": (
                    pack.metadata.min_playbook_version if pack.metadata else None
                ),
                "name": pack.metadata.name if pack.metadata else pack.root.name,
                "origin": pack.origin,
                "path": str(pack.root),
                "version": pack.metadata.version if pack.metadata else None,
            }
            for pack in packs
        ],
        "project_root": str(project_root),
        "quality_tier_overrides": dict(quality_tiers.agent_overrides),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }


telemetry_app = typer.Typer(
    name="telemetry",
    help="Manage the Claude Stop-hook that appends session telemetry to .claude/usage.jsonl",
    add_completion=False,
    no_args_is_help=True,
)
app.add_typer(telemetry_app)


@telemetry_app.command("enable")
def telemetry_enable(
    target_dir: str | None = _target_dir_option,
) -> None:
    """Configure the Claude Stop hook in .claude/settings.json (idempotent)."""
    project_root = _resolve_project_root(target_dir)
    console.print(
        f"\n[bold]Telemetry → enable[/bold] ({project_root})\n"
        f"  {deploy_telemetry_hook_config(project_root, Tool.claude, dry_run=False)}"
    )
    if not (project_root / "harness" / "telemetry.sh").exists():
        console.print(
            "  [yellow]warning[/yellow] harness/telemetry.sh not deployed — "
            "run [bold]ai-playbook deploy --tool claude[/bold] to ship the hook script."
        )


@telemetry_app.command("disable")
def telemetry_disable(
    target_dir: str | None = _target_dir_option,
) -> None:
    """Remove the AI Playbook Stop hook from .claude/settings.json."""
    project_root = _resolve_project_root(target_dir)
    console.print(
        f"\n[bold]Telemetry → disable[/bold] ({project_root})\n"
        f"  {disable_telemetry_hook(project_root)}"
    )


@telemetry_app.command("status")
def telemetry_status_cmd(
    target_dir: str | None = _target_dir_option,
) -> None:
    """Show whether the telemetry Stop hook is configured and where logs are written."""
    project_root = _resolve_project_root(target_dir)
    info = telemetry_status(project_root)
    table = Table(title=f"Telemetry — {project_root}")
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")
    hook_label = (
        "[green]configured[/green]" if info.hook_configured else "[yellow]not configured[/yellow]"
    )
    settings_label = (
        str(info.settings_path.relative_to(project_root))
        if info.settings_exists
        else f"{info.settings_path.relative_to(project_root)} (missing)"
    )
    harness_label = (
        "[green]present[/green]"
        if info.harness_script_present
        else "[yellow]missing[/yellow] — run [bold]ai-playbook deploy --tool claude[/bold]"
    )
    if info.usage_log_exists:
        usage_label = (
            f"{info.usage_log_path.relative_to(project_root)} ({info.usage_log_bytes} bytes)"
        )
    else:
        usage_label = f"{info.usage_log_path.relative_to(project_root)} (no sessions logged yet)"
    table.add_row("Stop hook", hook_label)
    table.add_row("settings.json", settings_label)
    table.add_row("harness/telemetry.sh", harness_label)
    table.add_row("usage log", usage_label)
    console.print(table)


@app.command(name="upgrade-check")
def upgrade_check(
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
) -> None:
    """Report whether the deployed playbook is up to date with the source.

    Exit codes:
      0 — up to date
            1 — drift or tool mismatch detected; redeploy or use the recorded tool
      2 — never deployed in this project (no .playbook-version)
    """
    project_root = _resolve_project_root(target_dir)
    try:
        report = check_upgrade(project_root, tool)
    except ConfigError as exc:
        _exit_config_error(exc)
    if as_json:
        _render_upgrade_json(report)
    else:
        _render_upgrade_report(report)
    if report.status is UpgradeStatus.up_to_date:
        raise typer.Exit(0)
    if report.status in (UpgradeStatus.drift, UpgradeStatus.tool_mismatch):
        raise typer.Exit(1)
    raise typer.Exit(2)


def _render_upgrade_report(report: UpgradeReport) -> None:
    title = f"Upgrade check — {report.project_root} (tool: {report.tool.value})"
    table = Table(title=title)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Status", _upgrade_status_label(report.status))
    table.add_row("Playbook (current)", report.current_playbook_version or "[dim]unknown[/dim]")
    if report.deployed_at:
        table.add_row("Last deployed", report.deployed_at)
    if report.deployed_tool:
        table.add_row("Last deployed --tool", report.deployed_tool)
    if report.deployed_language and report.deployed_language != "all":
        table.add_row("Last deployed --language", report.deployed_language)
    if report.status is not UpgradeStatus.not_deployed:
        table.add_row(
            "Fingerprint (deployed)",
            report.deployed_fingerprint or "[yellow]missing[/yellow]",
        )
        table.add_row("Fingerprint (source)", report.source_fingerprint or "")
    if report.deployed_packs:
        table.add_row("Packs", ", ".join(report.deployed_packs))

    console.print(table)
    for note in report.notes:
        console.print(f"[yellow]{note}[/yellow]")
    _print_upgrade_next_step(report)


def _render_upgrade_json(report: UpgradeReport) -> None:
    _print_json(
        {
            "current_playbook_version": report.current_playbook_version,
            "deployed_at": report.deployed_at,
            "deployed_fingerprint": report.deployed_fingerprint,
            "deployed_language": report.deployed_language,
            "deployed_packs": report.deployed_packs,
            "deployed_tool": report.deployed_tool,
            "notes": report.notes,
            "project_root": str(report.project_root),
            "source_fingerprint": report.source_fingerprint,
            "status": report.status.value,
            "tool": report.tool.value,
        }
    )


def _upgrade_status_label(status: UpgradeStatus) -> str:
    match status:
        case UpgradeStatus.up_to_date:
            return "[green]up to date[/green]"
        case UpgradeStatus.drift:
            return "[yellow]drift[/yellow] — source has changed since last deploy"
        case UpgradeStatus.tool_mismatch:
            return "[yellow]tool mismatch[/yellow] — requested tool differs from last deploy"
        case UpgradeStatus.not_deployed:
            return "[yellow]not deployed[/yellow]"


def _print_upgrade_next_step(report: UpgradeReport) -> None:
    if report.status is UpgradeStatus.up_to_date:
        return
    if report.status is UpgradeStatus.tool_mismatch and report.deployed_tool:
        console.print(
            f"\n[bold]Next:[/bold] [cyan]ai-playbook upgrade-check --tool "
            f"{report.deployed_tool}[/cyan]"
            f" (or deploy --tool {report.tool.value} if intentional)"
        )
        return
    cmd = f"ai-playbook deploy --tool {report.tool.value}"
    console.print(f"\n[bold]Next:[/bold] [cyan]{cmd}[/cyan]")


@app.command()
def deploy(
    agent: str = typer.Option(
        "all",
        "--agent",
        "-a",
        help=(
            "Agent(s) to deploy. Use 'all' or comma-separated names e.g. "
            "story-refiner,xp-pair-programmer"
        ),
    ),
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview what would be deployed without making changes",
    ),
    no_rules: bool = typer.Option(
        False,
        "--no-rules",
        help=(
            "Skip deploying the rules file "
            "(CLAUDE.md / copilot-instructions.md / ai-playbook.mdc / rules.md)"
        ),
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        "-l",
        help=(
            "Deploy only this active language's KB files (currently: python). "
            "Omit for all languages."
        ),
    ),
    no_mcp: bool = typer.Option(
        False,
        "--no-mcp",
        help="Skip deploying MCP server configuration (Atlassian for Jira)",
    ),
    no_harness: bool = typer.Option(
        False,
        "--no-harness",
        help="Skip deploying starter harness files (Makefile, hooks, CI workflow)",
    ),
    prune: bool = typer.Option(
        False,
        "--prune",
        help="After deploy, remove orphaned files in the deployed dirs that have no "
        "corresponding source file (e.g. left over from a renamed/removed agent). "
        "Preserves `*.disabled` files. Confirms before deleting unless --yes.",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        "-y",
        help="Skip the prune confirmation prompt. No effect without --prune.",
    ),
    harness_force: bool = typer.Option(
        False,
        "--harness-force",
        help="Overwrite existing harness files (Makefile, hooks, CI workflow). "
        "Off by default to protect adopter edits.",
    ),
) -> None:
    """Deploy agents, knowledge base, and rules to a project directory."""
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    target = get_target_adapter(tool)
    language_filter = _validate_language_filter(language)
    skip_files = language_skip_files(language_filter)
    rewrite = path_rewrite(target.destinations)
    packs = _load_pack_config_or_exit(project_root)
    discovered = discover_layered(source_root, packs)

    # All discoverable agents — core + packs — keyed by agent name for --agent filter.
    all_agents: dict[str, Path] = {
        f.relative.name.removesuffix(AGENT_FILE_SUFFIX): f.src_path
        for f in discovered.files
        if f.relative.parts[0] == "agents"
    }
    if not all_agents:
        error_console.print(
            f"[red]Error:[/red] No agents found in {source_root / 'agents'}. "
            "Run [bold]ai-playbook list[/bold] to inspect configured sources."
        )
        raise typer.Exit(1)
    agents_to_deploy = _resolve_agent_names_or_exit(agent, all_agents)

    if dry_run:
        console.print("[yellow]Dry run — no files will be written[/yellow]\n")

    backup_path = _backup_existing_deployment(project_root, tool, dry_run)

    console.print(f"\n[bold]Deploying to:[/bold] {project_root} ([cyan]{tool.value}[/cyan])\n")

    if discovered.overrides:
        console.print("[bold yellow]Pack overrides:[/bold yellow]")
        for override in discovered.overrides:
            console.print(
                f"  [yellow]{override.new_origin}[/yellow] overrides "
                f"[dim]{override.previous_origin}[/dim] at {override.relative}"
            )
        console.print()

    _print_pack_metadata(packs)

    try:
        _deploy_layered(
            discovered.files,
            agent_names=set(agents_to_deploy),
            project_root=project_root,
            target=target,
            dry_run=dry_run,
            rewrite=rewrite,
            skip_kb_files=skip_files,
            language_filter=language_filter,
        )
        _deploy_rules(source_root, project_root, target, dry_run, no_rules, rewrite)
        _deploy_commands(
            source_root,
            project_root,
            target,
            dry_run,
            set(agents_to_deploy),
            set(all_agents),
            rewrite=rewrite,
        )
        _deploy_mcp(project_root, target, dry_run, no_mcp)
        _deploy_harness(source_root, project_root, target, dry_run, no_harness, harness_force)
        _prune_deployment(
            project_root,
            source_root,
            tool,
            dry_run,
            prune,
            skip_files,
            discovered_files=discovered.files,
            yes=yes,
            current_pack_names={p.metadata.name for p in packs if p.metadata is not None},
        )
        _write_deploy_version(
            project_root,
            source_root,
            tool,
            dry_run,
            language_filter,
            skip_files,
            discovered_files=discovered.files,
            packs=packs,
        )
    except typer.Exit:
        raise
    except (DeployStepError, UnsafeDestinationError, WriteAccessError) as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        _print_rollback_hint(backup_path, tool, project_root)
        raise typer.Exit(1) from None
    except Exception:
        # Unexpected mid-deploy failure: the backup still fixes it, so print
        # the hint before the traceback surfaces. Re-raise rather than exit —
        # an unknown error must stay loud, not become a tidy exit code.
        _print_rollback_hint(backup_path, tool, project_root)
        raise

    console.print(DONE_MESSAGE)


@app.command()
def doctor(
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    as_json: bool = _json_option,
    strict: bool = typer.Option(
        False,
        "--strict",
        help="Use a 3-state exit code suitable for CI: 0=healthy, 1=issues, 2=not deployed. "
        "Default keeps the legacy contract (0 except when not deployed) so existing pipelines "
        "are unaffected.",
    ),
) -> None:
    """Check deployment health — staleness, missing files, disabled agents.

    Default exit codes preserve existing CI behaviour: 0 unless nothing is
    deployed (then 1). Pass `--strict` to opt into the 0/1/2 contract that
    distinguishes healthy from issues-found.
    """
    source_root = get_source_root()
    project_root = _resolve_project_root(target_dir)
    try:
        report = DoctorService().check(
            source_root=source_root, project_root=project_root, tool=tool
        )
    except DeploymentNotFoundError as exc:
        if as_json:
            _print_json(
                {
                    "agents_dir": str(exc.agents_dir),
                    "healthy": False,
                    "issues": [f"Nothing deployed at {exc.agents_dir}"],
                    "project_root": str(project_root),
                    "status": "not_deployed",
                    "tool": tool.value,
                    "warnings": [],
                }
            )
            raise typer.Exit(2 if strict else 1) from None
        error_console.print(f"[red]Nothing deployed[/red] at {exc.agents_dir}")
        error_console.print(f"Run: ai-playbook deploy --agent all --tool {tool.value}")
        raise typer.Exit(2 if strict else 1) from None

    if as_json:
        _render_doctor_json(report)
    else:
        _print_doctor_report(report.project_root, report.tool, report.issues, report.warnings)
    if strict and (report.issues or report.warnings):
        raise typer.Exit(1)


def _render_doctor_json(report: DoctorReport) -> None:
    _print_json(
        {
            "healthy": not report.issues and not report.warnings,
            "issues": [_plain_markup(issue) for issue in report.issues],
            "project_root": str(report.project_root),
            "status": "healthy" if not report.issues and not report.warnings else "attention",
            "tool": report.tool.value,
            "warnings": [_plain_markup(warning) for warning in report.warnings],
        }
    )


@app.command()
def rollback(
    tool: Tool = _tool_option,
    target_dir: str | None = _target_dir_option,
    force: bool = typer.Option(
        False,
        "--yes",
        "-y",
        "--force",
        "-f",
        help="Skip confirmation prompt. `--yes`/`-y` matches the deploy command's flag; "
        "`--force`/`-f` is kept as an alias for backward compatibility.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Show which backup would be restored without restoring anything",
    ),
) -> None:
    """Restore the previous deployment from backup."""
    project_root = _resolve_project_root(target_dir)
    backup_dir = project_root / BACKUP_DIR

    if not backup_dir.exists():
        error_console.print("[red]No backups found.[/red] Nothing to roll back.")
        raise typer.Exit(1)

    if not any(d.is_dir() for d in backup_dir.iterdir()):
        error_console.print("[red]No backups found.[/red] Nothing to roll back.")
        raise typer.Exit(1)

    latest = latest_backup_for_tool(project_root, tool)
    if latest is None:
        error_console.print(f"[red]No {tool.value} backups found.[/red] Nothing to roll back.")
        raise typer.Exit(1)

    console.print(f"\n[bold]Will restore from:[/bold] {latest.relative_to(project_root)}")
    console.print(
        "[dim]This will overwrite backed-up overlay files; MCP and harness files are not "
        "restored.[/dim]\n"
    )

    if dry_run:
        console.print("[yellow]Dry run — nothing restored.[/yellow]")
        return

    if not force:
        confirmed = typer.confirm("Proceed with rollback?")
        if not confirmed:
            console.print("[yellow]Aborted.[/yellow]")
            raise typer.Exit(0)

    restore_backup(project_root, tool, latest)
    console.print("[bold green]Rollback complete.[/bold green]")
    console.print(f"[dim]Run 'ai-playbook doctor --tool {tool.value}' to verify.[/dim]")


if __name__ == "__main__":  # pragma: no cover
    app()
