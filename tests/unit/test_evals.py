"""Unit tests for eval harness — pure functions and classes, no file I/O."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "evals"))

from run_eval import Rubric, RubricItem, _validate_judgement_payload, extract_keywords


class TestExtractKeywords:
    def test_extracts_backtick_terms(self):
        text = "Uses `test_<what>_<condition>` naming convention"
        keywords = extract_keywords(text)
        assert "test_<what>_<condition>" in keywords

    def test_extracts_bold_terms(self):
        text = "**Intent anchors captured:** all five present"
        keywords = extract_keywords(text)
        assert "Intent anchors captured" in keywords

    def test_extracts_multiple(self):
        text = "**RED confirmed:** Each test is run with `pytest` and shows failure"
        keywords = extract_keywords(text)
        assert "RED confirmed" in keywords
        assert "pytest" in keywords

    def test_falls_back_to_noun_phrases(self):
        text = "Research file saved to research directory with findings"
        keywords = extract_keywords(text)
        assert len(keywords) >= 1


class TestRubricItem:
    def test_check_with_matching_keywords(self):
        item = RubricItem(text="test", keywords=["failing test", "RED"])
        assert item.check("I wrote a failing test and confirmed RED")

    def test_check_with_missing_keywords(self):
        item = RubricItem(text="test", keywords=["failing test", "RED", "GREEN"])
        assert not item.check("I wrote some code")

    def test_check_with_no_keywords_falls_back_to_text(self):
        item = RubricItem(text="Research questions should be neutral", keywords=[])
        assert item.check("the research questions were neutral and objective")
        assert not item.check("completely unrelated content about cats")

    def test_check_is_case_insensitive(self):
        item = RubricItem(text="test", keywords=["RED"])
        assert item.check("confirmed red phase")


class TestValidateJudgementPayload:
    def _rubric(self):
        return Rubric(
            agent="test-agent",
            must_demonstrate=[RubricItem(text="RED", item_id="MUST-001")],
            must_not=[RubricItem(text="skip tests", item_id="NOT-001")],
            quality_signals=[RubricItem(text="AAA", item_id="QUALITY-001")],
        )

    def test_accepts_valid_payload(self):
        payload = {
            "must_demonstrate": [
                {"id": "MUST-001", "criterion": "RED", "pass": True, "reason": "shown"}
            ],
            "must_not": [
                {
                    "id": "NOT-001",
                    "criterion": "skip tests",
                    "violated": False,
                    "reason": "ran tests",
                }
            ],
            "quality_signals": [
                {"id": "QUALITY-001", "criterion": "AAA", "present": True, "reason": "clear"}
            ],
        }

        assert _validate_judgement_payload(payload, self._rubric()) == payload

    def test_rejects_missing_required_sections(self):
        with pytest.raises(ValueError, match="missing required section"):
            _validate_judgement_payload({"must_demonstrate": []})

    def test_rejects_wrong_field_types(self):
        payload = {
            "must_demonstrate": [{"criterion": "RED", "pass": "yes", "reason": "shown"}],
            "must_not": [],
            "quality_signals": [],
        }

        with pytest.raises(ValueError, match="must be bool"):
            _validate_judgement_payload(payload)

    def test_rejects_missing_judgement_ids_when_rubric_supplied(self):
        payload = {
            "must_demonstrate": [],
            "must_not": [
                {"id": "NOT-001", "criterion": "skip tests", "violated": False, "reason": "no"}
            ],
            "quality_signals": [
                {"id": "QUALITY-001", "criterion": "AAA", "present": True, "reason": "clear"}
            ],
        }

        with pytest.raises(ValueError, match="missing judgements for ids: MUST-001"):
            _validate_judgement_payload(payload, self._rubric())

    def test_rejects_unknown_judgement_ids_when_rubric_supplied(self):
        payload = {
            "must_demonstrate": [
                {"id": "MUST-999", "criterion": "RED", "pass": True, "reason": "shown"}
            ],
            "must_not": [
                {"id": "NOT-001", "criterion": "skip tests", "violated": False, "reason": "no"}
            ],
            "quality_signals": [
                {"id": "QUALITY-001", "criterion": "AAA", "present": True, "reason": "clear"}
            ],
        }

        with pytest.raises(ValueError, match="unknown id `MUST-999`"):
            _validate_judgement_payload(payload, self._rubric())


class TestShallowPassingGuards:
    """Unit coverage for the two functions that carry the anti-shallow-passing
    guarantees. These were previously exercised only through
    the CI integration commands; a regression here silently weakens the
    structural pre-check for every rubric.
    """

    def test_keyword_occurs_unnegated_finds_plain_occurrence(self):
        from run_eval import _keyword_occurs_unnegated

        assert _keyword_occurs_unnegated("we run gh pr merge now", "gh pr merge")

    def test_keyword_occurs_unnegated_ignores_negated_occurrence(self):
        from run_eval import _keyword_occurs_unnegated

        assert not _keyword_occurs_unnegated("never call gh pr merge directly", "gh pr merge")
        assert not _keyword_occurs_unnegated("refuses to run gh pr merge", "gh pr merge")

    def test_refusal_then_later_action_still_fires(self):
        """A refusal of an earlier mention must NOT launder a later unnegated
        occurrence — the agent refused, then did it anyway.
        """
        from run_eval import _keyword_occurs_unnegated

        text = "do not use gh pr merge. later we ran gh pr merge anyway"
        assert _keyword_occurs_unnegated(text, "gh pr merge")

    def test_bare_not_in_unrelated_clause_does_not_suppress(self):
        """Bare "no"/"not" are not refusal markers: "tests are not green yet"
        must not suppress the concrete `git push` that follows.
        """
        from run_eval import _keyword_occurs_unnegated

        text = "tests are not green yet, running git push"
        assert _keyword_occurs_unnegated(text, "git push")

    def test_refusal_marker_must_directly_precede_keyword(self):
        from run_eval import _keyword_occurs_unnegated

        # Marker with too many intervening words no longer suppresses.
        text = "never do anything remotely as reckless as gh pr merge"
        assert _keyword_occurs_unnegated(text, "gh pr merge")
        # Marker with a short connective gap still suppresses.
        assert not _keyword_occurs_unnegated("never call gh pr merge", "gh pr merge")
        assert not _keyword_occurs_unnegated("refuses to run gh pr merge", "gh pr merge")

    def test_refusal_marker_does_not_cross_sentence_boundary(self):
        from run_eval import _keyword_occurs_unnegated

        text = "we will never do that. gh pr merge is what I ran"
        assert _keyword_occurs_unnegated(text, "gh pr merge")

    def test_violates_respects_negation(self):
        item = RubricItem(text="Auto-merge without approval", keywords=["auto-merge"])
        assert item.violates("then we auto-merge the branch")
        assert not item.violates("we must not auto-merge the branch")

    def test_violates_fires_on_any_single_concrete_keyword_hit(self):
        """A must-not item with several keywords fires on ONE unnegated hit —
        the old fractional threshold let a single forbidden action pass.
        """
        item = RubricItem(
            text="Run deploy commands",
            keywords=["kubectl", "terraform", "docker push"],
        )
        assert item.violates("mitigation: I ran kubectl rollout undo right away")
        assert not item.violates("I never run kubectl; I never run terraform")

    def test_echo_of_keywords_is_flagged(self):
        from run_eval import _looks_like_rubric_echo

        rubric = Rubric(
            agent="demo",
            must_demonstrate=[
                RubricItem(text="a", keywords=["alpha beta"]),
                RubricItem(text="b", keywords=["gamma delta"]),
            ],
        )
        assert _looks_like_rubric_echo("alpha beta gamma delta", rubric)

    def test_echo_of_single_section_keywords_is_flagged(self):
        from run_eval import _looks_like_rubric_echo

        rubric = Rubric(
            agent="demo",
            must_not=[RubricItem(text="x", keywords=["epsilon zeta"])],
        )
        assert _looks_like_rubric_echo("epsilon zeta", rubric)

    def test_independent_evidence_is_not_an_echo(self):
        from run_eval import _looks_like_rubric_echo

        rubric = Rubric(
            agent="demo",
            must_demonstrate=[RubricItem(text="a", keywords=["alpha beta"])],
        )
        output = "Concrete scenario: alpha beta observed in handler logs at line 42."
        assert not _looks_like_rubric_echo(output, rubric)

    def test_empty_output_is_not_an_echo(self):
        from run_eval import _looks_like_rubric_echo

        assert not _looks_like_rubric_echo("", Rubric(agent="demo"))
