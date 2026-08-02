"""Upgrade-check helpers: surface playbook drift between source and a deployed project."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

from deploy_ai_playbook.config import current_playbook_version, load_pack_config
from deploy_ai_playbook.deployment_record import (
    DeploymentRecord,
    DeploymentScope,
    parse_deployment_record,
)
from deploy_ai_playbook.discovery import discover_layered, get_source_root
from deploy_ai_playbook.fs import compute_source_fingerprint
from deploy_ai_playbook.paths import LANGUAGE_FILES, VERSION_FILE, Tool


class UpgradeStatus(StrEnum):
    """States a deployed project can be in relative to source."""

    not_deployed = "not_deployed"
    up_to_date = "up_to_date"
    partial = "partial"
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
    deployment_scope: DeploymentScope = field(default_factory=DeploymentScope)
    current_playbook_version: str = ""
    notes: list[str] = field(default_factory=list)


def check_upgrade(project_root: Path, tool: Tool) -> UpgradeReport:
    """Compare the deployed playbook fingerprint against the current source.

    Returns an UpgradeReport with one of three statuses:
      - not_deployed: VERSION_FILE absent: adopter has never deployed
      - up_to_date: deployed fingerprint matches the source fingerprint
      - drift: fingerprints differ: running `deploy` would change files
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
        source_root,
        discovered.files,
        skip_files=skip_files,
        agent_names=parsed.scope.fingerprint_agent_names,
        include_commands=parsed.scope.commands,
        include_harness=parsed.scope.harness,
        include_rules=parsed.scope.rules,
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
        status = UpgradeStatus.partial if parsed.scope.is_partial else UpgradeStatus.up_to_date
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
        deployment_scope=parsed.scope,
        current_playbook_version=current_version,
        notes=notes,
    )


ParsedVersionFile = DeploymentRecord


def parse_version_file(text: str) -> DeploymentRecord:
    """Parse the simple ``key: value`` lines in `.playbook-version`.

    Unknown keys are ignored; multiple `pack:` lines collapse into ``packs``.
    """
    return parse_deployment_record(text)


def read_version_file(version_path: Path) -> DeploymentRecord | None:
    """Read and parse `.playbook-version`; return None if the file is absent."""
    if not version_path.exists():
        return None
    return parse_version_file(version_path.read_text(encoding="utf-8"))


def deployed_language_filter(project_root: Path) -> str | None:
    """Read the language filter recorded by the last deploy, if any."""
    parsed = read_version_file(project_root / VERSION_FILE)
    if parsed is None or parsed.language is None:
        return None
    value = parsed.language.lower()
    if value in ("", "all"):
        return None
    return value if value in LANGUAGE_FILES else None


def stale_carryover_fingerprint(
    previous: DeploymentRecord | None,
    *,
    tool: Tool,
    source_root: Path,
    discovered_files: list,
    selected_agents: set[str],
    all_agents: set[str],
    rules: bool,
    commands: bool,
    harness: bool,
    selected_language: str | None,
) -> str | None:
    """Return the previous fingerprint when a selective deploy leaves stale files.

    A selective deploy merges into the previously deployed surface without
    rewriting the carried-over files. Fingerprinting the merged surface from
    current source would claim those files came from source they were never
    deployed from: `upgrade-check` would then report a false "up to date".

    Returns None when the fresh merged-scope fingerprint is truthful: no
    previous record, this run rewrites the whole previous surface, or the
    source has not moved since the previous deploy. Otherwise returns the
    previous (stale) fingerprint to carry into the new record so
    `upgrade-check` reports drift; the next full deploy heals the record.
    """
    if previous is None or previous.tool != tool.value or not previous.fingerprint:
        return None
    prev_scope = previous.scope
    prev_agents = set(prev_scope.agents) if prev_scope.is_partial else set(all_agents)
    this_run_rewrites_previous_surface = (
        prev_agents <= selected_agents
        and (rules or not prev_scope.rules)
        and (commands or not prev_scope.commands)
        and (harness or not prev_scope.harness)
        and _language_skip_files(selected_language) <= _language_skip_files(previous.language)
    )
    if this_run_rewrites_previous_surface:
        return None
    current_over_previous_scope = compute_source_fingerprint(
        source_root,
        discovered_files,
        skip_files=_language_skip_files(previous.language),
        agent_names=prev_scope.fingerprint_agent_names,
        include_commands=prev_scope.commands,
        include_harness=prev_scope.harness,
        include_rules=prev_scope.rules,
    )
    if current_over_previous_scope == previous.fingerprint:
        return None
    return previous.fingerprint


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
