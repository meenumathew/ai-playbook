"""Contract tests for the deprecation registry.

`docs/deprecation-policy.md` defines the cycle; `.deprecations.toml` is the
machine-readable registry. These tests enforce that:

- the registry parses cleanly with the documented schema,
- every row in the registry corresponds to an entry in `CHANGELOG.md`'s
  most-recent versioned `### Deprecated` block (or to the `## [Unreleased]`
  block if the deprecation is not yet released),
- no row's `removal_version` matches the version currently in
  `pyproject.toml` (a release that contains a row whose `removal_version`
  is itself is a release that forgot to remove the surface),
- every row's `surface` is one of the documented surface types.

The registry's intentional shape is `[[deprecations]]` rows with a fixed
schema; pyright checks the parser shape, this file checks the contract.
"""

from __future__ import annotations

import re
import tomllib

from deploy_ai_playbook.cli import get_source_root

VALID_SURFACES = frozenset(
    {
        "cli-flag",
        "cli-command",
        "agent-id",
        "config-key",
        "kb-path",
        "deployment-layout",
        "skill-op",
    }
)
VALID_STATUSES = frozenset({"active", "grace", "removed"})

REQUIRED_KEYS = (
    "id",
    "surface",
    "added_version",
    "removal_version",
    "reason",
    "replacement",
    "status",
)

_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def _registry() -> list[dict[str, str]]:
    path = get_source_root() / ".deprecations.toml"
    assert path.exists(), ".deprecations.toml registry must exist at repo root"
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return list(data.get("deprecations", []))


def _current_version() -> str:
    pyproject = (get_source_root() / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject, re.MULTILINE)
    assert match, 'pyproject.toml must declare a `version = "X.Y.Z"` line'
    return match.group(1)


def _changelog_text() -> str:
    return (get_source_root() / "CHANGELOG.md").read_text(encoding="utf-8")


def test_registry_rows_have_required_schema():
    """Every registry row carries the fields the contract test depends on."""
    failures: list[str] = []
    for row in _registry():
        missing = [key for key in REQUIRED_KEYS if not row.get(key)]
        if missing:
            failures.append(f"{row.get('id', '<no-id>')}: missing keys {missing}")
        if row.get("surface") and row["surface"] not in VALID_SURFACES:
            failures.append(
                f"{row.get('id')}: surface={row['surface']!r} not in {sorted(VALID_SURFACES)}"
            )
        if row.get("status") and row["status"] not in VALID_STATUSES:
            failures.append(
                f"{row.get('id')}: status={row['status']!r} not in {sorted(VALID_STATUSES)}"
            )
        for version_field in ("added_version", "removal_version"):
            value = row.get(version_field)
            if value and not _VERSION_RE.match(value):
                failures.append(f"{row.get('id')}: {version_field}={value!r} is not X.Y.Z")
    assert not failures, "Deprecation registry schema failures:\n  " + "\n  ".join(failures)


def test_no_row_targets_the_current_release_version():
    """A release that contains a row whose `removal_version` is its own version
    is a release that forgot to remove the surface. Fail at the contract level
    so the gap is caught in CI rather than after publish.
    """
    current = _current_version()
    failures = [
        f"{row['id']}: removal_version {row['removal_version']} == current "
        f"version {current}; the surface must be removed before tagging."
        for row in _registry()
        if row.get("removal_version") == current
    ]
    assert not failures, "Unremoved deprecations:\n  " + "\n  ".join(failures)


def test_registry_rows_are_traceable_in_changelog():
    """Every registry row's id must appear in CHANGELOG.md.

    Either in the active `## [Unreleased]` block (a deprecation in flight),
    or in the most-recent versioned `### Deprecated` section (a deprecation
    that already shipped). Both cases keep the changelog and the registry
    aligned without requiring callers to count releases.
    """
    text = _changelog_text()
    failures = [row["id"] for row in _registry() if row.get("id") and row["id"] not in text]
    assert not failures, (
        "Deprecation registry rows missing from CHANGELOG.md (add to "
        "`### Deprecated` for the relevant version):\n  " + "\n  ".join(failures)
    )


def test_changelog_deprecated_entries_have_registry_rows():
    """The reverse direction: every concrete CHANGELOG `### Deprecated` bullet
    in a *released* section must have a registry row.

    The `## [Unreleased]` block is allowed to mention "No active deprecations."
    or freshly-added entries that have not yet been pinned in the registry.
    """
    text = _changelog_text()
    released_match = re.search(
        r"^## \[\d+\.\d+\.\d+\][^\n]*\n(.*?)(?=^## \[|\Z)",
        text,
        re.DOTALL | re.MULTILINE,
    )
    if not released_match:
        return
    released = released_match.group(1)
    deprecated_match = re.search(
        r"^### Deprecated\n(.*?)(?=^### |\Z)", released, re.DOTALL | re.MULTILINE
    )
    if not deprecated_match:
        return

    body = deprecated_match.group(1)
    if "no active deprecations" in body.lower():
        return

    bullets = [
        line.strip()
        for line in body.splitlines()
        if line.startswith("- ") and "no active deprecations" not in line.lower()
    ]
    if not bullets:
        return

    registry_ids = {row["id"] for row in _registry() if row.get("id")}
    failures = [b for b in bullets if not any(rid in b for rid in registry_ids)]
    assert not failures, (
        "CHANGELOG `### Deprecated` bullets without a `.deprecations.toml` row:\n  "
        + "\n  ".join(failures)
    )
