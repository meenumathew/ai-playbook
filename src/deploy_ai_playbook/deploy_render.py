"""Deploy/prune presentation for the `deploy` command.

Extracted from `cli.py` — this is top-layer presentation code (prints via the
shared consoles, raises `typer.Exit`), not service logic. `cli.py` imports the
public functions under their old underscore aliases so the call sites and the
`tests/acceptance/test_deploy.py` monkeypatch seam (`cli._deploy_layered`)
keep working unchanged.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path

import typer

from deploy_ai_playbook.backup import backup_deployed_files, write_version_file
from deploy_ai_playbook.config import load_issue_tracker_provider
from deploy_ai_playbook.console import console, error_console
from deploy_ai_playbook.discovery import OVERLAY_DIRS, OVERLAY_TITLES, DeployableFile
from deploy_ai_playbook.errors import AIPlaybookError
from deploy_ai_playbook.fs import (
    copy_commands_directory,
    copy_file,
    prune_orphaned_files,
)
from deploy_ai_playbook.mcp import deploy_mcp_config
from deploy_ai_playbook.paths import RULES_SOURCE_FILE, VERSION_FILE, Tool
from deploy_ai_playbook.safety import (
    UnsafeDestinationError,
    WriteAccessError,
    assert_safe_destination,
)
from deploy_ai_playbook.services.deploy import (
    agent_filtered_out,
    agent_model_tier_transform,
    group_deployable_files_by_overlay,
    iter_harness_files,
)
from deploy_ai_playbook.targets import TargetAdapter
from deploy_ai_playbook.telemetry import deploy_telemetry_hook_config
from deploy_ai_playbook.upgrade import read_version_file


class DeployStepError(RuntimeError, AIPlaybookError):
    """Raised when a deploy sub-step reports an actionable failure status."""


def _previously_deployed_pack_names(project_root: Path) -> set[str]:
    """Pack names recorded by the last deploy. Empty when no version file or no packs."""
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None:
        return set()
    # Pack specs are stored as "name@version"; we only need the name.
    return {spec.split("@", 1)[0].strip() for spec in parsed.packs if spec}


def backup_existing_deployment(project_root: Path, tool: Tool, dry_run: bool) -> Path | None:
    if dry_run:
        return None
    try:
        backup_path = backup_deployed_files(project_root, tool)
    except (UnsafeDestinationError, WriteAccessError, OSError) as exc:
        reason = getattr(exc, "strerror", None) or str(exc) or exc.__class__.__name__
        error_console.print(f"[red]Error:[/red] {reason}")
        raise typer.Exit(1) from None
    if backup_path:
        console.print(f"[dim]Backup saved to {backup_path.relative_to(project_root)}[/dim]")
    return backup_path


def print_rollback_hint(backup_path: Path | None, tool: Tool, project_root: Path) -> None:
    """Point a failed deploy at its backup — the fix is the same whatever broke."""
    if backup_path is None:
        return
    error_console.print(
        "[yellow]Deploy failed after creating a backup.[/yellow] "
        f"Run [bold]ai-playbook rollback --tool {tool.value} "
        f"-t {project_root} --yes[/bold] "
        f"to restore {backup_path.relative_to(project_root)}."
    )


def deploy_layered(
    discovered_files: list[DeployableFile],
    agent_names: set[str],
    project_root: Path,
    target: TargetAdapter,
    dry_run: bool,
    rewrite: dict[str, str],
    skip_kb_files: set[str],
    language_filter: str | None,
) -> None:
    """Deploy the merged core+pack files, grouped by overlay dir for header continuity.

    `discovered_files` is a list of `discovery.DeployableFile`. Agents are
    filtered to `agent_names` (the resolved --agent selection); other overlay
    dirs deploy in full. Pack files inherit the same filtering rules as core
    (skip_kb_files for the KB language filter).

    Deployed agent frontmatter also gets the model-tier materialization
    transform (claude only — see `services.deploy.agent_model_tier_transform`);
    notes about skipped/unmapped tiers print once, before the Agents section.
    """
    files_by_overlay = group_deployable_files_by_overlay(discovered_files)
    agent_transform, notes = agent_model_tier_transform(target.tool, project_root)
    for note in notes:
        console.print(f"[dim]{note}[/dim]")

    for overlay_dir in OVERLAY_DIRS:
        _deploy_overlay_files(
            overlay_dir=overlay_dir,
            overlay_files=files_by_overlay[overlay_dir],
            project_root=project_root,
            target=target,
            dry_run=dry_run,
            rewrite=rewrite,
            agent_names=agent_names,
            skip_kb_files=skip_kb_files,
            language_filter=language_filter,
            agent_transform=agent_transform if overlay_dir == "agents" else None,
        )


def _deploy_overlay_files(
    overlay_dir: str,
    overlay_files: list[DeployableFile],
    project_root: Path,
    target: TargetAdapter,
    dry_run: bool,
    rewrite: dict[str, str],
    agent_names: set[str],
    skip_kb_files: set[str],
    language_filter: str | None,
    agent_transform: Callable[[str], str] | None = None,
) -> None:
    if not overlay_files:
        return
    dst_dir = project_root / target.destination(overlay_dir)
    console.print(f"\n[bold]{OVERLAY_TITLES[overlay_dir]} →[/bold] {dst_dir}")
    if overlay_dir == "knowledge-base" and language_filter:
        console.print(f"  [dim]Language filter: {language_filter} only[/dim]")
    for entry in sorted(overlay_files, key=lambda f: f.relative):
        _deploy_overlay_file(
            entry=entry,
            overlay_dir=overlay_dir,
            dst_dir=dst_dir,
            project_root=project_root,
            dry_run=dry_run,
            rewrite=rewrite,
            agent_names=agent_names,
            skip_kb_files=skip_kb_files,
            transform=agent_transform,
        )


def _deploy_overlay_file(
    entry: DeployableFile,
    overlay_dir: str,
    dst_dir: Path,
    project_root: Path,
    dry_run: bool,
    rewrite: dict[str, str],
    agent_names: set[str],
    skip_kb_files: set[str],
    transform: Callable[[str], str] | None = None,
) -> None:
    relative_inside = entry.relative.relative_to(overlay_dir)
    if agent_filtered_out(entry, overlay_dir, agent_names):
        return
    if overlay_dir == "knowledge-base" and str(relative_inside) in skip_kb_files:
        console.print(f"  [dim]skipped[/dim] {relative_inside}")
        return
    status = copy_file(
        entry.src_path,
        dst_dir / relative_inside,
        dry_run,
        rewrite=rewrite,
        safe_root=project_root,
        transform=transform,
    )
    console.print(f"  {status} {relative_inside}")


def deploy_rules(
    source_root: Path,
    project_root: Path,
    target: TargetAdapter,
    dry_run: bool,
    no_rules: bool,
    rewrite: dict[str, str],
) -> None:
    rules_src = source_root / RULES_SOURCE_FILE
    if no_rules or not rules_src.exists():
        return
    rules_dst = project_root / target.destination("rules")
    status = copy_file(rules_src, rules_dst, dry_run, rewrite=rewrite, safe_root=project_root)
    console.print(f"\n[bold]Rules →[/bold] {rules_dst}")
    console.print(f"  {status} {rules_dst.name}")


def deploy_commands(
    source_root: Path,
    project_root: Path,
    target: TargetAdapter,
    dry_run: bool,
    agent_names: set[str],
    all_agent_names: set[str],
    rewrite: dict[str, str] | None = None,
) -> None:
    commands_src = source_root / "commands"
    commands_destination = target.optional_destination("commands")
    if not commands_src.exists() or not target.supports_commands or commands_destination is None:
        return
    commands_dest = project_root / commands_destination
    console.print(f"\n[bold]Commands →[/bold] {commands_dest}")
    for name, status in copy_commands_directory(
        commands_src,
        commands_dest,
        target.tool,
        dry_run,
        command_names=agent_names,
        known_agent_names=all_agent_names,
        safe_root=project_root,
        rewrite=rewrite,
    ):
        console.print(f"  {status} {name}")


def deploy_mcp(project_root: Path, target: TargetAdapter, dry_run: bool, no_mcp: bool) -> None:
    if no_mcp:
        return
    provider = load_issue_tracker_provider(project_root)
    mcp_path = target.mcp_config.path
    console.print(f"\n[bold]MCP →[/bold] {project_root / mcp_path}")
    if provider != "jira":
        # PM-tool agnosticism: only an explicit jira provider gets the
        # Atlassian MCP pushed into the project. Everything else is the
        # adopter's choice (docs/how-to/setup-issue-tracker.md).
        reason = (
            f"provider '{provider}' configures its own MCP"
            if provider is not None
            else 'no issue-tracker provider configured (set provider = "jira" to auto-configure)'
        )
        console.print(f"  [dim]skipped[/dim] {reason}")
        return
    mcp_status = deploy_mcp_config(project_root, target.tool, dry_run)
    console.print(f"  {mcp_status} atlassian")
    _raise_on_error_status(mcp_status)


def deploy_harness(
    source_root: Path,
    project_root: Path,
    target: TargetAdapter,
    dry_run: bool,
    no_harness: bool,
    force: bool = False,
) -> None:
    if no_harness:
        return
    harness_dir = source_root / "harness"
    if not harness_dir.exists():
        return
    console.print("\n[bold]Harness →[/bold]")
    for src_file, dst_rel, dst_file in iter_harness_files(harness_dir, project_root):
        console.print(
            _deploy_harness_file(src_file, dst_rel, dst_file, project_root, dry_run, force)
        )
    if target.tool is Tool.claude:
        telemetry_status = deploy_telemetry_hook_config(project_root, target.tool, dry_run)
        console.print(f"  {telemetry_status}")
        _raise_on_error_status(telemetry_status)


def _raise_on_error_status(status: str) -> None:
    if "[red]" not in status:
        return
    raise DeployStepError(_strip_rich_markup(status))


def _strip_rich_markup(status: str) -> str:
    return re.sub(r"\[[^\]]+\]", "", status)


def _deploy_harness_file(
    src_file: Path,
    dst_rel: str,
    dst_file: Path,
    project_root: Path,
    dry_run: bool,
    force: bool = False,
) -> str:
    """Copy one harness file. Existing files are kept unless `force` is set.

    The `kept` message is explicit so adopters can tell whether their local edits
    survived a redeploy. `--harness-force` overwrites — useful when the upstream
    fixes a bug in `telemetry.sh` or the CI workflow.
    """
    assert_safe_destination(dst_file, project_root)
    exists = dst_file.exists()
    if exists and not force:
        status = "exists, would keep" if dry_run else "exists, kept"
        return f"  [dim]{status}[/dim] {dst_rel} [dim](use --harness-force to overwrite)[/dim]"
    if dry_run:
        verb = "would overwrite" if exists else "would copy"
        return f"  [yellow]{verb}[/yellow] {dst_rel}"
    try:
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        dst_file.write_text(src_file.read_text(encoding="utf-8"), encoding="utf-8")
        if dst_file.suffix == ".sh":
            dst_file.chmod(0o755)
    except OSError as exc:
        raise WriteAccessError(
            f"Cannot deploy harness file {dst_file}: {exc.strerror or exc.__class__.__name__}"
        ) from exc
    verb = "overwrote" if exists else "copied"
    return f"  [green]{verb}[/green] {dst_rel}"


def prune_deployment(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    dry_run: bool,
    prune: bool,
    skip_files: set[str],
    discovered_files: list,
    yes: bool = False,
    current_pack_names: set[str] | None = None,
) -> None:
    """Remove orphaned files left behind by removed agents or removed packs.

    Two-stage flow on a real run:
      1. Compute would-prune set in dry-run mode.
      2. Show the user, surface a removed-packs warning when relevant, and
         require explicit confirmation (skipped with `--yes` or `--dry-run`).
      3. Apply the deletion.

    The removed-packs warning compares pack names recorded in `.playbook-version`
    against `current_pack_names` (loaded from `.ai-playbook.toml`). When a pack
    has been dropped from the config, its files become orphans — adopters
    should know that's *why* before confirming.
    """
    if not prune:
        return
    preview = prune_orphaned_files(
        project_root,
        source_root,
        tool,
        True,  # dry_run preview pass — never delete here
        discovered_files,
        skip_files=skip_files,
    )
    if not preview:
        return

    console.print("\n[bold]Prune →[/bold]")
    for path, _status in preview:
        verb = "would prune" if dry_run else "will prune"
        console.print(f"  [yellow]{verb}[/yellow] {path}")

    removed_packs = _previously_deployed_pack_names(project_root) - (current_pack_names or set())
    if removed_packs:
        console.print(
            "  [bold yellow]Note:[/bold yellow] some files came from packs no longer in "
            f".ai-playbook.toml: {sorted(removed_packs)}. "
            "If you didn't mean to remove them, restore the pack entry and re-run."
        )

    if dry_run:
        return
    if not yes:
        confirmed = typer.confirm(f"Delete {len(preview)} file(s)?", default=False)
        if not confirmed:
            console.print("[yellow]Prune aborted — no files deleted.[/yellow]")
            return

    pruned = prune_orphaned_files(
        project_root,
        source_root,
        tool,
        False,
        discovered_files,
        skip_files=skip_files,
    )
    for path, status in pruned:
        console.print(f"  {status} {path}")


def write_deploy_version(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    dry_run: bool,
    language_filter: str | None,
    skip_files: set[str],
    discovered_files: list | None = None,
    packs: list | None = None,
) -> None:
    status = write_version_file(
        project_root,
        source_root,
        tool,
        dry_run,
        language_filter,
        skip_files=skip_files,
        discovered_files=discovered_files,
        packs=packs,
    )
    console.print(f"\n[bold]Version →[/bold] {project_root / VERSION_FILE}")
    console.print(f"  {status} {VERSION_FILE}")


def print_pack_metadata(packs: list) -> None:
    if not packs:
        return
    console.print("[bold]Pack metadata:[/bold]")
    for pack in packs:
        metadata = pack.metadata
        if metadata is None:
            continue
        version = metadata.version or "unversioned"
        console.print(f"  {metadata.name} {version}")
    console.print()
