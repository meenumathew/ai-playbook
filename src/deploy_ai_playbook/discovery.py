"""Source-root resolution and agent discovery.

`get_source_root` returns the root of the bundled data files: when installed
as a wheel, data lives inside the package (`force-include` in
`pyproject.toml`); when running from a local checkout, it is the project
root. Tests can monkey-patch `__file__` on this module to redirect.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from deploy_ai_playbook.config import Source
from deploy_ai_playbook.errors import AIPlaybookError
from deploy_ai_playbook.paths import DISABLED_SUFFIX, Tool
from deploy_ai_playbook.targets import get_target_adapter

OVERLAY_DIRS: tuple[str, ...] = ("agents", "knowledge-base", "skills", "templates")

# Display titles for the overlay directories — kept here next to OVERLAY_DIRS so
# adding a new overlay updates one place, not two.
OVERLAY_TITLES: dict[str, str] = {
    "agents": "Agents",
    "knowledge-base": "Knowledge Base",
    "skills": "Skills",
    "templates": "Templates",
}

# Per-overlay filename contracts. agents/ must end in .agent.md; other overlays
# accept any non-hidden file. Centralised here so discover_layered and
# discover_agents agree on what counts as a deployable file.
_OVERLAY_FILE_SUFFIX: dict[str, str] = {
    "agents": ".agent.md",
}


@dataclass(frozen=True, slots=True)
class DeployableFile:
    """One file produced by discovery — origin tells us core vs which pack."""

    origin: str
    relative: Path
    src_path: Path


@dataclass(frozen=True, slots=True)
class Override:
    """A record of one layer overriding another at the same relative path."""

    relative: Path
    previous_origin: str
    new_origin: str


@dataclass(frozen=True, slots=True)
class LayeredDiscovery:
    """The merged result of layered discovery: winning files plus override records."""

    files: list[DeployableFile]
    overrides: list[Override]


def _walk_source(root: Path, origin: str) -> list[DeployableFile]:
    """Walk one source root (core or a pack), yield DeployableFile per overlay file."""
    files: list[DeployableFile] = []
    for overlay_dir in OVERLAY_DIRS:
        src_dir = root / overlay_dir
        if not src_dir.exists():
            continue
        required_suffix = _OVERLAY_FILE_SUFFIX.get(overlay_dir)
        for src_file in sorted(src_dir.rglob("*")):
            if not _is_deployable_source_file(src_file, src_dir, required_suffix):
                continue
            relative = Path(overlay_dir) / src_file.relative_to(src_dir)
            files.append(DeployableFile(origin=origin, relative=relative, src_path=src_file))
    return files


def _is_deployable_source_file(
    src_file: Path,
    src_dir: Path,
    required_suffix: str | None,
) -> bool:
    if src_file.is_symlink() or not src_file.is_file():
        return False
    relative = src_file.relative_to(src_dir)
    if any(part.startswith(".") for part in relative.parts):
        return False
    return required_suffix is None or src_file.name.endswith(required_suffix)


def discover_layered(source_root: Path, packs: list[Source]) -> LayeredDiscovery:
    """Walk the core source root + each pack, return merged result.

    Last-wins on relative-path collision: pack files override core, later packs
    override earlier packs. Each override produces an Override record so callers
    (deploy, doctor) can warn or surface them in operational output.
    """
    seen: dict[Path, DeployableFile] = {}
    overrides: list[Override] = []
    layers: list[tuple[Path, str]] = [(source_root, "core")]
    layers.extend((pack.root, pack.origin) for pack in packs)
    for root, origin in layers:
        for entry in _walk_source(root, origin=origin):
            previous = seen.get(entry.relative)
            if previous is not None:
                overrides.append(
                    Override(
                        relative=entry.relative,
                        previous_origin=previous.origin,
                        new_origin=origin,
                    )
                )
            seen[entry.relative] = entry
    return LayeredDiscovery(files=list(seen.values()), overrides=overrides)


def get_source_root() -> Path:
    """Return the root of the playbook data files.

    When installed as a wheel, data is bundled inside the package.
    When running locally, data is relative to this file's location.
    """
    bundled = Path(__file__).parent / "data"
    if bundled.exists():
        return bundled
    # Local development — go up from src/deploy_ai_playbook/ to project root.
    return Path(__file__).parent.parent.parent


def discover_agents(source_root: Path) -> dict[str, Path]:
    """Return a dict of agent_name -> agent file path.

    Thin shim over `discover_layered` so there's one source-of-truth walker.
    Callers that don't need pack overlays use this; callers that do (deploy,
    doctor, diff) call `discover_layered` directly.
    """
    discovered = discover_layered(source_root, packs=[])
    return {
        entry.relative.name.removesuffix(".agent.md"): entry.src_path
        for entry in discovered.files
        if entry.relative.parts[0] == "agents"
    }


def standard_agent_names(source_root: Path | None = None) -> list[str]:
    """Return shipped standard agent names in deterministic file order."""
    root = source_root or get_source_root()
    return list(discover_agents(root).keys())


def get_agents_dir(project_root: Path, tool: Tool) -> Path:
    """Return the deployed agents directory for the given tool."""
    return project_root / get_target_adapter(tool).destination("agents")


def find_deployed_agent(agents_dir: Path, name: str) -> tuple[Path | None, bool]:
    """Find a deployed agent file — active or disabled.

    Returns (path, is_disabled). Path is None if not found.
    """
    active = agents_dir / f"{name}.agent.md"
    disabled = agents_dir / f"{name}.agent.md{DISABLED_SUFFIX}"
    if active.exists():
        return active, False
    if disabled.exists():
        return disabled, True
    return None, False


class UnknownAgentError(ValueError, AIPlaybookError):
    """Raised when `resolve_agent_names` is given names not in the registry.

    Carries the unknown names *and* the registry so a CLI wrapper can render
    a helpful error without re-querying. Library code does not import Rich
    or Typer; presentation lives in `cli.py`.
    """

    def __init__(self, unknown: list[str], available: list[str], label: str) -> None:
        super().__init__(
            f"Unknown {label}(s): {', '.join(unknown)}. Available: {', '.join(available)}"
        )
        self.unknown = unknown
        self.available = available
        self.label = label


def resolve_agent_names(
    agent: str,
    all_agents: dict[str, Path],
    label: str = "agent",
) -> list[str]:
    """Parse and validate agent names from a CLI argument.

    Args:
        agent: 'all' or comma-separated agent names.
        all_agents: dict of available agents.
        label: label used in error messages.

    Returns:
        List of validated agent names.

    Raises:
        UnknownAgentError: if any provided name is not in `all_agents`.
            Callers (CLI) translate this into the user-facing presentation
            and exit code; library callers can handle it directly.
    """
    if agent == "all":
        return list(all_agents.keys())
    names = [a.strip() for a in agent.split(",")]
    unknown = [a for a in names if a not in all_agents]
    if unknown:
        raise UnknownAgentError(unknown=unknown, available=list(all_agents.keys()), label=label)
    return names
