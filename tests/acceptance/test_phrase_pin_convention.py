"""Guardrail for the phrase-pin classification convention.

The convention itself is documented in `tests/acceptance/__init__.py`:
markdown-content assertions in acceptance tests must be labeled with one
of `# CONTRACT-PHRASE:`, `# STRUCTURE-MARKER:`, or `# ACCIDENTAL-PIN:`.

This module enforces two things to keep the convention durable:

1. The legend itself must exist in `tests/acceptance/__init__.py`.
    If the legend is removed or its classification labels are renamed,
   future maintainers lose the documented standard.

2. Every test module that already adopts the convention must keep at
    least one classification label present. New PRs that strip annotations
   from a labeled file will trip this guardrail.

The guardrail does not attempt to enforce the convention on every
existing assertion (414 today across the suite) — that scope was
intentionally deferred. New markdown-content assertions added to the
labeled files should carry a classification label; reviewers and the CONTRIBUTING
note are the human enforcement layer.
"""

from __future__ import annotations

import re

from deploy_ai_playbook.cli import get_source_root

# Match each classification label after a `#` comment marker, allowing optional
# parenthetical qualifiers like `# CONTRACT-PHRASE (negative):`.
CLASSIFICATION_LABEL_RE = re.compile(r"#\s*(CONTRACT-PHRASE|STRUCTURE-MARKER|ACCIDENTAL-PIN)\b")

# Files that have adopted the convention. Adding a file here is a
# commitment that its markdown-content assertions stay labeled.
LABELED_FILES: tuple[str, ...] = (
    "tests/acceptance/test_skill_operation_contracts.py",
    "tests/acceptance/test_harness_release_contracts.py",
    "tests/acceptance/test_story_workflow_contracts.py",
    "tests/acceptance/test_approval_gate_contracts.py",
    "tests/acceptance/test_workflow_ordering_contracts.py",
    "tests/acceptance/test_docs_contracts.py",
    "tests/acceptance/test_eval_contracts.py",
    "tests/acceptance/test_agent_contracts.py",
    "tests/acceptance/test_kb_skill_contracts.py",
    "tests/acceptance/test_workflow_chain.py",
)


def test_classification_legend_exists_in_acceptance_init():
    """The legend documenting the three classification labels must live at a stable path.

    Other tests in this module reference the convention by name; if the
    legend disappears, the references rot. Pinning its presence stops a
    future cleanup from quietly removing the standard.
    """
    init_path = get_source_root() / "tests" / "acceptance" / "__init__.py"
    body = init_path.read_text(encoding="utf-8")
    for label in ("CONTRACT-PHRASE", "STRUCTURE-MARKER", "ACCIDENTAL-PIN"):
        # CONTRACT-PHRASE: the three classification label names ARE the convention.
        # Renaming one is a coordinated change across labeled files +
        # CONTRIBUTING.md; the test forces that coordination.
        assert label in body, (
            f"tests/acceptance/__init__.py must document the {label!r} classification label"
        )


def test_labeled_files_keep_at_least_one_classification_label():
    """Files that adopted the convention must retain at least one classification label.

    A maintainer who strips the labels from a file is making an active
    decision; the test surfaces it for review rather than letting the
    convention silently erode.
    """
    source_root = get_source_root()
    missing: list[str] = []
    deleted: list[str] = []
    for rel in LABELED_FILES:
        path = source_root / rel
        if not path.exists():
            # A renamed-or-deleted labeled file should also surface for
            # review — silently skipping it would let the convention
            # erode through deletion rather than label-stripping.
            deleted.append(rel)
            continue
        text = path.read_text(encoding="utf-8")
        if not CLASSIFICATION_LABEL_RE.search(text):
            missing.append(rel)
    issues: list[str] = []
    if deleted:
        issues.append(
            "Files listed in LABELED_FILES no longer exist on disk "
            f"(rename/delete updates LABELED_FILES too): {deleted}"
        )
    if missing:
        issues.append(
            "Files used to carry phrase-pin classification labels but no longer do — "
            "either re-add the labels or remove from LABELED_FILES with a PR-body "
            f"justification: {missing}"
        )
    assert not issues, (
        "Phrase-pin guardrail (convention: tests/acceptance/__init__.py):\n  " + "\n  ".join(issues)
    )


def test_classification_label_regex_matches_real_label_shapes():
    """Self-test: the classification label regex must match every permitted shape.

    Without this, a regression in `CLASSIFICATION_LABEL_RE` could let labeled files
    pass `test_labeled_files_keep_at_least_one_classification_label` while no longer
    detecting any real label.
    """
    must_match = (
        "    # CONTRACT-PHRASE: literal user-visible phrase",
        "# STRUCTURE-MARKER: heading must exist",
        "# ACCIDENTAL-PIN: loosen to substring",
        "    # CONTRACT-PHRASE (negative): forbidden anti-pattern",
        "    # STRUCTURE-MARKER (presence-only): pinned heading",
    )
    must_not_match = (
        "# This mentions CONTRACT but no classification label",
        "# contract-phrase: lowercase doesn't qualify",  # convention is uppercase
        "    contract = 'phrase'  # ordinary code",
    )
    for line in must_match:
        assert CLASSIFICATION_LABEL_RE.search(line), (
            f"classification label regex failed to match: {line!r}"
        )
    for line in must_not_match:
        assert not CLASSIFICATION_LABEL_RE.search(line), (
            f"classification label regex falsely matched unlabeled line: {line!r}"
        )


def test_contributing_doc_references_the_convention():
    """CONTRIBUTING.md § Testing must point new contributors at the convention.

    Discoverability is half the value of the convention. If the
    CONTRIBUTING note is removed, new contributors won't know to add
    classification labels.
    """
    contributing = (get_source_root() / "CONTRIBUTING.md").read_text(encoding="utf-8")
    # STRUCTURE-MARKER: pointer phrase, not exact wording.
    for token in ("CONTRACT-PHRASE", "STRUCTURE-MARKER", "ACCIDENTAL-PIN"):
        assert token in contributing, (
            f"CONTRIBUTING.md must mention the {token!r} classification label so new "
            f"contributors discover the phrase-pin convention"
        )
