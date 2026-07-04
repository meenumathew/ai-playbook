"""Deployment health checks for `ai-playbook doctor`."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from deploy_ai_playbook.config import (
    ModelTierConfig,
    load_model_tier_config,
    load_pack_config,
    load_quality_tier_config,
)
from deploy_ai_playbook.discovery import discover_layered, find_deployed_agent
from deploy_ai_playbook.errors import AIPlaybookError
from deploy_ai_playbook.fs import (
    apply_rewrite,
    compute_source_fingerprint,
    diff_file,
    expected_deployed_files,
)
from deploy_ai_playbook.paths import (
    HARNESS_FILES,
    LANGUAGE_FILES,
    RULES_SOURCE_FILE,
    VERSION_FILE,
    Tool,
)
from deploy_ai_playbook.services.deploy import (
    agent_model_tier_transform,
    language_skip_files,
    path_rewrite,
)
from deploy_ai_playbook.services.pack_validation import validate_pack_content
from deploy_ai_playbook.targets import get_target_adapter
from deploy_ai_playbook.telemetry import telemetry_hook_configured
from deploy_ai_playbook.upgrade import read_version_file


class DeploymentNotFoundError(AIPlaybookError):
    """Raised when the requested target has no deployed agents directory."""

    def __init__(self, agents_dir: Path) -> None:
        self.agents_dir = agents_dir
        super().__init__(str(agents_dir))


@dataclass(frozen=True, slots=True)
class DoctorReport:
    """Health-check output consumed by the CLI presentation layer."""

    project_root: Path
    tool: Tool
    issues: list[str]
    warnings: list[str]


class DoctorService:
    """Calculate deployment health without Typer or console output."""

    def check(self, source_root: Path, project_root: Path, tool: Tool) -> DoctorReport:
        destinations = get_target_adapter(tool).destinations
        agents_dir = project_root / destinations["agents"]
        if not agents_dir.exists():
            raise DeploymentNotFoundError(agents_dir)

        rewrite = path_rewrite(destinations)
        language_filter = _deployed_language_filter(project_root)
        skip_files = language_skip_files(language_filter)

        packs = load_pack_config(project_root)
        discovered = discover_layered(source_root, packs)
        layered_files = discovered.files
        all_agents: dict[str, Path] = {
            entry.relative.name.removesuffix(".agent.md"): entry.src_path
            for entry in layered_files
            if entry.relative.parts[0] == "agents"
        }

        agent_transform, _notes = agent_model_tier_transform(tool, project_root)
        issues, warnings = _check_agents_health(all_agents, agents_dir, rewrite, agent_transform)
        warnings.extend(
            _orphan_warnings(project_root, source_root, tool, skip_files, layered_files)
        )
        rule_issues, rule_warnings = _check_rules_health(
            source_root,
            project_root,
            destinations,
            rewrite,
        )
        directory_issues, directory_warnings = _check_deployed_directories(
            project_root,
            destinations,
            rewrite,
            skip_files,
            layered_files,
        )
        issues.extend(rule_issues + directory_issues)
        warnings.extend(rule_warnings + directory_warnings)
        warnings.extend(_command_warnings(source_root, project_root, tool, rewrite))
        warnings.extend(_version_warnings(source_root, project_root, skip_files, layered_files))
        warnings.extend(_tool_mismatch_warnings(project_root, tool))
        warnings.extend(_harness_warnings(project_root))
        warnings.extend(_telemetry_hook_warnings(project_root, tool))
        warnings.extend(_runtime_directory_warnings(project_root))
        warnings.extend(_model_tier_warnings(project_root))
        warnings.extend(_quality_tier_override_warnings(project_root, all_agents.keys()))
        warnings.extend(
            f"Pack override: [yellow]{override.new_origin}[/yellow] replaces "
            f"[dim]{override.previous_origin}[/dim] at [cyan]{override.relative}[/cyan]"
            for override in discovered.overrides
        )
        # Same findings config-validate treats as errors; here they are
        # deployed-state warnings, so `doctor --strict` gates them in CI.
        warnings.extend(validate_pack_content(packs))

        return DoctorReport(project_root=project_root, tool=tool, issues=issues, warnings=warnings)


def _deployed_language_filter(project_root: Path) -> str | None:
    """Read the language filter recorded by the last deploy, if any."""
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None or parsed.language is None:
        return None
    value = parsed.language.lower()
    if value in ("", "all"):
        return None
    return value if value in LANGUAGE_FILES else None


def _check_agents_health(
    all_agents: dict[str, Path],
    agents_dir: Path,
    rewrite: dict[str, str],
    agent_transform: Callable[[str], str] | None = None,
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    for name, src_file in all_agents.items():
        path, is_disabled = find_deployed_agent(agents_dir, name)
        if path is None:
            issues.append(f"Agent [cyan]{name}[/cyan] is not deployed")
        elif is_disabled:
            warnings.append(f"Agent [cyan]{name}[/cyan] is disabled")
        elif diff_file(src_file, path, rewrite=rewrite, transform=agent_transform):
            warnings.append(f"Agent [cyan]{name}[/cyan] is stale (source has changed)")
    return issues, warnings


def _orphan_warnings(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    skip_files: set[str],
    discovered_files: list[Any],
) -> list[str]:
    orphan_paths = _orphan_examples(project_root, source_root, tool, skip_files, discovered_files)
    if not orphan_paths:
        return []
    examples = orphan_paths[:3]
    suffix = "" if len(orphan_paths) <= 3 else f", and {len(orphan_paths) - 3} more"
    return [
        f"[cyan]{len(orphan_paths)}[/cyan] orphaned file(s) with no source counterpart "
        f"(e.g. {', '.join(examples)}{suffix}) — "
        f"run [bold]ai-playbook deploy --prune --tool {tool.value}[/bold] to clean up."
    ]


def _orphan_examples(
    project_root: Path,
    source_root: Path,
    tool: Tool,
    skip_files: set[str],
    discovered_files: list[Any],
) -> list[str]:
    expected = expected_deployed_files(source_root, tool, discovered_files, skip_files=skip_files)
    orphan_paths: list[str] = []
    for deployed_subdir, expected_files in expected.items():
        deployed_dir = project_root / deployed_subdir
        if not deployed_dir.exists():
            continue
        orphan_paths.extend(_orphan_paths_in_dir(project_root, deployed_dir, expected_files))
    return orphan_paths


def _orphan_paths_in_dir(
    project_root: Path,
    deployed_dir: Path,
    expected_files: set[Path],
) -> list[str]:
    orphan_paths: list[str] = []
    for file_path in deployed_dir.rglob("*"):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue
        if file_path.name.endswith(".disabled"):
            continue
        if file_path.relative_to(deployed_dir) in expected_files:
            continue
        orphan_paths.append(str(file_path.relative_to(project_root)))
    return orphan_paths


def _check_rules_health(
    source_root: Path,
    project_root: Path,
    destinations: Mapping[str, str],
    rewrite: dict[str, str],
) -> tuple[list[str], list[str]]:
    rules_src = source_root / RULES_SOURCE_FILE
    if not rules_src.exists():
        return [], []
    rules_dst = project_root / destinations["rules"]
    if not rules_dst.exists():
        return [f"Rules file [cyan]{rules_dst.name}[/cyan] is missing"], []
    if diff_file(rules_src, rules_dst, rewrite=rewrite):
        return [], [f"Rules file [cyan]{rules_dst.name}[/cyan] is stale"]
    return [], []


def _check_deployed_directories(
    project_root: Path,
    destinations: Mapping[str, str],
    rewrite: dict[str, str],
    skip_files: set[str],
    discovered_files: list[Any],
) -> tuple[list[str], list[str]]:
    issues: list[str] = []
    warnings: list[str] = []
    for dir_name in ("knowledge-base", "skills", "templates"):
        dir_issues, dir_warnings = _check_deployed_directory(
            project_root,
            destinations,
            rewrite,
            skip_files,
            dir_name,
            discovered_files,
        )
        issues.extend(dir_issues)
        warnings.extend(dir_warnings)
    return issues, warnings


def _check_deployed_directory(
    project_root: Path,
    destinations: Mapping[str, str],
    rewrite: dict[str, str],
    skip_files: set[str],
    dir_name: str,
    discovered_files: list[Any],
) -> tuple[list[str], list[str]]:
    deployable_entries = _deployable_layered_entries(discovered_files, dir_name, skip_files)
    if not deployable_entries:
        return [], []
    dst_dir = project_root / destinations[dir_name]
    if not dst_dir.exists():
        return [f"Directory [cyan]{dir_name}[/cyan] is not deployed"], []
    stale_count = _stale_layered_file_count(deployable_entries, dst_dir, rewrite, dir_name)
    if stale_count:
        return [], [f"[cyan]{dir_name}[/cyan] has {stale_count} stale/missing file(s)"]
    return [], []


def _command_warnings(
    source_root: Path,
    project_root: Path,
    tool: Tool,
    rewrite: dict[str, str],
) -> list[str]:
    target = get_target_adapter(tool)
    commands_destination = target.optional_destination("commands")
    commands_src = source_root / "commands"
    if not commands_src.exists() or not target.supports_commands or commands_destination is None:
        return []
    commands_dir = project_root / commands_destination
    stale_count = 0
    for src_file in sorted(commands_src.glob("*.md")):
        dst_name, content = target.transform_command(
            src_file.name, src_file.read_text(encoding="utf-8")
        )
        content = apply_rewrite(content, rewrite)
        dst_file = commands_dir / dst_name
        if not dst_file.exists() or dst_file.read_text(encoding="utf-8") != content:
            stale_count += 1
    if not stale_count:
        return []
    return [f"[cyan]Commands[/cyan] have {stale_count} stale/missing file(s)"]


def _deployable_layered_entries(
    discovered_files: list[Any],
    dir_name: str,
    skip_files: set[str],
) -> list[Any]:
    entries = []
    for entry in discovered_files:
        if entry.relative.parts[0] != dir_name:
            continue
        relative = entry.relative.relative_to(dir_name)
        if dir_name == "knowledge-base" and str(relative) in skip_files:
            continue
        entries.append(entry)
    return entries


def _stale_layered_file_count(
    discovered_files: list[Any],
    dst_dir: Path,
    rewrite: dict[str, str],
    dir_name: str,
) -> int:
    stale_count = 0
    for entry in discovered_files:
        relative = entry.relative.relative_to(dir_name)
        if diff_file(entry.src_path, dst_dir / relative, rewrite=rewrite):
            stale_count += 1
    return stale_count


def _version_warnings(
    source_root: Path,
    project_root: Path,
    skip_files: set[str],
    discovered_files: list[Any],
) -> list[str]:
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None:
        return [f"[cyan]{VERSION_FILE}[/cyan] missing — redeploy to add version tracking"]
    current_fingerprint = compute_source_fingerprint(
        source_root, discovered_files, skip_files=skip_files
    )
    deployed_fingerprint = parsed.fingerprint
    if not deployed_fingerprint:
        return [
            f"[cyan]{VERSION_FILE}[/cyan] missing playbook-fingerprint "
            "— redeploy to refresh version tracking"
        ]
    if deployed_fingerprint != current_fingerprint:
        return [
            f"[cyan]{VERSION_FILE}[/cyan] fingerprint mismatch"
            f" — deployed: {deployed_fingerprint}, source: {current_fingerprint}"
        ]
    return []


def _tool_mismatch_warnings(project_root: Path, tool: Tool) -> list[str]:
    """Warn if --tool disagrees with the tool recorded in `.playbook-version`.

    Catches the silent-overlay-corruption mode where an adopter ran their last
    deploy with one tool (e.g. claude) and is now running doctor or deploy with
    another (e.g. copilot). The two destinations don't share files, so doctor
    happily reports "healthy" against an empty .github/agents tree while the
    real deployment lives under .claude/. Surfacing this as a warning makes
    the mismatch visible without blocking — adopters who genuinely run
    multi-tool deployments can ignore it.
    """
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None or not parsed.tool:
        return []
    if parsed.tool != tool.value:
        return [
            f"Tool mismatch — last deploy was [cyan]{parsed.tool}[/cyan], "
            f"running doctor as [cyan]{tool.value}[/cyan]. "
            f"Run [bold]ai-playbook doctor --tool {parsed.tool}[/bold] "
            f"or redeploy with --tool {tool.value} if intentional."
        ]
    return []


def _harness_warnings(project_root: Path) -> list[str]:
    warnings: list[str] = []
    for dst_rel in HARNESS_FILES.values():
        path = project_root / dst_rel
        if not path.exists():
            warnings.append(
                f"Harness file [cyan]{dst_rel}[/cyan] missing — redeploy without "
                f"--no-harness to add it"
            )
            continue
        # Shell scripts must keep their executable bit. A wheel re-extraction or
        # a `cp -r` without `-p` strips it; the file then exists but the Stop
        # hook silently fails. Catch the gap before the next session ends.
        if path.suffix == ".sh" and not _is_user_executable(path):
            warnings.append(
                f"Harness script [cyan]{dst_rel}[/cyan] is not executable — "
                f"run [bold]chmod +x {dst_rel}[/bold] (re-deploy will also fix it)."
            )
    warnings.extend(_commit_msg_hook_warnings(project_root))
    return warnings


def _is_user_executable(path: Path) -> bool:
    """Return True iff the file's owner-execute bit is set.

    `os.access(..., X_OK)` checks the *invoking user's* effective permissions,
    which can be misleading on shared-mount NFS or when running as root. We
    check the stat mode directly so the diagnostic matches what `chmod +x`
    sets, regardless of who runs `doctor`.
    """
    try:
        return bool(path.stat().st_mode & 0o100)
    except OSError:
        return False


def _telemetry_hook_warnings(project_root: Path, tool: Tool) -> list[str]:
    if tool is not Tool.claude:
        return []
    if not (project_root / "harness" / "telemetry.sh").exists():
        return []
    if telemetry_hook_configured(project_root):
        return []
    return [
        "Telemetry Stop hook is not configured in [cyan].claude/settings.json[/cyan] "
        "— run [bold]ai-playbook deploy --tool claude[/bold] to enable usage logging."
    ]


def _commit_msg_hook_warnings(project_root: Path) -> list[str]:
    """Warn when the teach-back commit-msg hook is configured but not installed."""
    pre_commit_config = project_root / ".pre-commit-config.yaml"
    if not pre_commit_config.exists():
        return []
    try:
        config_text = pre_commit_config.read_text(encoding="utf-8")
    except OSError:
        return []
    if not _pre_commit_config_has_commit_msg_stage(config_text):
        return []
    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        return []
    hook_path = git_dir / "hooks" / "commit-msg"
    if hook_path.exists() and "pre-commit" in hook_path.read_text(
        encoding="utf-8", errors="replace"
    ):
        return []
    return [
        "Teach-back hook configured but commit-msg stage not installed "
        "— run: [cyan]pre-commit install --hook-type commit-msg[/cyan]"
    ]


def _pre_commit_config_has_commit_msg_stage(config_text: str) -> bool:
    """Return True when any pre-commit hook declares the commit-msg stage.

    This intentionally avoids a YAML dependency in the runtime CLI but accepts
    the common inline and block-list shapes pre-commit supports.
    """
    lines = config_text.splitlines()
    for line_index, line in enumerate(lines):
        if line.strip().startswith("stages:") and _stage_line_contains_commit_msg(
            lines, line_index
        ):
            return True
    return False


def _stage_line_contains_commit_msg(lines: list[str], line_index: int) -> bool:
    line = lines[line_index]
    after_colon = line.strip().partition(":")[2].split("#", 1)[0].strip()
    if after_colon:
        return _stage_value_contains_commit_msg(after_colon)
    return any(
        _stage_block_item_contains_commit_msg(child_line)
        for child_line in _stage_child_lines(lines, line_index)
    )


def _stage_child_lines(lines: list[str], line_index: int):
    parent_indent = len(lines[line_index]) - len(lines[line_index].lstrip())
    for child_line in lines[line_index + 1 :]:
        child_stripped = child_line.strip()
        if not child_stripped or child_stripped.startswith("#"):
            continue
        child_indent = len(child_line) - len(child_line.lstrip())
        if child_indent <= parent_indent:
            break
        yield child_stripped


def _stage_block_item_contains_commit_msg(stripped_line: str) -> bool:
    return stripped_line.startswith("-") and _stage_value_contains_commit_msg(
        stripped_line[1:].strip()
    )


def _stage_value_contains_commit_msg(value: str) -> bool:
    normalized = (
        value.split("#", 1)[0]
        .replace("[", " ")
        .replace("]", " ")
        .replace(",", " ")
        .replace('"', " ")
        .replace("'", " ")
    )
    return "commit-msg" in normalized.split()


_RUNTIME_DIRS: tuple[str, ...] = (
    "stories",
    "plans",
    "research",
    "audits",
    "reviews",
    "incidents",
)


def _runtime_directory_warnings(project_root: Path) -> list[str]:
    """Warn for missing artifact directories — but not on a fresh deploy.

    Agents create these on first use (`agents/<name>.agent.md` does
    `Write` into `stories/`, `plans/`, etc.). On a brand-new project
    every dir is missing, which is the *expected* state. Firing six
    warnings on a healthy first-time deploy is noise that drowns the
    diagnostics that actually matter (stale agents, missing rules).

    Heuristic: only warn when *some* runtime dirs exist and others
    don't — that's the partial-state worth flagging. If none exist,
    the project hasn't started working yet; if all exist, nothing to
    warn about.
    """
    existing = [d for d in _RUNTIME_DIRS if (project_root / d).exists()]
    if not existing or len(existing) == len(_RUNTIME_DIRS):
        return []
    return [
        f"Runtime directory [cyan]{runtime_dir}/[/cyan] doesn't exist"
        " — agents will create it, but mkdir -p is cleaner"
        for runtime_dir in _RUNTIME_DIRS
        if not (project_root / runtime_dir).exists()
    ]


def _model_tier_warnings(project_root: Path) -> list[str]:
    model_tiers = load_model_tier_config(project_root)
    if model_tiers is None:
        return [
            "Model tier mapping missing — add [cyan]model_tiers[/cyan] with "
            "advisor/executor in [cyan].ai-playbook.toml[/cyan]. Single-model setups may "
            "set both tiers to the same model."
        ]
    missing = _missing_model_tiers(model_tiers)
    if not missing:
        return []
    return [
        "Model tier mapping incomplete — missing "
        f"[cyan]{', '.join(missing)}[/cyan] in [cyan].ai-playbook.toml[/cyan] "
        "model_tiers."
    ]


def _missing_model_tiers(model_tiers: ModelTierConfig) -> list[str]:
    missing: list[str] = []
    if not model_tiers.advisor:
        missing.append("advisor")
    if not model_tiers.executor:
        missing.append("executor")
    return missing


def _quality_tier_override_warnings(project_root: Path, agent_names: Iterable[str]) -> list[str]:
    quality_tiers = load_quality_tier_config(project_root)
    unknown_agents = sorted(set(quality_tiers.agent_overrides) - set(agent_names))
    if not unknown_agents:
        return []
    examples = ", ".join(unknown_agents[:3])
    suffix = "" if len(unknown_agents) <= 3 else f", and {len(unknown_agents) - 3} more"
    return [
        "Quality tier override names unknown agent(s): "
        f"[cyan]{examples}{suffix}[/cyan] in [cyan].ai-playbook.toml[/cyan]."
    ]
