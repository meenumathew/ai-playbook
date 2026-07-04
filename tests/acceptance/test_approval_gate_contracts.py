"""Contract tests for approval-gate canonical-with-pointer discipline.

The approval gate is canonical in `CLAUDE.md` § Shared Rules § Approval
gate. Every agent and skill that needs the rule must cite it by reference,
not restate the literal phrasing. Restatements drift over time, while
references stay correct as long as the canonical rule does.

Two structural pins, one classified phrase, no exact-prose-matching:

1. CONTRACT-PHRASE — the literal commit-prompt sentence
   `Changes staged. Say 'commit' to proceed.` is the contract Claude says
   to the user. It is allowed in:
   - `CLAUDE.md` (canonical)
   - `evals/` (sample agent output is the contract under test)
   - `docs/` (walkthrough/example output)
   - `README.md` (Quick Start walkthrough)
   - `docs/rfcs/` (quoted examples)
   It is NOT allowed in `agents/*.agent.md` or `skills/*/SKILL.md` —
   those must cite by reference. This rule keeps the prompt definition
   in exactly one editable place.

2. STRUCTURE-MARKER — every agent or skill that mentions the approval
   gate must cite `CLAUDE.md` § Shared Rules § Approval gate (the
   canonical pointer), not invent a private wording. The pointer
   resolver in `test_pointer_contracts.py` checks the citation lands on
   a real heading; this test checks the citation exists at all.
"""

from __future__ import annotations

import re
from pathlib import Path

from deploy_ai_playbook.cli import get_source_root

# CONTRACT-PHRASE: this is the literal user-facing approval prompt.
# If this string changes, every consumer changes — that's the point.
COMMIT_PROMPT = "Changes staged. Say"

# Files where the literal prompt is allowed to live verbatim.
# CLAUDE.md is the canonical rule. README.md and CHANGELOG.md cite the
# prompt in walkthroughs / release notes — those are documenting the
# contract, not duplicating it.
ALLOWED_PROMPT_LOCATIONS: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "CHANGELOG.md",
)

# Subdirectories where the literal prompt is allowed (any file beneath).
ALLOWED_PROMPT_DIRS: tuple[str, ...] = (
    "evals/",
    "docs/",
)

# Citation pattern: any agent/skill that references the approval gate
# must do so via this canonical pointer. The pointer-resolver in
# test_pointer_contracts.py verifies the heading exists.
CANONICAL_CITATION_RE = re.compile(r"`CLAUDE\.md`\s+§\s+Shared Rules\s+§\s+Approval gate")

# Marker that signals "this file talks about the approval gate at all".
# Files mentioning approval/gate keywords must include the canonical
# citation; files that don't need it stay silent.
APPROVAL_KEYWORD_RE = re.compile(r"approval gate", re.IGNORECASE)


def _is_allowed_prompt_path(rel: str) -> bool:
    if rel in ALLOWED_PROMPT_LOCATIONS:
        return True
    return any(rel.startswith(prefix) for prefix in ALLOWED_PROMPT_DIRS)


def _walk_repo_markdown(source_root: Path) -> list[tuple[str, str]]:
    """Yield (relative_path, text) for every markdown file under source_root.

    Skips .venv, mutants, and any dot-directory.
    """
    out: list[tuple[str, str]] = []
    for path in sorted(source_root.rglob("*.md")):
        rel_parts = path.relative_to(source_root).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        if rel_parts[0] in {".venv", "mutants", "node_modules"}:
            continue
        out.append(("/".join(rel_parts), path.read_text(encoding="utf-8")))
    return out


def test_commit_prompt_phrase_lives_only_in_allowed_locations():
    """CONTRACT-PHRASE: the literal commit prompt must not migrate into agents/skills.

    Allowed in CLAUDE.md (canonical), README.md (walkthrough), evals/
    (sample output), and docs/ (examples). Anywhere else is a partial
    restatement that will drift away from CLAUDE.md.
    """
    source_root = get_source_root()
    leaks: list[str] = []
    for rel, text in _walk_repo_markdown(source_root):
        if COMMIT_PROMPT not in text:
            continue
        if _is_allowed_prompt_path(rel):
            continue
        leaks.append(rel)
    assert not leaks, (
        f"Literal commit prompt {COMMIT_PROMPT!r} appeared in non-canonical files. "
        f"Cite `CLAUDE.md` § Shared Rules § Approval gate instead of copying the phrase. "
        f"Leaks: {leaks}"
    )


def test_agents_and_skills_mentioning_approval_gate_cite_canonical_pointer():
    """STRUCTURE-MARKER: every agent/skill discussing the approval gate cites CLAUDE.md.

    Skills and agents are free to NOT mention the gate at all. But if
    they do, they must point at the canonical heading rather than invent
    private wording. The pointer-resolver test guarantees that heading
    exists.
    """
    source_root = get_source_root()
    targets: list[tuple[str, Path]] = [
        (f"agents/{path.name}", path)
        for path in sorted((source_root / "agents").glob("*.agent.md"))
    ]
    targets.extend(
        (f"skills/{path.parent.name}/SKILL.md", path)
        for path in sorted((source_root / "skills").glob("*/SKILL.md"))
    )

    missing_citation: list[str] = []
    for rel, path in targets:
        text = path.read_text(encoding="utf-8")
        if not APPROVAL_KEYWORD_RE.search(text):
            continue
        if not CANONICAL_CITATION_RE.search(text):
            missing_citation.append(rel)

    assert not missing_citation, (
        "These files mention the approval gate but do not cite "
        "`CLAUDE.md` § Shared Rules § Approval gate. Add the canonical "
        f"citation rather than restating the rule.\n  Files: {missing_citation}"
    )


def test_approval_gate_canonical_citation_resolves():
    """The canonical citation string must point at a real heading in CLAUDE.md.

    This is a belt-and-braces check on top of test_pointer_contracts.py:
    it makes the failure message actionable when somebody renames the
    heading in CLAUDE.md without updating callers.
    """
    source_root = get_source_root()
    claude_md = (source_root / "CLAUDE.md").read_text(encoding="utf-8")

    # Required headings, in nesting order.
    assert "## Shared Rules" in claude_md, (
        "CLAUDE.md must contain a `## Shared Rules` section — the canonical "
        "approval-gate citation depends on it"
    )
    # The approval-gate paragraph is bolded inline rather than a heading;
    # the canonical citation reads "§ Shared Rules § Approval gate" because
    # callers cite the bolded sub-rule by name. This test pins the bolded
    # phrase as the third-tier anchor — change either side and the test
    # surfaces the breakage.
    assert "**Approval gate.**" in claude_md, (
        "CLAUDE.md must contain `**Approval gate.**` as a bolded sub-rule "
        "inside § Shared Rules — every agent/skill cites this anchor"
    )


def test_synthetic_restatement_would_be_caught():
    """Self-test: the leak detector flags a synthetic in-memory restatement.

    Without this, a regression in the path/string logic could let a real
    restatement slip through silently.
    """
    fake_files = [
        ("CLAUDE.md", f"...{COMMIT_PROMPT} 'commit' to proceed."),  # canonical, OK
        ("agents/fake.agent.md", f"Just say {COMMIT_PROMPT} 'commit'..."),  # leak
        ("skills/fake/SKILL.md", "Cite CLAUDE.md instead of copying the phrase."),  # OK
    ]
    leaks = [
        rel
        for rel, text in fake_files
        if COMMIT_PROMPT in text and not _is_allowed_prompt_path(rel)
    ]
    assert leaks == ["agents/fake.agent.md"], (
        f"detector failed to isolate the synthetic leak: {leaks}"
    )
