"""Backup, restore, and version-file helpers for the deploy CLI.

Backups are created before every non-dry-run deploy so that a redeploy gone
wrong can be rolled back. The backup directory name embeds a microsecond-
precision timestamp (plus a numeric suffix on collision) so that rapid
back-to-back deploys do not clobber each other.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from deploy_ai_playbook.config import load_pack_config
from deploy_ai_playbook.discovery import discover_layered
from deploy_ai_playbook.fs import assert_safe_path, assert_safe_tree, compute_source_fingerprint
from deploy_ai_playbook.paths import BACKUP_DIR, VERSION_FILE, Tool
from deploy_ai_playbook.targets import get_target_adapter

MAX_BACKUPS = 5
BACKUP_METADATA_FILE = ".playbook-backup-metadata"


@dataclass(frozen=True, slots=True)
class RestoreTarget:
    key: str
    staged: Path
    destination: Path
    is_dir: bool


def write_version_file(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    dry_run: bool,
    language: str | None = None,
    skip_files: set[str] | None = None,
    discovered_files: list | None = None,
    packs: list | None = None,
) -> str:
    """Write a .playbook-version file to the project root. Returns status string."""
    if discovered_files is None:
        resolved_packs = packs if packs is not None else load_pack_config(project_root)
        discovered_files = discover_layered(source_root, resolved_packs).files
    fingerprint = compute_source_fingerprint(source_root, discovered_files, skip_files=skip_files)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    language_value = language or "all"
    content = (
        f"playbook-fingerprint: {fingerprint}\n"
        f"deployed-at: {timestamp}\n"
        f"tool: {tool.value}\n"
        f"language: {language_value}\n"
        f"{_pack_version_lines(packs)}"
    )
    dst = project_root / VERSION_FILE
    if dry_run:
        return "[yellow]would write[/yellow]"
    dst.write_text(content, encoding="utf-8")
    return "[green]written[/green]"


def _pack_version_lines(packs: list | None) -> str:
    if not packs:
        return ""
    lines: list[str] = []
    for pack in packs:
        metadata = pack.metadata
        if metadata is None:
            continue
        version = metadata.version or "unversioned"
        lines.append(f"pack: {metadata.name}@{version}\n")
    return "".join(lines)


# Backup flow keeps ordered filesystem branches together for rollback clarity.
def backup_deployed_files(project_root: Path, tool: Tool) -> Path | None:  # noqa: C901
    """Back up currently deployed files before overwriting.

    Returns the backup directory path, or None if nothing was deployed.
    """
    destinations = get_target_adapter(tool).destinations
    deployed_dirs: list[tuple[str, Path]] = []
    for key in ("agents", "knowledge-base", "skills", "templates"):
        d = project_root / destinations[key]
        assert_safe_path(d, project_root)
        if d.exists():
            assert_safe_tree(d, project_root)
            deployed_dirs.append((key, d))
    if "commands" in destinations:
        d = project_root / destinations["commands"]
        assert_safe_path(d, project_root)
        if d.exists():
            assert_safe_tree(d, project_root)
            deployed_dirs.append(("commands", d))
    rules_dst = project_root / destinations["rules"]
    assert_safe_path(rules_dst, project_root)
    has_rules = rules_dst.exists()

    if not deployed_dirs and not has_rules:
        return None

    # Microsecond precision so rapid redeploys (same-second) don't collide.
    created_at = datetime.now(UTC)
    timestamp = created_at.strftime("%Y%m%d-%H%M%S-%f")
    backup_root = project_root / BACKUP_DIR / timestamp
    assert_safe_path(backup_root, project_root)
    # If the same microsecond is hit twice (extremely rare), append a counter.
    # mkdir-and-retry rather than exists()-then-mkdir: leaves no window for a
    # concurrent process to claim the path between check and create.
    suffix = 0
    while True:
        try:
            backup_root.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            suffix += 1
            backup_root = project_root / BACKUP_DIR / f"{timestamp}-{suffix}"
            assert_safe_path(backup_root, project_root)

    for key, src_dir in deployed_dirs:
        dst_dir = backup_root / key
        shutil.copytree(src_dir, dst_dir)

    if has_rules:
        shutil.copy2(rules_dst, backup_root / rules_dst.name)

    version_file = project_root / VERSION_FILE
    assert_safe_path(version_file, project_root)
    if version_file.exists():
        shutil.copy2(version_file, backup_root / VERSION_FILE)

    _write_backup_metadata(backup_root, tool, created_at)
    _rotate_backups(project_root)
    return backup_root


def _write_backup_metadata(backup_root: Path, tool: Tool, created_at: datetime) -> None:
    """Record the tool a backup belongs to so rollback can select safely."""
    backup_root.joinpath(BACKUP_METADATA_FILE).write_text(
        f"tool: {tool.value}\ncreated-at: {created_at.strftime('%Y-%m-%dT%H:%M:%SZ')}\n",
        encoding="utf-8",
    )


def _read_metadata_tool(backup_root: Path) -> str | None:
    metadata_path = backup_root / BACKUP_METADATA_FILE
    if metadata_path.exists():
        tool = _read_tool_line(metadata_path)
        if tool is not None:
            return tool
    return _read_tool_line(backup_root / VERSION_FILE)


def _read_tool_line(path: Path) -> str | None:
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("tool:"):
            return line.split(":", 1)[1].strip()
    return None


def latest_backup_for_tool(project_root: Path, tool: Tool) -> Path | None:
    """Return the newest backup created for `tool`, ignoring other tool backups."""
    backup_dir = project_root / BACKUP_DIR
    if not backup_dir.exists():
        return None
    backups = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    for backup_root in backups:
        if _read_metadata_tool(backup_root) == tool.value:
            return backup_root
    return None


def _rotate_backups(project_root: Path) -> None:
    """Keep only the most recent MAX_BACKUPS backups, remove older ones.

    Failures to remove are surfaced on stderr rather than silently swallowed.
    The deploy itself still succeeds — rotation is housekeeping — but adopters
    need to know when `.playbook-backup/` is filling up (full disk, locked
    backup, permission change) so they can investigate before the next deploy.
    """
    backup_dir = project_root / BACKUP_DIR
    if not backup_dir.exists():
        return
    backups = sorted(
        [d for d in backup_dir.iterdir() if d.is_dir()],
        reverse=True,
    )
    backups_by_tool: dict[str | None, list[Path]] = {}
    for backup_root in backups:
        backups_by_tool.setdefault(_read_metadata_tool(backup_root), []).append(backup_root)

    for tool_backups in backups_by_tool.values():
        for old_backup in tool_backups[MAX_BACKUPS:]:
            try:
                shutil.rmtree(old_backup)
            except OSError as exc:
                print(
                    f"warning: failed to rotate old backup {old_backup}: "
                    f"{exc.strerror or exc.__class__.__name__}",
                    file=sys.stderr,
                )


def _stage_backup(backup_root: Path, staging: Path, destinations: Mapping[str, str]) -> str:
    """Copy backup contents into a staging directory. Returns the rules filename."""
    for key in ("agents", "knowledge-base", "skills", "templates"):
        backup_src = backup_root / key
        if backup_src.exists():
            assert_safe_tree(backup_src, backup_root)
            shutil.copytree(backup_src, staging / key)

    if "commands" in destinations:
        backup_src = backup_root / "commands"
        if backup_src.exists():
            assert_safe_tree(backup_src, backup_root)
            shutil.copytree(backup_src, staging / "commands")

    rules_name = Path(destinations["rules"]).name
    backup_rules = backup_root / rules_name
    if backup_rules.exists():
        assert_safe_path(backup_rules, backup_root)
        shutil.copy2(backup_rules, staging / rules_name)

    backup_version = backup_root / VERSION_FILE
    if backup_version.exists():
        assert_safe_path(backup_version, backup_root)
        shutil.copy2(backup_version, staging / VERSION_FILE)

    return rules_name


def _swap_staged(
    staging: Path, project_root: Path, destinations: Mapping[str, str], rules_name: str
) -> None:
    """Move staged files into their final deployment locations."""
    targets = _restore_targets(staging, project_root, destinations, rules_name)
    for target in targets:
        assert_safe_path(target.destination, project_root)
    rollback_root = staging / ".rollback-current"
    _snapshot_current_targets(targets, rollback_root)
    try:
        for target in targets:
            _replace_target(target)
    except Exception:
        _restore_current_targets(targets, rollback_root)
        raise
    finally:
        shutil.rmtree(rollback_root, ignore_errors=True)


def _restore_targets(
    staging: Path, project_root: Path, destinations: Mapping[str, str], rules_name: str
) -> list[RestoreTarget]:
    targets: list[RestoreTarget] = []
    for key in ("agents", "knowledge-base", "skills", "templates"):
        staged = staging / key
        if staged.exists():
            targets.append(
                RestoreTarget(
                    key=key,
                    staged=staged,
                    destination=project_root / destinations[key],
                    is_dir=True,
                )
            )

    if "commands" in destinations:
        staged = staging / "commands"
        if staged.exists():
            targets.append(
                RestoreTarget(
                    key="commands",
                    staged=staged,
                    destination=project_root / destinations["commands"],
                    is_dir=True,
                )
            )

    rules_staged = staging / rules_name
    if rules_staged.exists():
        targets.append(
            RestoreTarget(
                key="rules",
                staged=rules_staged,
                destination=project_root / destinations["rules"],
                is_dir=False,
            )
        )

    version_staged = staging / VERSION_FILE
    if version_staged.exists():
        targets.append(
            RestoreTarget(
                key="version",
                staged=version_staged,
                destination=project_root / VERSION_FILE,
                is_dir=False,
            )
        )
    return targets


def _snapshot_current_targets(targets: list[RestoreTarget], rollback_root: Path) -> None:
    for target in targets:
        if not target.destination.exists():
            continue
        snapshot = rollback_root / target.key
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        if target.destination.is_dir() and not target.destination.is_symlink():
            shutil.copytree(target.destination, snapshot)
        else:
            shutil.copy2(target.destination, snapshot)


def _replace_target(target: RestoreTarget) -> None:
    target.destination.parent.mkdir(parents=True, exist_ok=True)
    if target.destination.exists():
        _remove_path(target.destination)
    if target.is_dir:
        target.staged.rename(target.destination)
    else:
        shutil.copy2(target.staged, target.destination)


def _restore_current_targets(targets: list[RestoreTarget], rollback_root: Path) -> None:
    for target in reversed(targets):
        snapshot = rollback_root / target.key
        if target.destination.exists():
            _remove_path(target.destination)
        if not snapshot.exists():
            continue
        target.destination.parent.mkdir(parents=True, exist_ok=True)
        if target.is_dir:
            shutil.copytree(snapshot, target.destination)
        else:
            shutil.copy2(snapshot, target.destination)


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def restore_backup(project_root: Path, tool: Tool, backup_root: Path) -> None:
    """Restore deployed files from a backup directory.

    Uses a two-phase approach: copy backup to a temp staging directory first,
    then swap into place. If the copy fails mid-way, the current deployment
    remains intact.
    """
    import tempfile

    destinations = get_target_adapter(tool).destinations
    staging = Path(tempfile.mkdtemp(prefix="playbook-restore-", dir=project_root))

    try:
        rules_name = _stage_backup(backup_root, staging, destinations)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise

    try:
        _swap_staged(staging, project_root, destinations, rules_name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
