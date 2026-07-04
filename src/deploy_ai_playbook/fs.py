"""Pure file-system helpers for the deploy CLI.

These functions return Rich-formatted status strings for the caller to print,
but never call `console.print` directly — keeping IO concerns separate from
presentation makes them safe to compose and easy to test.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterator, Mapping
from pathlib import Path

from deploy_ai_playbook.paths import HARNESS_FILES, RULES_SOURCE_FILE, Tool
from deploy_ai_playbook.safety import (
    UnsafeDestinationError,
    assert_safe_destination,
    write_bytes_safely,
    write_text_safely,
)
from deploy_ai_playbook.targets import COMMAND_ARGUMENTS_PLACEHOLDER, get_target_adapter

AGENT_FILE_SUFFIX = ".agent.md"


def generated_command_shim(agent_name: str) -> str:
    """Standard slash-command shim for agents without an authored `commands/` file.

    Pack agents ship no shim of their own (the `commands/` overlay is
    core-only); deploy generates this so pack agents are slash-invocable
    exactly like core agents. Mirrors the authored shim shape.
    """
    return (
        "---\n"
        f"description: 'Forward to the {agent_name} agent'\n"
        "mode: agent\n"
        "---\n"
        f"Use the **{agent_name}** agent.\n"
        "\n"
        f"{COMMAND_ARGUMENTS_PLACEHOLDER}\n"
    )


def _iter_visible_files(directory: Path) -> Iterator[Path]:
    for file_path in sorted(directory.rglob("*")):
        if file_path.is_file() and not file_path.name.startswith("."):
            yield file_path


def _is_skipped(relative_path: Path, skip_files: set[str] | None) -> bool:
    return skip_files is not None and str(relative_path) in skip_files


def assert_safe_path(path: Path, safe_root: Path) -> None:
    assert_safe_destination(path, safe_root)


def assert_safe_tree(root: Path, safe_root: Path) -> None:
    assert_safe_destination(root, safe_root)
    for path in root.rglob("*"):
        if path.is_symlink():
            raise UnsafeDestinationError(
                f"Unsafe destination {root}: refuses to back up through symlink {path}"
            )


def _expected_command_files(
    source_root: Path,
    tool: Tool,
    agent_names: set[str] | None = None,
) -> set[Path] | None:
    src_commands = source_root / "commands"
    if not src_commands.exists():
        return None
    target = get_target_adapter(tool)
    if not target.supports_commands:
        return None
    files: set[Path] = set()
    authored_stems: set[str] = set()
    for file_path in src_commands.glob("*.md"):
        authored_stems.add(file_path.stem)
        output_name, _ = target.transform_command(file_path.name, "")
        files.add(Path(output_name))
    # Generated shims for agents without an authored shim (pack agents) are
    # expected too — prune and doctor must not treat them as orphans.
    for agent_name in (agent_names or set()) - authored_stems:
        output_name, _ = target.transform_command(f"{agent_name}.md", "")
        files.add(Path(output_name))
    return files


def _iter_prunable_files(deployed_dir: Path) -> Iterator[Path]:
    for file_path in deployed_dir.rglob("*"):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        if file_path.name.endswith(".disabled"):
            continue
        yield file_path


def _hash_overlay_sources(
    hasher: hashlib._Hash,
    discovered_files: list,
    skip_files: set[str] | None,
) -> None:
    """Hash overlay files (agents / knowledge-base / skills / templates) from discovery."""
    for entry in sorted(discovered_files, key=lambda f: f.relative):
        if (
            entry.relative.parts[0] == "knowledge-base"
            and skip_files
            and str(entry.relative.relative_to("knowledge-base")) in skip_files
        ):
            continue
        hasher.update(str(entry.relative).encode())
        hasher.update(entry.src_path.read_bytes())


def _hash_command_sources(hasher: hashlib._Hash, source_root: Path) -> None:
    commands_dir = source_root / "commands"
    if not commands_dir.exists():
        return
    for file_path in _iter_visible_files(commands_dir):
        hasher.update(("commands/" + str(file_path.relative_to(commands_dir))).encode())
        hasher.update(file_path.read_bytes())


def _hash_harness_sources(hasher: hashlib._Hash, source_root: Path) -> None:
    harness_dir = source_root / "harness"
    if not harness_dir.exists():
        return
    for src_name in sorted(HARNESS_FILES):
        file_path = harness_dir / src_name
        if not file_path.is_file():
            continue
        hasher.update(("harness/" + src_name).encode())
        hasher.update(file_path.read_bytes())


def compute_source_fingerprint(
    source_root: Path,
    discovered_files: list,
    skip_files: set[str] | None = None,
) -> str:
    """Compute a short hash fingerprint of all deployable source files.

    `discovered_files` is the result of `discovery.discover_layered(...).files`
    (typed loosely as `list` to avoid an `fs → discovery` import cycle). The
    fingerprint covers overlay content (core + packs) plus commands, harness,
    and CLAUDE.md, so any drift is reflected in the hash.
    """
    hasher = hashlib.sha256()
    _hash_overlay_sources(hasher, discovered_files, skip_files)
    _hash_command_sources(hasher, source_root)
    _hash_harness_sources(hasher, source_root)
    rules = source_root / RULES_SOURCE_FILE
    if rules.exists():
        hasher.update(rules.read_bytes())
    return hasher.hexdigest()[:12]


def copy_file(
    src: Path,
    dst: Path,
    dry_run: bool,
    rewrite: dict[str, str] | None = None,
    safe_root: Path | None = None,
    transform: Callable[[str], str] | None = None,
) -> str:
    """Copy src to dst. Returns a rich status string for display.

    Args:
        src: Source file path.
        dst: Destination file path.
        dry_run: If True, no files are written.
        rewrite: Optional dict of {old_text: new_text} applied to file content on write.
        transform: Optional content transform applied after `rewrite`.
    """
    assert_safe_destination(dst, safe_root)
    source_bytes = src.read_bytes()
    text_content = _text_with_rewrite(source_bytes, rewrite, transform)
    if dry_run:
        return "[yellow]would copy[/yellow]"
    if text_content is not None:
        return write_text_safely(dst, text_content, safe_root)
    return write_bytes_safely(dst, source_bytes, safe_root)


def diff_file(
    src: Path,
    dst: Path,
    rewrite: dict[str, str] | None = None,
    transform: Callable[[str], str] | None = None,
) -> str | None:
    """Compare source content against deployed file.

    Applies the same `rewrite`/`transform` the deploy applied, so a clean
    deployment always compares equal. Returns a status string if they differ,
    or None if identical / not deployed.
    """
    if not dst.exists():
        return "[yellow]not deployed[/yellow]"
    src_bytes = src.read_bytes()
    text_content = _text_with_rewrite(src_bytes, rewrite, transform)
    if text_content is not None:
        src_bytes = text_content.encode("utf-8")
    if src_bytes == dst.read_bytes():
        return None
    return "[red]changed[/red]"


def _text_with_rewrite(
    content: bytes,
    rewrite: dict[str, str] | None,
    transform: Callable[[str], str] | None = None,
) -> str | None:
    if not rewrite and transform is None:
        return None
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return None
    text = apply_rewrite(text, rewrite)
    return transform(text) if transform is not None else text


def copy_directory(
    src: Path,
    dst: Path,
    dry_run: bool,
    skip_files: set[str] | None = None,
    rewrite: dict[str, str] | None = None,
    safe_root: Path | None = None,
) -> list[tuple[str, str]]:
    """Recursively copy src directory to dst.

    Returns list of (relative_path, status_string) for each file processed.
    Files whose relative path is in skip_files are reported as 'skipped' and not copied.
    `rewrite` is forwarded to copy_file so root-relative path refs (e.g. `knowledge-base/`)
    can be remapped to tool-specific deployment paths.
    """
    results: list[tuple[str, str]] = []
    for src_file in sorted(src.rglob("*")):
        if src_file.is_file() and not src_file.name.startswith("."):
            relative = src_file.relative_to(src)
            if skip_files and str(relative) in skip_files:
                results.append((str(relative), "[dim]skipped[/dim]"))
                continue
            dst_file = dst / relative
            status = copy_file(src_file, dst_file, dry_run, rewrite=rewrite, safe_root=safe_root)
            results.append((str(relative), status))
    return results


def expected_deployed_files(
    source_root: Path,
    tool: Tool,
    discovered_files: list,
    skip_files: set[str] | None = None,
) -> dict[str, set[Path]]:
    """Compute the set of files each deployed directory *should* contain.

    Used by `--prune` and `doctor` to identify orphaned files (e.g. left over
    after an agent rename) that have no source counterpart.

    `discovered_files` is the result of `discovery.discover_layered(...).files`
    (typed loosely as `list` to avoid an `fs → discovery` import cycle). Pack
    files are recognised as expected — prune will NOT remove them.

    Returns a mapping from deployed directory path (string) to the set of
    relative `Path` objects expected in that directory. Disabled-agent files
    (`<name>.agent.md.disabled`) are intentionally not in the expected set —
    callers should preserve them at prune time.
    """
    target = get_target_adapter(tool)
    destinations = target.destinations
    expected = _expected_overlay_files(discovered_files, destinations, skip_files)
    agent_names = {
        entry.relative.name.removesuffix(AGENT_FILE_SUFFIX)
        for entry in discovered_files
        if entry.relative.parts[0] == "agents"
    }
    _add_expected_command_files(expected, source_root, tool, agent_names)
    return expected


def _expected_overlay_files(
    discovered_files: list,
    destinations: Mapping[str, str],
    skip_files: set[str] | None,
) -> dict[str, set[Path]]:
    expected: dict[str, set[Path]] = {}
    for entry in discovered_files:
        overlay = entry.relative.parts[0]
        if overlay not in destinations:
            continue
        relative_inside = entry.relative.relative_to(overlay)
        if overlay == "knowledge-base" and _is_skipped(relative_inside, skip_files):
            continue
        expected.setdefault(destinations[overlay], set()).add(relative_inside)
    return expected


def _add_expected_command_files(
    expected: dict[str, set[Path]],
    source_root: Path,
    tool: Tool,
    agent_names: set[str] | None = None,
) -> None:
    target = get_target_adapter(tool)
    if not target.supports_commands:
        return
    files = _expected_command_files(source_root, tool, agent_names)
    if files is not None:
        expected[target.destination("commands")] = files


def prune_orphaned_files(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    dry_run: bool,
    discovered_files: list,
    skip_files: set[str] | None = None,
) -> list[tuple[Path, str]]:
    """Remove deployed files that have no corresponding source file.

    Preserves `*.disabled` files (user-managed state). Returns a list of
    (relative_path, status_string) tuples for caller display.

    `discovered_files` is the result of `discovery.discover_layered(...).files`
    (typed loosely as `list` to avoid an `fs → discovery` import cycle). Pack
    files are recognised as expected — prune will NOT remove them.
    """
    expected = expected_deployed_files(source_root, tool, discovered_files, skip_files=skip_files)
    results: list[tuple[Path, str]] = []

    for deployed_subdir, expected_files in expected.items():
        deployed_dir = project_root / deployed_subdir
        assert_safe_destination(deployed_dir, project_root)
        if not deployed_dir.exists():
            continue
        for file_path in _iter_prunable_files(deployed_dir):
            relative = file_path.relative_to(deployed_dir)
            if relative in expected_files:
                continue
            display_path = file_path.relative_to(project_root)
            if dry_run:
                results.append((display_path, "[yellow]would prune[/yellow]"))
            else:
                file_path.unlink()
                results.append((display_path, "[red]pruned[/red]"))
    return results


def copy_commands_directory(
    src: Path,
    dst: Path,
    tool: Tool,
    dry_run: bool,
    command_names: set[str] | None = None,
    known_agent_names: set[str] | None = None,
    safe_root: Path | None = None,
    rewrite: dict[str, str] | None = None,
) -> list[tuple[str, str]]:
    """Copy commands directory with tool-specific transformations.

    - Claude: copies as-is (.md, $ARGUMENTS placeholder)
    - Copilot: renames to .prompt.md, replaces $ARGUMENTS with ${input:arguments}
    - Cursor: copies as .md, keeps $ARGUMENTS placeholder
    - Kiro: returns no command files because the target has no slash-command destination

    `rewrite` is the same source-path → deployed-path map the overlay copy
    uses, applied after the tool-specific transform.
    """
    target = get_target_adapter(tool)
    if not target.supports_commands:
        return []
    results: list[tuple[str, str]] = []
    for src_file in sorted(src.glob("*.md")):
        if _command_filtered_out(src_file.stem, command_names, known_agent_names):
            continue
        dst_name, content = target.transform_command(
            src_file.name, src_file.read_text(encoding="utf-8")
        )
        content = apply_rewrite(content, rewrite)
        dst_file = dst / dst_name
        assert_safe_destination(dst_file, safe_root)
        if dry_run:
            status = "[yellow]would copy[/yellow]"
        else:
            status = write_text_safely(dst_file, content, safe_root)
        results.append((dst_name, status))
    if command_names is not None:
        authored_stems = {p.stem for p in src.glob("*.md")}
        results.extend(
            _generate_missing_shims(
                sorted(command_names - authored_stems), target, dst, dry_run, safe_root, rewrite
            )
        )
    return results


def _command_filtered_out(
    stem: str,
    command_names: set[str] | None,
    known_agent_names: set[str] | None,
) -> bool:
    if command_names is None:
        return False
    if known_agent_names is not None:
        return stem in known_agent_names and stem not in command_names
    return stem not in command_names


def apply_rewrite(content: str, rewrite: dict[str, str] | None) -> str:
    """Apply the deploy-time path-reference rewrite map to file content.

    Public because staleness checks (diff/doctor) must apply the same rewrite
    deploy applies, or freshly deployed content compares as changed forever."""
    if rewrite:
        for old, new in rewrite.items():
            content = content.replace(old, new)
    return content


def _generate_missing_shims(
    agent_names: list[str],
    target,
    dst: Path,
    dry_run: bool,
    safe_root: Path | None,
    rewrite: dict[str, str] | None,
) -> list[tuple[str, str]]:
    """Generate standard shims for agents without an authored `commands/` file.

    Pack agents have no shim of their own; this keeps them slash-invocable
    like core agents.
    """
    results: list[tuple[str, str]] = []
    for agent_name in agent_names:
        dst_name, content = target.transform_command(
            f"{agent_name}.md", generated_command_shim(agent_name)
        )
        content = apply_rewrite(content, rewrite)
        dst_file = dst / dst_name
        assert_safe_destination(dst_file, safe_root)
        if dry_run:
            status = "[yellow]would generate[/yellow]"
        else:
            status = f"{write_text_safely(dst_file, content, safe_root)} [dim](generated)[/dim]"
        results.append((dst_name, status))
    return results
