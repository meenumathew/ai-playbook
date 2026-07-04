"""Cross-agent handoff contracts over the committed eval baselines.

The eval harness judges each agent's baseline against its own rubric in
isolation; nothing previously asserted that one agent's output satisfies the
NEXT agent's input contract. These tests chain the committed baselines:
story-refiner's output must not trip slice-planner's STOP conditions, and
slice-planner's output must give xp-pair-programmer what its TDD loop needs.

All assertions here are STRUCTURE-MARKER: they check that contract elements
exist (anchors, AC with tests, slices with RED steps), never exact prose.
"""

from __future__ import annotations

import re

from deploy_ai_playbook.cli import get_source_root

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _load_sample(agent_name: str) -> str:
    path = get_source_root() / "evals" / "samples" / f"{agent_name}.md"
    return _FRONTMATTER_RE.sub("", path.read_text(encoding="utf-8"))


def test_story_refiner_output_satisfies_slice_planner_input_contract():
    """slice-planner step 1 STOPs without AC and reads the five anchors —
    story-refiner's baseline must hand over both."""
    sample = _load_sample("story-refiner")

    # STRUCTURE-MARKER: the five intent anchors must be present by name.
    for anchor in (
        "Problem",
        "Desired outcome",
        "Why now",
        "Key constraint",
        "Smallest useful change",
    ):
        assert anchor in sample, f"story-refiner baseline missing anchor: {anchor}"

    # STRUCTURE-MARKER: AC in Given/When/Then shape — the no-AC STOP gate
    # in slice-planner must not fire on a refined story.
    given_when_then = re.findall(r"Given .+?, when .+?, then .+", sample, re.IGNORECASE)
    assert len(given_when_then) >= 3, (
        f"expected >=3 Given/When/Then AC, found {len(given_when_then)}"
    )

    # STRUCTURE-MARKER: one named test per AC (the one-test-per-AC rule).
    test_names = re.findall(r"Test: `?(test_\w+)`?", sample)
    assert len(test_names) >= len(given_when_then), (
        "every AC must name its test before the slice-planner handoff"
    )


def test_slice_planner_output_satisfies_xp_pair_programmer_input_contract():
    """xp-pair-programmer's outer loop needs ordered slices, a RED step per
    slice, and named test checkpoints — slice-planner's baseline must
    provide all three."""
    sample = _load_sample("slice-planner")

    # STRUCTURE-MARKER: at least two ordered slices.
    slices = re.findall(r"### Slice \d+", sample)
    assert len(slices) >= 2, f"expected >=2 slices, found {len(slices)}"

    # STRUCTURE-MARKER: TDD entry point — every slice plan starts from RED.
    assert "RED" in sample, "plan must mark RED steps for the TDD loop"

    # STRUCTURE-MARKER: named, runnable test checkpoints.
    checkpoints = re.findall(r"test_\w+", sample)
    assert len(checkpoints) >= len(slices), "each slice needs at least one named test checkpoint"


def _normalized_test_names(text: str) -> set[str]:
    """Test names with the layer prefix stripped — the plan promotes a story's
    `test_<behaviour>` AC name to `test_ac_<behaviour>` when it becomes the
    outer acceptance test, so chains compare on the behaviour part."""
    return {re.sub(r"^test_(ac_)?", "", name) for name in re.findall(r"test_\w+", text)}


def test_chained_baselines_describe_the_same_story():
    """The handoff is only meaningful if both baselines describe one story —
    a shared test behaviour proves the chain is continuous, not coincidental."""
    story_tests = _normalized_test_names(_load_sample("story-refiner"))
    plan_tests = _normalized_test_names(_load_sample("slice-planner"))

    assert story_tests & plan_tests, (
        "slice-planner baseline shares no test behaviours with story-refiner's AC — "
        "the committed baselines no longer chain into one story"
    )
