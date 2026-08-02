"""Cross-agent handoff contracts over the committed eval baselines.

The eval harness judges each agent's baseline against its own rubric in
isolation; nothing previously asserted that one agent's output satisfies the
NEXT agent's input contract. These tests chain the committed baselines across
the full default workflow. Build half: story-refiner's output must not trip
slice-planner's STOP conditions, and slice-planner's output must give
xp-pair-programmer what its TDD loop needs. Ship half: xp-pair-programmer's
run must give diff-reviewer per-AC test evidence, diff-reviewer's record must
give release-captain a verdict to gate on, and all baselines must keep
narrating one story.

All assertions here are STRUCTURE-MARKER: they check that contract elements
exist (anchors, AC with tests, slices with RED steps), never exact prose.
"""

from __future__ import annotations

import re

import pytest

from deploy_ai_playbook.cli import get_source_root

pytestmark = pytest.mark.repo_contract

_FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)


def _load_sample(agent_name: str) -> str:
    path = get_source_root() / "evals" / "samples" / f"{agent_name}.md"
    return _FRONTMATTER_RE.sub("", path.read_text(encoding="utf-8"))


def test_story_refiner_output_satisfies_slice_planner_input_contract():
    """slice-planner step 1 STOPs without AC and reads the five anchors:
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

    # STRUCTURE-MARKER: AC in Given/When/Then shape: the no-AC STOP gate
    # in slice-planner must not fire on a refined story.
    given_when_then = re.findall(r"Given .+?, when .+?, then .+", sample, re.IGNORECASE)
    assert len(given_when_then) >= 3, (
        f"expected >=3 Given/When/Then AC, found {len(given_when_then)}"
    )

    # STRUCTURE-MARKER: one named test per AC (the one-test-per-AC rule).
    # Both AC-to-test mapping formats count: inline "Test: `test_x`" and the
    # story template's "## TDD Test Names" list ("- `test_x`: AC 1").
    test_names = re.findall(r"Test: `?(test_\w+)`?", sample)
    test_names += re.findall(r"(?m)^\s*-\s*`(test_\w+)`:", sample)
    assert len(test_names) >= len(given_when_then), (
        "every AC must name its test before the slice-planner handoff"
    )


def test_slice_planner_output_satisfies_xp_pair_programmer_input_contract():
    """xp-pair-programmer's outer loop needs ordered slices, a RED step per
    slice, and named test checkpoints: slice-planner's baseline must
    provide all three."""
    sample = _load_sample("slice-planner")

    # STRUCTURE-MARKER: at least two ordered slices.
    slices = re.findall(r"### Slice \d+", sample)
    assert len(slices) >= 2, f"expected >=2 slices, found {len(slices)}"

    # STRUCTURE-MARKER: TDD entry point: every slice plan starts from RED.
    assert "RED" in sample, "plan must mark RED steps for the TDD loop"

    # STRUCTURE-MARKER: named, runnable test checkpoints.
    checkpoints = re.findall(r"test_\w+", sample)
    assert len(checkpoints) >= len(slices), "each slice needs at least one named test checkpoint"


def test_xp_pair_programmer_output_satisfies_diff_reviewer_input_contract():
    """diff-reviewer's AC-coverage step needs per-task test evidence:
    xp-pair-programmer's baseline must name its tests and show the
    RED-then-verify discipline the review checks for."""
    sample = _load_sample("xp-pair-programmer")

    # STRUCTURE-MARKER: every task section names at least one runnable test.
    tasks = re.split(r"(?m)^## Task ", sample)[1:]
    assert len(tasks) >= 2, f"expected >=2 task sections, found {len(tasks)}"
    for number, task in enumerate(tasks, start=1):
        assert re.search(r"test_\w+", task), (
            f"Task {number} names no test — diff-reviewer's AC-coverage table has nothing to cite"
        )

    # STRUCTURE-MARKER: RED shown before GREEN, and a verification command run.
    assert "RED" in sample, "baseline must show the failing-first step"
    assert "uv run pytest" in sample, "baseline must show the verification command it ran"


def test_diff_reviewer_output_satisfies_release_captain_input_contract():
    """release-captain gates on an explicit review record: diff-reviewer's
    baseline must carry a verdict and per-AC coverage status. Shape only:
    the verdict's outcome (approve / request changes) is the review's call."""
    sample = _load_sample("diff-reviewer")

    # STRUCTURE-MARKER: an explicit verdict section with a decision in it.
    verdict = re.search(r"(?m)^## Verdict\n+(.+)", sample)
    assert verdict, "review must open with a ## Verdict section"
    assert re.search(r"approve|request changes", verdict.group(1), re.IGNORECASE), (
        "verdict must state a decision release-captain can gate on"
    )

    # STRUCTURE-MARKER: per-AC coverage table with a status column.
    assert re.search(r"\|\s*AC\s*\|.*\|\s*Status\s*\|", sample), (
        "review must carry the AC-coverage table release gates read"
    )

    # STRUCTURE-MARKER: findings cite tests by name, closing the loop to
    # what xp-pair-programmer ran or still owes.
    assert re.search(r"test_\w+", sample), "review must reference named tests as evidence"


def _normalized_test_names(text: str) -> set[str]:
    """Test names normalized to the behaviour part so chains compare intent."""
    return {re.sub(r"^test_", "", name) for name in re.findall(r"test_\w+", text)}


def test_chained_baselines_describe_the_same_story():
    """The handoff is only meaningful if both baselines describe one story:
    a shared test behaviour proves the chain is continuous, not coincidental."""
    story_tests = _normalized_test_names(_load_sample("story-refiner"))
    plan_tests = _normalized_test_names(_load_sample("slice-planner"))

    assert story_tests & plan_tests, (
        "slice-planner baseline shares no test behaviours with story-refiner's AC — "
        "the committed baselines no longer chain into one story"
    )


def test_ship_half_baselines_continue_the_same_story():
    """The ship half only chains if the baselines keep narrating one story:
    the review must cite a behaviour the implementation ran, and the release
    must name the story artifact whose behaviours were reviewed."""
    xp_tests = _normalized_test_names(_load_sample("xp-pair-programmer"))
    review_tests = _normalized_test_names(_load_sample("diff-reviewer"))
    release_sample = _load_sample("release-captain")

    # STRUCTURE-MARKER: implementation and review share a test behaviour.
    assert xp_tests & review_tests, (
        "diff-reviewer baseline shares no test behaviours with "
        "xp-pair-programmer's run — the ship-half handoff broke"
    )

    # STRUCTURE-MARKER: the release names a story artifact (release-captain
    # works from artifacts, not test names) whose slug tokens appear in the
    # reviewed behaviours' vocabulary.
    story_ref = re.search(r"STORY-\d+-([\w-]+)\.md", release_sample)
    assert story_ref, "release-captain baseline must name the story artifact"
    review_vocabulary = " ".join(review_tests)
    slug_tokens = story_ref.group(1).split("-")
    shared = [token for token in slug_tokens if token in review_vocabulary]
    assert shared, (
        f"story slug '{story_ref.group(1)}' shares no vocabulary with the "
        "reviewed test behaviours — the release baseline drifted to a "
        "different story"
    )


def test_samples_readme_names_all_chain_members():
    """The samples README warns that chain membership couples baseline
    rewrites: the warning is only honest if it names every member."""
    readme = (get_source_root() / "evals" / "samples" / "README.md").read_text(encoding="utf-8")
    chain_note = readme[readme.index("Chained baselines") :]
    for agent in (
        "story-refiner",
        "slice-planner",
        "xp-pair-programmer",
        "diff-reviewer",
        "release-captain",
    ):
        assert agent in chain_note, f"samples README chain note must name {agent} as a chain member"


def test_retrospective_skill_is_reachable_from_closing_agents():
    """The retrospective skill only fires if the chain's closing agents offer
    it: story close (xp-pair-programmer), audit close (code-inspector), and
    release close (release-captain) must each hand off to the skill."""
    root = get_source_root()
    for agent in ("xp-pair-programmer", "code-inspector", "release-captain"):
        text = (root / "agents" / f"{agent}.agent.md").read_text(encoding="utf-8")
        # STRUCTURE-MARKER: the skill path is the wiring; offer wording is free.
        assert "skills/retrospective" in text, (
            f"{agent} must offer skills/retrospective after its closing step"
        )
