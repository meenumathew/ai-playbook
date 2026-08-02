"""Diff service: compute drift between source and a deployed copy."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from deploy_ai_playbook.config import load_pack_config
from deploy_ai_playbook.deployment_record import DeploymentScope, parse_deployment_record
from deploy_ai_playbook.discovery import discover_layered
from deploy_ai_playbook.fs import apply_rewrite, diff_file
from deploy_ai_playbook.paths import (
    AGENT_FILE_SUFFIX,
    HARNESS_FILES,
    RULES_SOURCE_FILE,
    VERSION_FILE,
    Tool,
)
from deploy_ai_playbook.services.deploy import agent_model_tier_transform, path_rewrite
from deploy_ai_playbook.targets import TargetAdapter, get_target_adapter


@dataclass(frozen=True, slots=True)
class DiffSection:
    """One labelled group of file-level diffs ready for display."""

    title: str
    location: Path
    changes: list[tuple[str, str]]


@dataclass(frozen=True, slots=True)
class DiffReport:
    """Aggregate result of a diff computation."""

    sections: list[DiffSection] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return any(section.changes for section in self.sections)


def compute_diff(
    source_root: Path,
    project_root: Path,
    tool: Tool,
) -> DiffReport:
    """Compute the diff sections between the playbook source and a deployment."""
    target = get_target_adapter(tool)
    destinations = target.destinations
    rewrite = path_rewrite(destinations)
    packs = load_pack_config(project_root)
    discovered = discover_layered(source_root, packs)
    record_path = project_root / VERSION_FILE
    scope = (
        parse_deployment_record(record_path.read_text(encoding="utf-8")).scope
        if record_path.exists()
        else DeploymentScope()
    )
    scoped_agent_names = set(scope.agents) if scope.is_partial else None
    known_agent_names = {
        entry.relative.name.removesuffix(AGENT_FILE_SUFFIX)
        for entry in discovered.files
        if entry.relative.parts[0] == "agents"
    }

    agent_transform, _notes = agent_model_tier_transform(tool, project_root)

    sections: list[DiffSection] = []
    sections.append(
        _agents_section(
            project_root,
            target,
            rewrite,
            discovered.files,
            agent_transform,
            scoped_agent_names,
        )
    )
    if scope.rules:
        sections.extend(_rules_sections(source_root, project_root, destinations, rewrite))
    sections.extend(
        _overlay_directory_sections(project_root, destinations, rewrite, discovered.files)
    )
    if scope.commands:
        sections.extend(
            _command_sections(
                source_root,
                project_root,
                target,
                rewrite,
                scoped_agent_names,
                known_agent_names,
            )
        )
    if scope.harness:
        sections.extend(_harness_sections(source_root, project_root))
    return DiffReport(sections=sections)


def _agents_section(
    project_root: Path,
    target: TargetAdapter,
    rewrite: dict[str, str],
    discovered_files: list,
    agent_transform: Callable[[str], str] | None = None,
    agent_names: set[str] | None = None,
) -> DiffSection:
    agents_dir = project_root / target.destination("agents")
    changes: list[tuple[str, str]] = []
    for entry in discovered_files:
        if entry.relative.parts[0] != "agents":
            continue
        source_filename = entry.relative.name
        if (
            agent_names is not None
            and source_filename.removesuffix(AGENT_FILE_SUFFIX) not in agent_names
        ):
            continue
        filename = target.agent_output_name(source_filename)
        status = diff_file(
            entry.src_path, agents_dir / filename, rewrite=rewrite, transform=agent_transform
        )
        if status:
            changes.append((filename, status))
    return DiffSection(title="Agents", location=agents_dir, changes=changes)


def _rules_sections(
    source_root: Path,
    project_root: Path,
    destinations: Mapping[str, str],
    rewrite: dict[str, str],
) -> list[DiffSection]:
    rules_src = source_root / RULES_SOURCE_FILE
    if not rules_src.exists():
        return []
    rules_dst = project_root / destinations["rules"]
    status = diff_file(rules_src, rules_dst, rewrite=rewrite)
    changes = [(rules_dst.name, status)] if status else []
    return [DiffSection(title="Rules", location=rules_dst, changes=changes)]


def _overlay_directory_sections(
    project_root: Path,
    destinations: Mapping[str, str],
    rewrite: dict[str, str],
    discovered_files: list,
) -> list[DiffSection]:
    sections: list[DiffSection] = []
    for dir_name in ("knowledge-base", "skills", "templates"):
        dst_dir = project_root / destinations[dir_name]
        title = dir_name.replace("-", " ").title()
        changes: list[tuple[str, str]] = []
        for entry in sorted(discovered_files, key=lambda f: f.relative):
            if entry.relative.parts[0] != dir_name:
                continue
            relative = entry.relative.relative_to(dir_name)
            status = diff_file(entry.src_path, dst_dir / relative, rewrite=rewrite)
            if status:
                changes.append((str(relative), status))
        sections.append(DiffSection(title=title, location=dst_dir, changes=changes))
    return sections


def _command_sections(
    source_root: Path,
    project_root: Path,
    target: TargetAdapter,
    rewrite: dict[str, str],
    agent_names: set[str] | None = None,
    known_agent_names: set[str] | None = None,
) -> list[DiffSection]:
    commands_src = source_root / "commands"
    commands_destination = target.optional_destination("commands")
    if not commands_src.exists() or not target.supports_commands or commands_destination is None:
        return []
    commands_dest = project_root / commands_destination
    changes: list[tuple[str, str]] = []
    for src_file in sorted(commands_src.glob("*.md")):
        if (
            agent_names is not None
            and known_agent_names is not None
            and src_file.stem in known_agent_names
            and src_file.stem not in agent_names
        ):
            continue
        dst_name, content = target.transform_command(
            src_file.name, src_file.read_text(encoding="utf-8")
        )
        content = apply_rewrite(content, rewrite)
        dst_file = commands_dest / dst_name
        if not dst_file.exists():
            changes.append((dst_name, "[yellow]not deployed[/yellow]"))
        elif dst_file.read_text(encoding="utf-8") != content:
            changes.append((dst_name, "[red]changed[/red]"))
    return [DiffSection(title="Commands", location=commands_dest, changes=changes)]


def _harness_sections(source_root: Path, project_root: Path) -> list[DiffSection]:
    harness_dir = source_root / "harness"
    if not harness_dir.exists():
        return []
    changes: list[tuple[str, str]] = []
    for src_name, dst_rel in HARNESS_FILES.items():
        src_file = harness_dir / src_name
        if not src_file.exists():
            continue
        dst_file = project_root / dst_rel
        status = diff_file(src_file, dst_file)
        if status:
            changes.append((dst_rel, status))
    return [DiffSection(title="Harness", location=project_root, changes=changes)]
