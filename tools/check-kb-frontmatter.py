#!/usr/bin/env python3
"""KB frontmatter contract enforcement.

Every `knowledge-base/*.md` file (and `skills/<name>/SKILL.md`) declares a
machine-readable frontmatter block that agents use for load decisions. Without
mechanical enforcement, drift accumulates silently — keys go missing, cross_refs
point at renamed files, the load_when keyword goes stale.

This hook validates two things:

1. Required keys are present and non-empty.
2. cross_refs entries resolve to existing files.

Usage (pre-commit passes paths as args; CLI accepts paths or scans defaults):

    python tools/check-kb-frontmatter.py [path ...]

Exit codes:

    0  all files conform
    1  one or more files violate the contract (details printed to stderr)

Skip flag: set CLAUDE_SKIP_KB_FRONTMATTER=1 to bypass for emergencies.
"""

from __future__ import annotations

import datetime
import os
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KB_DIR = REPO_ROOT / "knowledge-base"
SKILLS_DIR = REPO_ROOT / "skills"

# `verified` is a manual review date. Stale dates are surfaced as a non-blocking
# WARNING, never a hard error: a hard gate would make CI go red purely because
# time passed with no code change. The warning prompts a re-review; it does not
# fail the build.
VERIFIED_STALE_DAYS = 180

KB_REQUIRED_KEYS = {
    "id",
    "size",
    "tldr",
    "load_when",
    "audience",
    "canonical_for",
    "cross_refs",
    "verified",
}

SKILL_REQUIRED_KEYS = {"name", "description", "user-invocable", "license"}

FRONTMATTER_PATTERN = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
HEADING_PATTERN = re.compile(r"^#+\s+(.+)$", re.MULTILINE)


class CheckError(Exception):
    """A frontmatter contract violation."""


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    match = FRONTMATTER_PATTERN.match(text)
    if not match:
        raise CheckError(f"{path}: missing frontmatter block (expected --- ... ---)")
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError as exc:
        raise CheckError(f"{path}: invalid YAML in frontmatter — {exc}") from exc
    if not isinstance(data, dict):
        raise CheckError(f"{path}: frontmatter is not a YAML mapping")
    return data


def split_cross_refs(value: object) -> list[str]:
    """cross_refs may be a comma-separated string, a list, or 'all KB files'."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        if value.strip().lower().startswith("all"):
            return []  # sentinel value used by INDEX/CHEATSHEET — skip resolution
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def check_kb_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = parse_frontmatter(path)
    except CheckError as exc:
        return [str(exc)]

    missing = KB_REQUIRED_KEYS - data.keys()
    if missing:
        errors.append(f"{path}: missing required keys: {', '.join(sorted(missing))}")

    errors.extend(
        f"{path}: required key '{key}' is empty"
        for key in KB_REQUIRED_KEYS & data.keys()
        if data[key] in (None, "", [], {})
    )

    for ref in split_cross_refs(data.get("cross_refs")):
        target, _, heading = ref.partition("§")
        target = target.strip()
        heading = heading.strip()
        target_path = _resolve_cross_ref_target(path, target)
        if target_path is None:
            errors.append(f"{path}: cross_refs entry '{target}' does not resolve")
            continue
        if heading and not _heading_resolves(
            _normalize_heading(heading), _extract_headings(target_path)
        ):
            errors.append(
                f"{path}: cross_refs entry '{target}' does not contain heading '{heading}'"
            )

    return errors


def _resolve_cross_ref_target(path: Path, target: str) -> Path | None:
    candidates = [
        KB_DIR / target,
        REPO_ROOT / target,
        path.parent / target,
    ]
    return next((candidate for candidate in candidates if candidate.exists()), None)


def _extract_headings(path: Path) -> set[str]:
    return {_normalize_heading(heading) for heading in HEADING_PATTERN.findall(path.read_text())}


def _normalize_heading(raw: str) -> str:
    text = raw.strip().strip("`").rstrip(".,;:)").strip()
    text = re.sub(r"\s*\*?\([^)]*\)?\*?\s*$", "", text).strip()
    text = re.sub(r"\s*—\s+.*$", "", text).strip()
    return re.sub(r"^\d+\.\s+", "", text).strip()


def _heading_resolves(heading: str, headings: set[str]) -> bool:
    if heading in headings:
        return True
    return sum(candidate.startswith(f"{heading} ") for candidate in headings) == 1


def _parse_verified(value: object) -> datetime.date | None:
    """Coerce a `verified` value to a date. YAML parses unquoted ISO dates to
    `datetime.date`; quoted values arrive as `str`. Returns None if unparseable
    (the missing/empty case is already covered by the required-key check)."""
    if isinstance(value, datetime.date):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def freshness_warnings(kb_files: list[Path], today: datetime.date | None = None) -> list[str]:
    """Non-blocking staleness warnings for KB files whose `verified` date is old."""
    today = today or datetime.datetime.now(datetime.UTC).date()
    warnings: list[str] = []
    for path in kb_files:
        try:
            data = parse_frontmatter(path)
        except CheckError:
            continue  # malformed frontmatter is already reported as an error
        verified = _parse_verified(data.get("verified"))
        if verified is None:
            continue  # missing/invalid `verified` is the required-key check's job
        age = (today - verified).days
        if age > VERIFIED_STALE_DAYS:
            warnings.append(
                f"{path}: verified {verified.isoformat()} is {age} days old "
                f"(> {VERIFIED_STALE_DAYS}); re-review the content and bump `verified`."
            )
    return warnings


def check_skill_file(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = parse_frontmatter(path)
    except CheckError as exc:
        return [str(exc)]

    missing = SKILL_REQUIRED_KEYS - data.keys()
    if missing:
        errors.append(f"{path}: missing required keys: {', '.join(sorted(missing))}")

    errors.extend(
        f"{path}: required key '{key}' is empty"
        for key in SKILL_REQUIRED_KEYS & data.keys()
        if data[key] in (None, "")
    )

    return errors


def classify(path: Path) -> str | None:
    """Classify a path as 'kb', 'skill', or None by shape, not location.

    KB:    any .md file under knowledge-base
    Skill: filename SKILL.md, grandparent dir named 'skills'
    """
    parts = path.parts
    if path.suffix == ".md" and "knowledge-base" in parts:
        return "kb"
    if path.name == "SKILL.md" and "skills" in parts:
        return "skill"
    return None


def discover_targets(args: list[str]) -> tuple[list[Path], list[Path]]:
    """Return (kb_files, skill_files) to check.

    With explicit args, classify each path by shape. Without args, scan the
    canonical directories under REPO_ROOT.
    """
    if args:
        kb: list[Path] = []
        skill: list[Path] = []
        for arg in args:
            path = Path(arg) if Path(arg).is_absolute() else (REPO_ROOT / arg).resolve()
            kind = classify(path)
            if kind == "kb":
                kb.append(path)
            elif kind == "skill":
                skill.append(path)
        return kb, skill

    # Top-level KB plus shipped language conventions. `workspaces/` stays
    # excluded deliberately: its files are seeded per-adopter content, not
    # shipped KB, so the contract does not apply to them.
    kb = sorted(p for p in KB_DIR.glob("*.md"))
    kb.extend(sorted((KB_DIR / "languages").glob("*.md")))
    skill = sorted(SKILLS_DIR.glob("*/SKILL.md"))
    return kb, skill


def main(argv: list[str]) -> int:
    if os.environ.get("CLAUDE_SKIP_KB_FRONTMATTER") == "1":
        return 0

    kb_files, skill_files = discover_targets(argv[1:])
    all_errors: list[str] = []

    for path in kb_files:
        all_errors.extend(check_kb_file(path))
    for path in skill_files:
        all_errors.extend(check_skill_file(path))

    # Non-blocking: surface stale `verified` dates without failing the run.
    warnings = freshness_warnings(kb_files)
    if warnings:
        print("⚠ KB staleness warnings (non-blocking):\n", file=sys.stderr)
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)
        print("", file=sys.stderr)

    if all_errors:
        print("✗ KB frontmatter contract violations:\n", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nKB contract: id, size, tldr, load_when, audience, canonical_for, "
            "cross_refs, verified.\nSkill contract: name, description, "
            "user-invocable, license.\nWhy: knowledge-base/INDEX.md § Loading "
            "Rule. Skip: CLAUDE_SKIP_KB_FRONTMATTER=1.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
