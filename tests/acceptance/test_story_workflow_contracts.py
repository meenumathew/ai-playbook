"""Contract tests for story-shape handling and story templates.

These tests pin *behavioural* invariants — that each agent and template
documents the four work shapes, regression-test-first for bugs, spike
short-circuit, etc. They deliberately avoid pinning prose position
(`.find()` + slice) or exact heading wording, so legitimate copy-edits
and section reorderings do not produce false failures.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from deploy_ai_playbook.cli import get_source_root

# ---------------------------------------------------------------------------
# Lightweight markdown parsing — no positional pinning
# ---------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)


def _frontmatter(text: str) -> dict[str, object]:
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}


def _ordered_headings(text: str) -> list[tuple[int, str]]:
    """Headings in document order, as (level, normalized_text) pairs."""
    return [(len(m.group(1)), m.group(2).strip().lower()) for m in _HEADING_RE.finditer(text)]


def _heading_index(headings: list[tuple[int, str]], substring: str) -> int:
    needle = substring.lower()
    for i, (_, text) in enumerate(headings):
        if needle in text:
            return i
    return -1


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# slice-planner: spike short-circuit + bug-stories slice rule
# ---------------------------------------------------------------------------


def test_slice_planner_handles_bug_and_spike_types():
    agent = _read(get_source_root() / "agents" / "slice-planner.agent.md")

    # Spike short-circuit: agent must explicitly stop on `type: spike` and
    # name research/RESEARCH- as the deliverable. The check is anchored by
    # the canonical token "type: spike", not by section headings.
    assert re.search(r"`type:\s*spike`.*\bSTOP\b", agent, re.DOTALL | re.IGNORECASE), (
        "slice-planner must STOP when story `type: spike`"
    )
    assert "research/RESEARCH-" in agent, (
        "slice-planner spike short-circuit must point at research/RESEARCH-NNN deliverable"
    )

    # Bug stories: first slice is the regression test that fails first.
    assert re.search(r"`type:\s*bug`", agent), "slice-planner must classify `type: bug` stories"
    assert re.search(r"regression\s+test", agent, re.IGNORECASE), (
        "slice-planner must require a regression test for bug stories"
    )
    assert re.search(r"fail(ing|s)?", agent, re.IGNORECASE), (
        "slice-planner regression-test slice must require an initial failure (RED)"
    )


# ---------------------------------------------------------------------------
# xp-pair-programmer: work-shape classification + spike STOP
# ---------------------------------------------------------------------------


def test_xp_pair_short_circuits_on_spike_and_handles_bug_type():
    agent = _read(get_source_root() / "agents" / "xp-pair-programmer.agent.md")

    # All four work shapes must be documented as `type: <shape>`. We do not
    # pin where in the file they appear.
    for shape in ("story", "bug", "spike", "chore"):
        assert re.search(rf"`type:\s*{shape}`", agent), (
            f"xp-pair-programmer must document `type: {shape}`"
        )

    # Spike triggers STOP and the bug shape requires a regression test.
    assert re.search(r"`type:\s*spike`.*\bSTOP\b", agent, re.DOTALL), (
        "xp-pair-programmer must STOP on `type: spike`"
    )
    assert re.search(r"regression\s+test", agent, re.IGNORECASE), (
        "xp-pair-programmer must require regression test for `type: bug`"
    )


# ---------------------------------------------------------------------------
# story-refiner: classify before capturing anchors
# ---------------------------------------------------------------------------


def test_story_refiner_classifies_work_shape_before_anchors():
    agent = _read(get_source_root() / "agents" / "story-refiner.agent.md")

    # Find the two procedural steps by stable substrings — not by position.
    # Both must exist and "classify" must come first in document order.
    classify_match = re.search(r"\bClassify[^\n]+work shape\b", agent, re.IGNORECASE)
    anchors_match = re.search(r"\bCapture[^\n]+intent anchors\b", agent, re.IGNORECASE)
    assert classify_match, "story-refiner must include a 'classify the work shape' step"
    assert anchors_match, "story-refiner must include a 'capture intent anchors' step"
    assert classify_match.start() < anchors_match.start(), (
        "story-refiner must classify the work shape before capturing intent anchors"
    )

    # All four shapes must be named.
    for shape in ("story", "bug", "spike", "chore"):
        assert re.search(rf"\b{shape}\b", agent, re.IGNORECASE), (
            f"story-refiner must mention the `{shape}` work shape"
        )

    # The PREFIX placeholder is part of the artifact-naming contract.
    assert "<PREFIX>-NNN" in agent, (
        "story-refiner must keep the <PREFIX>-NNN placeholder in artifact paths"
    )

    # Bug and spike paths replace the anchors step — flag presence, not phrasing.
    assert re.search(r"bug\s+path", agent, re.IGNORECASE), (
        "story-refiner must document a bug-path branch that replaces anchors"
    )
    assert re.search(r"spike\s+path", agent, re.IGNORECASE), (
        "story-refiner must document a spike-path branch that replaces anchors"
    )


# ---------------------------------------------------------------------------
# Templates: frontmatter, required structure, skill + agent wiring
# ---------------------------------------------------------------------------


def test_story_templates_per_type_wired_into_skill_and_agent():
    source_root = get_source_root()
    templates = source_root / "templates"

    # Each template must declare YAML frontmatter with a non-empty `type:`.
    expected_types = {
        "story-template.md": "story",
        "story-bug-template.md": "bug",
        "story-spike-template.md": "spike",
    }
    for filename, expected_type in expected_types.items():
        body = _read(templates / filename)
        fm = _frontmatter(body)
        assert fm, f"templates/{filename} must declare YAML frontmatter"
        assert fm.get("type") == expected_type, (
            f"templates/{filename} must declare `type: {expected_type}` in frontmatter, "
            f"got {fm.get('type')!r}"
        )

    # Bug template: structure is what slice-planner depends on. We assert
    # heading presence (case-insensitive) rather than exact wording.
    bug = _read(templates / "story-bug-template.md")
    bug_headings = {text for _, text in _ordered_headings(bug)}
    for required in ("symptom", "reproduction"):
        assert any(required in h for h in bug_headings), (
            f"story-bug-template.md must contain a top-level '{required.title()}' heading"
        )
    # Reproduction must capture observed-vs-expected behaviour somewhere.
    assert re.search(r"\bexpected\b", bug, re.IGNORECASE), (
        "story-bug-template.md must capture expected behaviour"
    )
    assert re.search(r"\bactual\b", bug, re.IGNORECASE), (
        "story-bug-template.md must capture actual behaviour"
    )

    # Spike template: the artifact contract is the deliverable + timebox.
    spike = _read(templates / "story-spike-template.md")
    assert re.search(r"^\s*deliverable\s*:", spike, re.MULTILINE | re.IGNORECASE), (
        "story-spike-template.md must declare a deliverable field"
    )
    assert re.search(r"\btimebox\b", spike, re.IGNORECASE), (
        "story-spike-template.md must declare a timebox"
    )
    assert "research/RESEARCH-" in spike, (
        "story-spike-template.md must point at research/RESEARCH-NNN deliverable"
    )

    # Skill must reference the templates by filename and document the prefixes.
    skill = _read(source_root / "skills" / "story-writing" / "SKILL.md")
    for slug in ("story-bug-template.md", "story-spike-template.md"):
        assert slug in skill, f"story-writing skill must reference templates/{slug}"
    for prefix in ("BUG-NNN-", "SPIKE-NNN-", "CHORE-NNN-"):
        assert prefix in skill, f"story-writing skill must document the {prefix} prefix"

    # Story-refiner agent must reference the bug and spike templates.
    refiner = _read(source_root / "agents" / "story-refiner.agent.md")
    for slug in ("story-bug-template.md", "story-spike-template.md"):
        assert slug in refiner, f"story-refiner must reference templates/{slug}"


def test_story_template_evidence_line_is_pointed_not_generic():
    template = _read(get_source_root() / "templates" / "story-template.md")
    headings = _ordered_headings(template)

    dod_idx = _heading_index(headings, "definition of done")
    assert dod_idx != -1, "story-template.md must contain a 'Definition of Done' section"

    # Slice the section by walking forward to the next heading at <= same level
    # or end-of-doc. This is structural, not byte-position-pinned.
    dod_level = headings[dod_idx][0]
    next_section_pattern = re.compile(rf"^#{{1,{dod_level}}}\s+\S", re.MULTILINE)
    # Find the byte offset of the DoD heading to slice the body.
    dod_heading_match = re.search(
        rf"^#{{{dod_level}}}\s+.*Definition of Done.*$", template, re.MULTILINE | re.IGNORECASE
    )
    assert dod_heading_match, "Definition of Done heading not found by structural lookup"
    body_start = dod_heading_match.end()
    next_match = next_section_pattern.search(template, body_start)
    body_end = next_match.start() if next_match else len(template)
    dod = template[body_start:body_end]

    # The evidence line must point at concrete artifacts, not generic phrasing.
    assert re.search(r"\bAC\s+walkthrough\b", dod), (
        "Definition of Done must require an AC walkthrough"
    )
    assert re.search(r"before\s*/?\s*after", dod, re.IGNORECASE), (
        "Definition of Done must capture before/after evidence"
    )
    # CONTRACT-PHRASE (negative): the literal generic catch-all phrasing
    # was explicitly removed during template review; reintroducing it
    # weakens DoD evidence. See classification convention in
    # tests/acceptance/__init__.py.
    assert "tests, screenshots, logs, rollout notes" not in dod, (
        "Definition of Done must not fall back to a generic 'tests, screenshots, logs' line"
    )
