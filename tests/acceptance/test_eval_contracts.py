"""Contract tests for committed eval markdown files."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from deploy_ai_playbook.cli import get_source_root
from tests.acceptance.contract_data import AGENT_CONTRACTS


def _read_eval(filename: str) -> str:
    source_root = get_source_root()
    return (source_root / "evals" / filename).read_text()


def test_every_agent_has_an_eval_pair():
    """Every agent ships with all six required eval artifacts.

    Adding agent #N must touch all of these in the same PR — a partial
    add (e.g. forgot the rubric.json) silently shrinks coverage. Earlier
    versions of this test only checked the two main markdown files; the
    extension catches drift on the adversarial pair, the sample file
    used by `eval-drift.yml`'s LLM judge, and the schema-backed rubric.
    """
    source_root = get_source_root()
    evals_dir = source_root / "evals"
    failures: list[str] = []
    for agent_name in AGENT_CONTRACTS:
        required = {
            "input": evals_dir / f"{agent_name}-input.md",
            "expected": evals_dir / f"{agent_name}-expected.md",
            "adversarial-input": evals_dir / f"{agent_name}-adversarial-input.md",
            "adversarial-expected": evals_dir / f"{agent_name}-adversarial-expected.md",
            "sample": evals_dir / "samples" / f"{agent_name}.md",
            "rubric": evals_dir / "rubrics" / f"{agent_name}.json",
        }
        for label, path in required.items():
            if not path.exists():
                rel = path.relative_to(source_root)
                failures.append(f"{agent_name}: missing {label} eval artifact at {rel}")
    assert not failures, "Incomplete eval coverage:\n  " + "\n  ".join(failures)


def test_eval_expected_files_have_required_sections():
    # STRUCTURE-MARKER: rubric section headings — presence is the contract;
    # the prose inside each section is free to change.
    required_sections = [
        r"## Must (demonstrate|identify|Fix)",
        r"## Must NOT",
        r"## Quality signals",
    ]
    for agent_name in AGENT_CONTRACTS:
        content = _read_eval(f"{agent_name}-expected.md")
        for pattern in required_sections:
            assert re.search(pattern, content), (
                f"evals/{agent_name}-expected.md missing section matching: {pattern}"
            )


def test_eval_expected_files_cite_kb():
    # STRUCTURE-MARKER: every rubric must ground its criteria in at least one
    # KB citation; which KB file it cites is free.
    kb_reference_pattern = re.compile(
        r"`(?:knowledge-base/)?(?:\w[\w-]*\.md)`|"
        r"(?:security|testing|design-patterns|observability|performance|"
        r"style-guide|refactoring|feature-flags|philosophy|"
        r"working-agreement)\.md"
    )
    for agent_name in AGENT_CONTRACTS:
        content = _read_eval(f"{agent_name}-expected.md")
        matches = kb_reference_pattern.findall(content)
        assert matches, (
            f"evals/{agent_name}-expected.md has no KB file references — "
            f"eval criteria should be grounded in knowledge base"
        )


def test_eval_input_files_are_non_empty():
    for agent_name in AGENT_CONTRACTS:
        content = _read_eval(f"{agent_name}-input.md").strip()
        assert len(content) > 50, (
            f"evals/{agent_name}-input.md is too short ({len(content)} chars) — "
            f"needs a meaningful scenario"
        )


# ---------------------------------------------------------------------------
# Rubric schema validation
#
# `evals/rubrics/_schema.json` is the source of truth for rubric shape; this
# test enforces it with stdlib (no jsonschema dep). Catches typos like
# `must_demostrate` and id-pattern drift before the LLM judge ever runs.
# ---------------------------------------------------------------------------


_RUBRIC_TOP_REQUIRED = {"agent", "version", "must_demonstrate", "must_not", "quality_signals"}
_RUBRIC_ITEM_REQUIRED = {"id", "criterion", "keywords"}
_RUBRIC_ITEM_ALLOWED = _RUBRIC_ITEM_REQUIRED | {"evidence"}
_RUBRIC_AGENT_RE = re.compile(r"^[a-z][a-z0-9-]*$")
_RUBRIC_ITEM_ID_RE = re.compile(r"^[A-Z][A-Z0-9-]+-(MUST|NOT|QUALITY)-\d{3,4}$")


def _rubric_validation_errors(path: Path, data: Any) -> list[str]:
    name = path.name
    if not isinstance(data, dict):
        return [f"{name}: top-level must be a JSON object"]
    errors = list(_top_level_errors(name, path.stem, data))
    for section in ("must_demonstrate", "must_not", "quality_signals"):
        items = data.get(section)
        if not isinstance(items, list):
            errors.append(f"{name}: {section} must be a list")
            continue
        for index, item in enumerate(items):
            errors.extend(_rubric_item_errors(name, section, index, item))
    return errors


def _top_level_errors(name: str, stem: str, data: dict[str, Any]) -> list[str]:
    """Top-level shape: required keys, no extras, agent matches stem, version is 1."""
    errors: list[str] = []
    keys = set(data.keys())
    missing = _RUBRIC_TOP_REQUIRED - keys
    extra = keys - _RUBRIC_TOP_REQUIRED
    if missing:
        errors.append(f"{name}: missing top-level keys {sorted(missing)}")
    if extra:
        errors.append(f"{name}: unexpected top-level keys {sorted(extra)}")
    agent = data.get("agent")
    if isinstance(agent, str):
        if not _RUBRIC_AGENT_RE.match(agent):
            errors.append(f"{name}: agent={agent!r} is not kebab-case")
        if agent != stem:
            errors.append(f"{name}: agent={agent!r} does not match filename stem {stem!r}")
    if data.get("version") != 1:
        errors.append(f"{name}: version must be 1, got {data.get('version')!r}")
    return errors


def _rubric_item_errors(name: str, section: str, index: int, item: Any) -> list[str]:
    prefix = f"{name}:{section}[{index}]"
    if not isinstance(item, dict):
        return [f"{prefix}: not a JSON object"]
    out: list[str] = []
    keys = set(item.keys())
    missing = _RUBRIC_ITEM_REQUIRED - keys
    extra = keys - _RUBRIC_ITEM_ALLOWED
    if missing:
        out.append(f"{prefix}: missing keys {sorted(missing)}")
    if extra:
        out.append(f"{prefix}: unexpected keys {sorted(extra)}")
    item_id = item.get("id")
    if isinstance(item_id, str) and not _RUBRIC_ITEM_ID_RE.match(item_id):
        out.append(f"{prefix}: id={item_id!r} does not match expected pattern")
    keywords = item.get("keywords")
    if not isinstance(keywords, list) or not keywords:
        out.append(f"{prefix}: keywords must be a non-empty list")
    elif not all(isinstance(k, str) and k for k in keywords):
        out.append(f"{prefix}: keywords entries must be non-empty strings")
    criterion = item.get("criterion")
    if not isinstance(criterion, str) or len(criterion) < 10:
        out.append(f"{prefix}: criterion must be a non-trivial string")
    return out


def test_every_rubric_validates_against_the_schema():
    """Every `evals/rubrics/<agent>.json` must satisfy `_schema.json`."""
    rubrics_dir = get_source_root() / "evals" / "rubrics"
    failures: list[str] = []
    for path in sorted(rubrics_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        with path.open(encoding="utf-8") as fh:
            data = json.load(fh)
        failures.extend(_rubric_validation_errors(path, data))
    assert not failures, "Rubric schema violations:\n  " + "\n  ".join(failures)


def test_rubric_ids_are_unique_within_each_section():
    """Duplicate ids in the same section silently mask coverage."""
    rubrics_dir = get_source_root() / "evals" / "rubrics"
    failures: list[str] = []
    for path in sorted(rubrics_dir.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        for section in ("must_demonstrate", "must_not", "quality_signals"):
            seen: set[str] = set()
            for item in data.get(section, []):
                item_id = item.get("id")
                if item_id in seen:
                    failures.append(f"{path.name}:{section}: duplicate id {item_id!r}")
                if isinstance(item_id, str):
                    seen.add(item_id)
    assert not failures, "Duplicate rubric ids:\n  " + "\n  ".join(failures)


ADVERSARIAL_EVAL_NAMES = {
    "code-inspector-adversarial",
    "diff-reviewer-adversarial",
    "docs-maintainer-adversarial",
    "incident-responder-adversarial",
    "release-captain-adversarial",
    "slice-planner-adversarial",
    "story-refiner-adversarial",
    "xp-pair-programmer-adversarial",
}


def test_no_orphan_eval_files():
    source_root = get_source_root()
    evals_dir = source_root / "evals"
    eval_files = sorted(evals_dir.glob("*.md"))
    for eval_file in eval_files:
        stem = eval_file.stem
        suffix = stem.split("-")[-1]
        agent_name = stem.rsplit(f"-{suffix}", 1)[0]
        is_known = agent_name in AGENT_CONTRACTS or agent_name in ADVERSARIAL_EVAL_NAMES
        assert is_known, f"Orphan eval file {eval_file.name} — no matching agent '{agent_name}'"


def test_sample_subdirectory_files_map_to_known_rubrics():
    """Files under samples/adversarial/ and samples/negative/ must map to rubrics.

    The eval-drift judge loops derive the rubric name from the filename stem;
    an orphan would make the weekly run judge against the wrong rubric or
    crash. Negative controls may target either a standard agent or an
    adversarial eval.
    """
    source_root = get_source_root()
    samples_dir = source_root / "evals" / "samples"
    failures: list[str] = []

    for path in sorted((samples_dir / "adversarial").glob("*.md")):
        if path.name == "README.md":
            continue
        if path.stem not in ADVERSARIAL_EVAL_NAMES:
            failures.append(f"adversarial/{path.name}: no matching adversarial eval pair")

    for path in sorted((samples_dir / "negative").glob("*.md")):
        if path.name == "README.md":
            continue
        if path.stem not in AGENT_CONTRACTS and path.stem not in ADVERSARIAL_EVAL_NAMES:
            failures.append(f"negative/{path.name}: no matching rubric")
        # STRUCTURE-MARKER: negative controls must self-declare so a reader
        # (or the judge-output artifact) can't mistake them for baselines.
        if "negative_control" not in path.read_text(encoding="utf-8"):
            failures.append(f"negative/{path.name}: missing `negative_control:` front-matter")

    assert not failures, "Orphan or unmarked sample files:\n  " + "\n  ".join(failures)
