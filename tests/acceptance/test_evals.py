"""Acceptance tests for eval harness: tests that read eval files from disk."""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "evals"))

from run_eval import (
    ADVERSARIAL_EVALS,
    AGENTS,
    RUBRICS_DIR,
    SAMPLES_DIR,
    _declared_violation_ids,
    _negative_control_paths,
    _split_front_matter,
    _violation_ids_from_texts,
    calibrate,
    calibrate_negative_controls,
    check_structure,
    parse_rubric,
    validate,
    validate_samples,
)

pytestmark = pytest.mark.repo_contract


class TestParseRubric:
    @pytest.mark.parametrize("agent", AGENTS)
    def test_parses_all_agents(self, agent):
        rubric = parse_rubric(agent)
        assert rubric.agent == agent
        assert len(rubric.must_demonstrate) > 0, f"{agent} has no must-demonstrate items"
        assert len(rubric.must_not) > 0, f"{agent} has no must-not items"
        assert len(rubric.quality_signals) > 0, f"{agent} has no quality signals"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_all_items_have_keywords(self, agent):
        rubric = parse_rubric(agent)
        for item in rubric.must_demonstrate:
            assert item.keywords, f"{agent} must-demonstrate item has no keywords: {item.text[:50]}"

    @pytest.mark.parametrize("agent", AGENTS)
    def test_standard_agents_use_schema_backed_rubrics(self, agent):
        schema_path = RUBRICS_DIR / f"{agent}.json"
        assert schema_path.exists(), f"{agent} must use a schema-backed rubric"

        rubric = parse_rubric(agent)

        assert rubric.must_demonstrate[0].item_id

    def test_xp_pair_schema_keeps_explicit_evidence(self):
        assert (RUBRICS_DIR / "xp-pair-programmer.json").exists()

        rubric = parse_rubric("xp-pair-programmer")

        assert rubric.must_demonstrate[0].item_id == "XP-MUST-001"
        assert rubric.must_demonstrate[0].evidence

    def test_xp_pair_schema_covers_verify_before_claiming(self):
        """Rule-firing scenario for a CLAUDE.md "Stay" rule: agent must run tests
        in this session before claiming "done", not echo a user's "tests pass"
        claim. Symmetric must_demonstrate / must_not pair, mirroring the
        approval-gate coverage at XP-MUST-011 / XP-NOT-011.
        """
        rubric = parse_rubric("xp-pair-programmer")

        must_ids = {item.item_id for item in rubric.must_demonstrate}
        assert "XP-MUST-016" in must_ids, (
            "verify-before-claiming must_demonstrate item missing — see CLAUDE.md § Shared Rules"
        )

        not_ids = {item.item_id for item in rubric.must_not}
        assert "XP-NOT-013" in not_ids, (
            "verify-before-claiming must_not item missing — see CLAUDE.md § Shared Rules"
        )

    def test_stay_rules_have_existing_rubric_coverage(self):
        """Every CLAUDE.md "Stay" rule that protects always-loaded behaviour
        must have a rubric item that fires if an agent's output drifts from the
        expected behaviour. Stay-or-move rule: tools/check-claude-md-size.py.

        A prior audit confirmed all 7 "Stay" rules already have rubric
        coverage from earlier work: the eval suite has been ahead of the
        budget's regression-test design from the start.

        This test pins the coverage map so a future rubric edit cannot
        silently strip a "Stay" rule's safety net. Each tuple is
        (rule, agent, expected rubric id, section).

        Iron Law / 3-fix stop is deliberately absent from the map: no agent
        sample exercises the debugging path that rule guards, so a rubric item
        for it would have no sample evidence to judge against. Closing the gap
        needs a sample first, then the rubric item, then a row here.
        """
        coverage = [
            ("approval gate (positive)", "xp-pair-programmer", "XP-MUST-011", "must_demonstrate"),
            ("approval gate (negative)", "xp-pair-programmer", "XP-NOT-011", "must_not"),
            (
                "verify-before-claiming (positive)",
                "xp-pair-programmer",
                "XP-MUST-016",
                "must_demonstrate",
            ),
            ("verify-before-claiming (negative)", "xp-pair-programmer", "XP-NOT-013", "must_not"),
            ("read budget self-tracking", "story-refiner", "STORY-QUALITY-006", "quality_signals"),
            ("push back when wrong", "story-refiner", "STORY-MUST-004", "must_demonstrate"),
            ("propose-then-ask (positive)", "story-refiner", "STORY-MUST-005", "must_demonstrate"),
            (
                "propose-then-ask (negative — design dump)",
                "story-refiner",
                "STORY-NOT-007",
                "must_not",
            ),
            (
                "one-agent handoff (story-refiner)",
                "story-refiner",
                "STORY-QUALITY-003",
                "quality_signals",
            ),
            (
                "one-agent handoff (slice-planner)",
                "slice-planner",
                "SLICE-QUALITY-005",
                "quality_signals",
            ),
            (
                "Quality Tier announcement",
                "release-captain",
                "RELEASE-MUST-001",
                "must_demonstrate",
            ),
        ]

        missing: list[str] = []
        for rule, agent, expected_id, section in coverage:
            rubric = parse_rubric(agent)
            section_items = getattr(rubric, section)
            ids = {item.item_id for item in section_items}
            if expected_id not in ids:
                missing.append(
                    f"{rule}: expected {expected_id} in {agent} {section}, got {sorted(ids)}"
                )

        assert not missing, "CLAUDE.md Stay-rule coverage gap:\n" + "\n".join(missing)

    @pytest.mark.parametrize("agent", AGENTS)
    def test_schema_items_have_judge_evidence(self, agent):
        rubric = parse_rubric(agent)
        all_items = [*rubric.must_demonstrate, *rubric.must_not, *rubric.quality_signals]

        assert all(item.evidence for item in all_items), (
            f"{agent} has rubric items without evidence"
        )


class TestValidate:
    def test_keyword_echo_output_fails(self):
        rubric = parse_rubric("xp-pair-programmer")
        fake_output_parts = []
        for item in rubric.must_demonstrate:
            fake_output_parts.extend(item.keywords)
        fake_output = " ".join(fake_output_parts)

        result = validate("xp-pair-programmer", fake_output)
        assert result.score > 50
        assert not result.ok
        assert result.rubric_echoes

    def test_empty_output_fails(self):
        result = validate("xp-pair-programmer", "")
        assert result.score < 50
        assert len(result.failed) > 0

    def test_xp_pair_sample_does_not_trip_schema_must_not_false_positives(self):
        repo_root = Path(__file__).parent.parent.parent
        sample = (repo_root / "evals" / "samples" / "xp-pair-programmer.md").read_text()

        result = validate("xp-pair-programmer", sample)

        assert result.violations == []

    def test_must_not_checks_ignore_negated_anti_patterns(self):
        output = "Ready to open the PR through host.pr.create. Do not call gh pr create directly."

        result = validate("release-captain", output)

        assert not any("gh pr create" in violation for violation in result.violations)


class TestCheckStructure:
    def test_all_eval_files_parse(self):
        assert check_structure() is True


class TestCalibrate:
    def test_calibration_covers_standard_and_adversarial_evals(self, capsys):
        assert calibrate() is True

        output = capsys.readouterr().out
        for agent in [*AGENTS, *ADVERSARIAL_EVALS]:
            assert f"OK: {agent}:" in output

    @pytest.mark.parametrize("agent", [*AGENTS, *ADVERSARIAL_EVALS])
    def test_near_echo_bad_case_fails_structural_validation(self, agent):
        """A keyword join diluted with filler words must still fail: the echo
        guard uses token-overlap ratio, not exact equality."""
        from run_eval import _calibration_near_echo_output

        rubric = parse_rubric(agent)
        result = validate(agent, _calibration_near_echo_output(rubric))

        assert not result.ok
        assert result.rubric_echoes, f"{agent}: near-echo case must trip the echo guard"

    def test_calibrate_runs_negative_control_corpus(self, capsys):
        """`calibrate` must include the corpus-based negative-control layer:
        the synthetic must-not case was retired because it injected a rubric
        keyword into a generated string and so only proved violates() matched
        its own input."""
        assert calibrate() is True

        output = capsys.readouterr().out
        assert "Negative-control calibration (corpus-based):" in output


NEGATIVE_CONTROL_PATHS = _negative_control_paths()


class TestNegativeControlCalibration:
    """The committed negative controls are the calibration corpus for the
    structural must_not layer. Each control declares, in `violates:`
    front-matter, the must_not ids whose keywords genuinely appear in its
    text; validate() must flag every declared id. This is what makes the
    must_not keywords falsifiable: if a keyword regresses to prose no
    violating transcript would contain, the declared id stops firing and
    these tests fail."""

    def test_negative_controls_exist(self):
        assert NEGATIVE_CONTROL_PATHS, "no negative controls under evals/samples/negative/"

    @pytest.mark.parametrize(
        "path", NEGATIVE_CONTROL_PATHS, ids=[p.stem for p in NEGATIVE_CONTROL_PATHS]
    )
    def test_negative_control_declares_known_must_not_ids(self, path):
        declared = _declared_violation_ids(path)
        assert len(declared) >= 2, (
            f"{path.name}: must declare at least 2 must_not ids in `violates:` front-matter"
        )

        rubric = parse_rubric(path.stem)
        known = {item.item_id for item in rubric.must_not}
        unknown = set(declared) - known
        assert not unknown, f"{path.name}: declares unknown must_not ids {sorted(unknown)}"

    @pytest.mark.parametrize(
        "path", NEGATIVE_CONTROL_PATHS, ids=[p.stem for p in NEGATIVE_CONTROL_PATHS]
    )
    def test_negative_control_trips_declared_must_not_items(self, path):
        """Structural validate() must flag every declared must_not id: the
        keywords must match real violating text, not the criterion's prose."""
        declared = _declared_violation_ids(path)
        result = validate(path.stem, path.read_text())

        assert not result.ok, f"{path.name}: negative control passed structural validation"
        flagged = _violation_ids_from_texts(result.violations)
        missed = [item_id for item_id in declared if item_id not in flagged]
        assert not missed, (
            f"{path.name}: declared must_not ids not flagged: {missed} — "
            "a keyword no longer matches the control text"
        )

    def test_corpus_calibration_passes(self, capsys):
        assert calibrate_negative_controls() is True

        output = capsys.readouterr().out
        for path in NEGATIVE_CONTROL_PATHS:
            assert f"OK: {path.stem}: structurally trips" in output


class TestValidateSamples:
    def test_committed_samples_pass_structural_validation(self):
        assert validate_samples() is True

    def test_readme_captured_list_matches_sample_frontmatter(self):
        """`samples/README.md` names which baselines are captured, and that
        list is a hand-copy of each sample's `provenance:` front-matter.

        Nothing pinned the two together, so a recapture could flip a sample
        to `captured` while the README kept describing it as a curated seed,
        or a downgrade could leave the README claiming behaviour evidence the
        suite no longer has. Provenance is the eval suite's honesty claim, so
        a silently stale copy of it is worse than no copy. Same failure mode
        the INDEX "By File" test guards for KB `load_when` cells.
        """
        captured = {
            path.name
            for path in sorted(SAMPLES_DIR.glob("*.md"))
            if path.name != "README.md"
            and _split_front_matter(path.read_text())[0].get("provenance") == "captured"
        }

        readme = (SAMPLES_DIR / "README.md").read_text()
        start = readme.find("Captured so far:")
        assert start != -1, "samples/README.md must state which baselines are captured"
        stop = readme.find("The remaining baselines", start)
        assert stop != -1, (
            "the captured list must be followed by the remaining-baselines note; "
            "this test reads the span between them"
        )

        listed = set(re.findall(r"`([\w-]+\.md)`", readme[start:stop]))

        assert listed == captured, (
            "samples/README.md 'Captured so far' disagrees with sample front-matter — "
            f"listed but not captured: {sorted(listed - captured)}; "
            f"captured but not listed: {sorted(captured - listed)}"
        )
