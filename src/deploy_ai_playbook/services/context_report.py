"""Static context-surface measurement for playbook agents."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from deploy_ai_playbook.discovery import DeployableFile
from deploy_ai_playbook.paths import AGENT_FILE_SUFFIX, RULES_SOURCE_FILE

CHEATSHEET_PATH = Path("knowledge-base") / "CHEATSHEET.md"
ESTIMATE_METHOD = "ceil(characters / 4)"


class ContextReportError(ValueError):
    """Raised when a declared context surface cannot be measured."""


@dataclass(frozen=True, slots=True)
class SurfaceEstimate:
    """Measured size of one static text surface."""

    path: str
    characters: int
    estimated_tokens: int

    def as_dict(self) -> dict[str, str | int]:
        return {
            "characters": self.characters,
            "estimated_tokens": self.estimated_tokens,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class AgentContextEstimate:
    """Fixed plus agent-specific context for one invocation."""

    agent: str
    origin: str
    agent_surface: SurfaceEstimate
    preloads: tuple[SurfaceEstimate, ...]
    total_characters: int
    estimated_tokens: int

    def as_dict(self) -> dict[str, object]:
        return {
            "agent": self.agent,
            "agent_surface": self.agent_surface.as_dict(),
            "estimated_tokens": self.estimated_tokens,
            "origin": self.origin,
            "preloads": [surface.as_dict() for surface in self.preloads],
            "total_characters": self.total_characters,
        }


@dataclass(frozen=True, slots=True)
class ContextEstimateReport:
    """Static context report for selected agents."""

    fixed: tuple[SurfaceEstimate, ...]
    agents: tuple[AgentContextEstimate, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "agents": [agent.as_dict() for agent in self.agents],
            "estimate": {
                "billable_usage": False,
                "method": ESTIMATE_METHOD,
                "scope": "static playbook files only",
            },
            "fixed": [surface.as_dict() for surface in self.fixed],
        }


def build_context_report(
    source_root: Path,
    layered_files: Iterable[DeployableFile],
    selected_agents: Sequence[str],
) -> ContextEstimateReport:
    """Measure fixed rules, agent instructions, and declared KB preloads."""
    files_by_relative = {entry.relative: entry for entry in layered_files}
    agent_entries = {
        entry.relative.name.removesuffix(AGENT_FILE_SUFFIX): entry
        for entry in files_by_relative.values()
        if entry.relative.parts[0] == "agents"
    }
    fixed = (
        _measure(Path(RULES_SOURCE_FILE), source_root / RULES_SOURCE_FILE),
        _measure_layered(CHEATSHEET_PATH, files_by_relative),
    )
    fixed_characters = sum(surface.characters for surface in fixed)
    agents: list[AgentContextEstimate] = []
    for agent_name in selected_agents:
        entry = agent_entries.get(agent_name)
        if entry is None:
            known = ", ".join(sorted(agent_entries))
            raise ContextReportError(f"unknown agent {agent_name!r}; available: {known}")
        agent_surface = _measure(entry.relative, entry.src_path)
        preload_paths = _declared_preloads(entry.src_path)
        preloads = tuple(
            _measure_layered(Path("knowledge-base") / preload_path, files_by_relative)
            for preload_path in preload_paths
        )
        total_characters = (
            fixed_characters
            + agent_surface.characters
            + sum(surface.characters for surface in preloads)
        )
        agents.append(
            AgentContextEstimate(
                agent=agent_name,
                origin=entry.origin,
                agent_surface=agent_surface,
                preloads=preloads,
                total_characters=total_characters,
                estimated_tokens=_estimate_tokens(total_characters),
            )
        )
    return ContextEstimateReport(fixed=fixed, agents=tuple(agents))


def _declared_preloads(agent_path: Path) -> tuple[Path, ...]:
    content = agent_path.read_text(encoding="utf-8")
    if not content.startswith("---\n"):
        return ()
    frontmatter_end = content.find("\n---", 4)
    if frontmatter_end < 0:
        raise ContextReportError(f"{agent_path}: unclosed YAML frontmatter")
    frontmatter = content[4:frontmatter_end]
    preload_line = next(
        (line for line in frontmatter.splitlines() if line.startswith("preload:")),
        None,
    )
    if preload_line is None:
        return ()
    value = preload_line.partition(":")[2].strip()
    preloads: list[Path] = []
    for raw_item in value.split(","):
        name = raw_item.partition("§")[0].strip().strip("`")
        if not name:
            continue
        relative = Path(name.removeprefix("knowledge-base/"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ContextReportError(f"{agent_path}: unsafe preload path {name!r}")
        preloads.append(relative)
    return tuple(preloads)


def _measure_layered(
    relative: Path,
    files_by_relative: dict[Path, DeployableFile],
) -> SurfaceEstimate:
    entry = files_by_relative.get(relative)
    if entry is None:
        raise ContextReportError(f"missing declared context surface: {relative}")
    return _measure(relative, entry.src_path)


def _measure(relative: Path, path: Path) -> SurfaceEstimate:
    try:
        characters = len(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ContextReportError(f"cannot read context surface {relative}: {exc}") from exc
    return SurfaceEstimate(
        path=relative.as_posix(),
        characters=characters,
        estimated_tokens=_estimate_tokens(characters),
    )


def _estimate_tokens(characters: int) -> int:
    return (characters + 3) // 4
