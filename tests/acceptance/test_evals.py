"""Acceptance tests for eval harness — tests that read eval files from disk."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "evals"))

from run_eval import (
    ADVERSARIAL_EVALS,
    AGENTS,
    RUBRICS_DIR,
    calibrate,
    check_structure,
    parse_rubric,
    validate,
    validate_samples,
)


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
        """Rule-firing scenario from SPIKE-006 / RFC-0001: agent must run tests
        in this session before claiming "done", not echo a user's "tests pass"
        claim. Symmetric must_demonstrate / must_not pair, mirroring the
        approval-gate coverage at XP-MUST-011 / XP-NOT-011.
        """
        rubric = parse_rubric("xp-pair-programmer")

        must_ids = {item.item_id for item in rubric.must_demonstrate}
        assert "XP-MUST-016" in must_ids, (
            "verify-before-claiming must_demonstrate item missing — see RFC-0001"
        )

        not_ids = {item.item_id for item in rubric.must_not}
        assert "XP-NOT-013" in not_ids, (
            "verify-before-claiming must_not item missing — see RFC-0001"
        )

    def test_rfc_0001_stay_rules_have_existing_rubric_coverage(self):
        """RFC-0001 § (c) regression-test strategy: every "Stay" rule that
        protects always-loaded behaviour must have a rubric item that fires
        if an agent's output drifts from the expected behaviour.

        A prior audit confirmed all 7 candidate "Stay" rules already
        have rubric coverage from earlier work — the eval suite has been
        ahead of the RFC's regression-test design from the start.

        This test pins the coverage map so a future rubric edit cannot
        silently strip a "Stay" rule's safety net. Each tuple is
        (rule, agent, expected rubric id, section).

        Iron Law / 3-fix stop is deferred — no agent sample exercises the
        debugging path the rule guards, so a structural rubric item is not
        backed by sample evidence today. Tracked as a follow-up CHORE.
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

        assert not missing, "RFC-0001 Stay-rule coverage gap:\n" + "\n".join(missing)

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
            assert f"✓ {agent}:" in output

    @pytest.mark.parametrize("agent", [*AGENTS, *ADVERSARIAL_EVALS])
    def test_near_echo_bad_case_fails_structural_validation(self, agent):
        """A keyword join diluted with filler words must still fail — the echo
        guard uses token-overlap ratio, not exact equality."""
        from run_eval import _calibration_near_echo_output

        rubric = parse_rubric(agent)
        result = validate(agent, _calibration_near_echo_output(rubric))

        assert not result.ok
        assert result.rubric_echoes, f"{agent}: near-echo case must trip the echo guard"

    @pytest.mark.parametrize("agent", [*AGENTS, *ADVERSARIAL_EVALS])
    def test_must_not_violation_case_fails_via_violates(self, agent):
        """An output that concretely performs a forbidden action must fail
        through the must-not violation path, not merely low keyword score."""
        from run_eval import _calibration_violation_output

        rubric = parse_rubric(agent)
        if not rubric.must_not:
            pytest.skip(f"{agent} rubric has no must_not items")
        result = validate(agent, _calibration_violation_output(rubric))

        assert not result.ok
        assert result.violations, f"{agent}: violation case must trigger violates()"


class TestValidateSamples:
    def test_committed_samples_pass_structural_validation(self):
        assert validate_samples() is True
