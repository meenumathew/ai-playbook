"""Artifacts service — pure logic for artifact discovery and gitignore policy."""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

ARTIFACT_DIRECTORIES: Mapping[str, str] = {
    "stories": "Story",
    "research": "Research",
    "plans": "Plan",
    "audits": "Audit",
    "reviews": "Review",
    "incidents": "Incident",
}
ARTIFACT_IGNORE_BLOCK_START = "# ai-playbook artifacts (managed)"
ARTIFACT_IGNORE_BLOCK_END = "# end ai-playbook artifacts"
ARTIFACT_IGNORE_LINES = tuple(f"{directory}/" for directory in ARTIFACT_DIRECTORIES)
# Hook state written by the shipped harness hooks: read-budget.sh counters and
# telemetry.sh usage log, including rotated archives (usage-<ts>.jsonl[.gz]).
# Machine-local by nature — the managed block keeps it out of version control.
HOOK_STATE_IGNORE_LINES = (
    ".claude/read-budget/",
    ".claude/usage*.jsonl*",
)
MANAGED_IGNORE_LINES = (*ARTIFACT_IGNORE_LINES, *HOOK_STATE_IGNORE_LINES)


class ArtifactPolicy(StrEnum):
    """Adopter artifact tracking policy managed through `.gitignore`."""

    local = "local"
    shared = "shared"
    status = "status"


def collect_artifact_rows(
    project_root: Path,
    query: str | None,
) -> list[tuple[str, str, str]]:
    """Return (kind, relative_path, status) rows for every matching artifact."""
    rows: list[tuple[str, str, str]] = []
    for directory, kind in ARTIFACT_DIRECTORIES.items():
        artifact_dir = project_root / directory
        if not artifact_dir.exists():
            continue
        rows.extend(
            _artifact_row(project_root, kind, artifact_path)
            for artifact_path in sorted(artifact_dir.rglob("*.md"))
            if artifact_path.is_file() and _artifact_matches(project_root, artifact_path, query)
        )
    return rows


def _artifact_row(project_root: Path, kind: str, artifact_path: Path) -> tuple[str, str, str]:
    return (
        kind,
        artifact_path.relative_to(project_root).as_posix(),
        _artifact_status(artifact_path),
    )


def _artifact_matches(project_root: Path, artifact_path: Path, query: str | None) -> bool:
    if query is None:
        return True
    needle = query.lower()
    relative_path = artifact_path.relative_to(project_root).as_posix().lower()
    if needle in relative_path:
        return True
    return needle in artifact_path.read_text(encoding="utf-8").lower()


def _artifact_status(artifact_path: Path) -> str:
    for line in artifact_path.read_text(encoding="utf-8").splitlines()[:40]:
        if line.startswith("status:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("| **Status** |"):
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) >= 2:
                return cells[1]
    return ""


def artifact_policy_status(gitignore_path: Path) -> str:
    """Describe the current artifact-policy state of `.gitignore`."""
    if not gitignore_path.exists():
        return "Artifact policy: shared (no .gitignore file)"
    content = gitignore_path.read_text(encoding="utf-8")
    if has_managed_artifact_block(content):
        return "Artifact policy: local (managed .gitignore block present)"
    if any(line.strip() in ARTIFACT_IGNORE_LINES for line in content.splitlines()):
        return "Artifact policy: custom (artifact paths ignored outside managed block)"
    return "Artifact policy: shared (no managed artifact ignore block)"


def artifact_gitignore_content(content: str, policy: ArtifactPolicy) -> str:
    """Compute the new gitignore content for the requested policy."""
    without_block = _remove_managed_artifact_block(content)
    if policy is ArtifactPolicy.local:
        return _append_managed_artifact_block(without_block)
    return without_block


def has_managed_artifact_block(content: str) -> bool:
    return (
        ARTIFACT_IGNORE_BLOCK_START in content
        and ARTIFACT_IGNORE_BLOCK_END in content
        and all(line in content for line in MANAGED_IGNORE_LINES)
    )


def _append_managed_artifact_block(content: str) -> str:
    block = _managed_artifact_block()
    if not content.strip():
        return f"{block}\n"
    return f"{content.rstrip()}\n\n{block}\n"


def _remove_managed_artifact_block(content: str) -> str:
    start = content.find(ARTIFACT_IGNORE_BLOCK_START)
    if start == -1:
        return content
    end = content.find(ARTIFACT_IGNORE_BLOCK_END, start)
    if end == -1:
        return content
    end += len(ARTIFACT_IGNORE_BLOCK_END)
    return _normalise_gitignore_content(content[:start] + content[end:])


def _normalise_gitignore_content(content: str) -> str:
    stripped = content.strip("\n")
    return f"{stripped}\n" if stripped else ""


def _managed_artifact_block() -> str:
    return "\n".join(
        [ARTIFACT_IGNORE_BLOCK_START, *MANAGED_IGNORE_LINES, ARTIFACT_IGNORE_BLOCK_END]
    )
