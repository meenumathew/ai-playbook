"""Upgrade-check helpers — surface playbook drift between source and a deployed project."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from deploy_ai_playbook.config import current_playbook_version, load_pack_config
from deploy_ai_playbook.discovery import discover_layered, get_source_root
from deploy_ai_playbook.fs import compute_source_fingerprint
from deploy_ai_playbook.paths import LANGUAGE_FILES, VERSION_FILE, Tool


class UpgradeStatus(StrEnum):
    """States a deployed project can be in relative to source."""

    not_deployed = "not_deployed"
    up_to_date = "up_to_date"
    drift = "drift"
    tool_mismatch = "tool_mismatch"


@dataclass(frozen=True)
class UpgradeReport:
    """Snapshot of upgrade state for one project + tool combination."""

    project_root: Path
    tool: Tool
    status: UpgradeStatus
    deployed_fingerprint: str | None = None
    source_fingerprint: str | None = None
    deployed_at: str | None = None
    deployed_tool: str | None = None
    deployed_language: str | None = None
    deployed_packs: list[str] = field(default_factory=list)
    current_playbook_version: str = ""
    notes: list[str] = field(default_factory=list)


def check_upgrade(project_root: Path, tool: Tool) -> UpgradeReport:
    """Compare the deployed playbook fingerprint against the current source.

    Returns an UpgradeReport with one of three statuses:
      - not_deployed: VERSION_FILE absent — adopter has never deployed
      - up_to_date: deployed fingerprint matches the source fingerprint
      - drift: fingerprints differ — running `deploy` would change files
            - tool_mismatch: VERSION_FILE was written by a different tool target
    """
    version_path = project_root / VERSION_FILE
    current_version = current_playbook_version()

    if not version_path.exists():
        return UpgradeReport(
            project_root=project_root,
            tool=tool,
            status=UpgradeStatus.not_deployed,
            current_playbook_version=current_version,
            notes=[f"{VERSION_FILE} missing — run `ai-playbook deploy --tool {tool.value}`"],
        )

    parsed = parse_version_file(version_path.read_text(encoding="utf-8"))

    source_root = get_source_root()
    packs = load_pack_config(project_root)
    discovered = discover_layered(source_root, packs)
    skip_files = _language_skip_files(parsed.language)
    source_fingerprint = compute_source_fingerprint(
        source_root, discovered.files, skip_files=skip_files
    )

    notes: list[str] = []
    if parsed.tool and parsed.tool != tool.value:
        notes.append(
            f"Last deploy was --tool {parsed.tool}; upgrade-check ran as --tool {tool.value}. "
            f"Re-run with --tool {parsed.tool}, or deploy --tool {tool.value} if intentional."
        )

    if parsed.tool and parsed.tool != tool.value:
        status = UpgradeStatus.tool_mismatch
    elif parsed.fingerprint == source_fingerprint:
        status = UpgradeStatus.up_to_date
    else:
        status = UpgradeStatus.drift
    return UpgradeReport(
        project_root=project_root,
        tool=tool,
        status=status,
        deployed_fingerprint=parsed.fingerprint,
        source_fingerprint=source_fingerprint,
        deployed_at=parsed.deployed_at,
        deployed_tool=parsed.tool,
        deployed_language=parsed.language,
        deployed_packs=parsed.packs,
        current_playbook_version=current_version,
        notes=notes,
    )


@dataclass(frozen=True)
class ParsedVersionFile:
    """Typed view over `.playbook-version` for callers across cli/doctor/upgrade.

    `.playbook-version` is the on-disk record of what was last deployed. It is
    a tiny ``key: value`` text file (no JSON/TOML so it stays human-readable).
    Three modules used to parse it independently — that drift hazard collapses
    into this single dataclass + parser. Callers that need only one field may
    still call `read_version_field()` for ergonomics.
    """

    fingerprint: str | None = None
    deployed_at: str | None = None
    tool: str | None = None
    language: str | None = None
    packs: list[str] = field(default_factory=list)


def parse_version_file(text: str) -> ParsedVersionFile:
    """Parse the simple ``key: value`` lines in `.playbook-version`.

    Unknown keys are ignored; multiple `pack:` lines collapse into ``packs``.
    """
    fingerprint: str | None = None
    deployed_at: str | None = None
    tool: str | None = None
    language: str | None = None
    packs: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        match key:
            case "playbook-fingerprint":
                fingerprint = value
            case "deployed-at":
                deployed_at = value
            case "tool":
                tool = value
            case "language":
                language = value
            case "pack":
                packs.append(value)
    return ParsedVersionFile(
        fingerprint=fingerprint,
        deployed_at=deployed_at,
        tool=tool,
        language=language,
        packs=packs,
    )


def read_version_file(version_path: Path) -> ParsedVersionFile | None:
    """Read and parse `.playbook-version`; return None if the file is absent."""
    if not version_path.exists():
        return None
    return parse_version_file(version_path.read_text(encoding="utf-8"))


def _language_skip_files(language: str | None) -> set[str]:
    """Return KB files omitted for a deployed-language filter (`all` → empty)."""
    if language is None or language in ("", "all"):
        return set()
    if language not in LANGUAGE_FILES:
        return set()
    skipped: set[str] = set()
    for name, files in LANGUAGE_FILES.items():
        if name != language:
            skipped.update(files)
    return skipped
