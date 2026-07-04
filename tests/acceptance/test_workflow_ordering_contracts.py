"""Contract tests for the agent-chain ordering across canonical files.

The agent chain (story-refiner → slice-planner → xp-pair-programmer →
diff-reviewer → release-captain) is the most-cited piece of prose in the
repo — it appears in CLAUDE.md, README.md, the user guide, the cheatsheet,
and the choose-workflow-path how-to. Each file uses its own lead-in
phrase ("Default workflow path:", "Recommended invocation sequence:",
"Refine before build —", "Pipeline:"). That is fine — different docs have
different voices.

What is NOT fine is the *order* drifting. If one file accidentally moves
diff-reviewer before xp-pair-programmer, every downstream pointer rots.

This module pins the ordering, not the phrasing. For each canonical file,
it scans for any line that mentions multiple agent names and an arrow
(`→` / `->`). Wherever those agents appear together, they must appear in
the canonical sequence below.

Negative-space rule: if a file is in the canonical-files list, it MUST
contain at least one line citing the chain. That stops a future copy-edit
from silently dropping the workflow citation entirely.

Tests in this file are STRUCTURE-MARKER (presence + ordering), not
CONTRACT-PHRASE. Lead-in wording is free to change.
"""

from __future__ import annotations

import re
from pathlib import Path

from deploy_ai_playbook.cli import get_source_root

# Canonical sequence: each agent's index is its position in the chain.
# release-captain is last because it ships; story-refiner is first because
# it refines. xp-pair-programmer sits between slice-planner and diff-reviewer.
CANONICAL_CHAIN: tuple[str, ...] = (
    "story-refiner",
    "slice-planner",
    "xp-pair-programmer",
    "diff-reviewer",
    "release-captain",
)

# Files that MUST cite the chain. Adding a file here pins both presence
# and ordering. Removing one is a deliberate decision — record it in the
# PR body.
CANONICAL_FILES: tuple[str, ...] = (
    "CLAUDE.md",
    "README.md",
    "knowledge-base/CHEATSHEET.md",
    "docs/user-guide.md",
    "docs/how-to/choose-workflow-path.md",
)

# A "chain-citation line" is any non-empty line that mentions ≥ 2 of the
# canonical agents AND contains an arrow (→ or ->). This skips routing
# tables (which list agents in any order) and prose mentions of a single
# agent.
_ARROW_RE = re.compile(r"→|->")


def _chain_citation_lines(text: str) -> list[tuple[int, str]]:
    """Return (1-based line number, line text) for every chain-citation line."""
    hits: list[tuple[int, str]] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        if not _ARROW_RE.search(line):
            continue
        mentioned = [a for a in CANONICAL_CHAIN if a in line]
        if len(mentioned) >= 2:
            hits.append((idx, line))
    return hits


def _canonical_index(agent: str) -> int:
    return CANONICAL_CHAIN.index(agent)


def _last_agent(segment: str) -> str | None:
    """Return the canonical agent whose name occurs *latest* in `segment`."""
    best: tuple[int, str] | None = None
    for agent in CANONICAL_CHAIN:
        j = segment.rfind(agent)
        if j == -1:
            continue
        if best is None or j > best[0]:
            best = (j, agent)
    return best[1] if best else None


def _first_agent(segment: str) -> str | None:
    """Return the canonical agent whose name occurs *earliest* in `segment`."""
    best: tuple[int, str] | None = None
    for agent in CANONICAL_CHAIN:
        j = segment.find(agent)
        if j == -1:
            continue
        if best is None or j < best[0]:
            best = (j, agent)
    return best[1] if best else None


def _ordering_violations(line: str) -> list[str]:
    """Return human-readable ordering violations on a single line, or [].

    Algorithm: split the line on arrows. The "chain" is the sequence of
    agent names *adjacent to arrows* — the last agent named in segment N
    paired with the first agent named in segment N+1. Prose mentions of
    other agents elsewhere in a segment do not count.

    Example:
        "xp-pair-programmer → diff-reviewer. Do not skip story-refiner..."
        seg[0]="xp-pair-programmer " (last=xp-pair-programmer)
        seg[1]=" diff-reviewer. Do not skip story-refiner..." (first=diff-reviewer)
        chain pair: (xp-pair-programmer=2, diff-reviewer=3) — OK.

    The "story-refiner" prose mention in seg[1] is ignored because it is
    not adjacent to an arrow.
    """
    segments = _ARROW_RE.split(line)
    if len(segments) < 2:
        return []

    chain: list[str] = []
    # Left edge of first arrow: take last agent of seg[0].
    head = _last_agent(segments[0])
    if head:
        chain.append(head)
    # For each subsequent segment, take its first agent (right edge of
    # the preceding arrow). For interior segments we still anchor on the
    # FIRST agent — its position relative to the arrow on its left is
    # what defines its place in the chain. If a segment names no agent,
    # the chain is broken on that side; skip it.
    for seg in segments[1:]:
        nxt = _first_agent(seg)
        if nxt:
            chain.append(nxt)

    if len(chain) < 2:
        return []

    violations: list[str] = []
    for i in range(1, len(chain)):
        prev = chain[i - 1]
        cur = chain[i]
        if _canonical_index(cur) < _canonical_index(prev):
            violations.append(
                f"`{cur}` (canonical position {_canonical_index(cur)}) appears after "
                f"`{prev}` (canonical position {_canonical_index(prev)}) across an arrow"
            )
    return violations


def _read(source_root: Path, rel: str) -> str:
    path = source_root / rel
    assert path.exists(), f"canonical file missing: {rel}"
    return path.read_text(encoding="utf-8")


def test_canonical_files_cite_the_agent_chain():
    """Every canonical file must contain at least one chain-citation line.

    A "chain-citation line" mentions ≥ 2 canonical agents and an arrow
    (→ or ->). This catches drift where a copy-edit silently drops the
    workflow citation entirely.
    """
    # STRUCTURE-MARKER: this test asserts presence-of-citation only;
    # lead-in phrasing ("Pipeline:" vs "Default workflow path:" vs
    # "Recommended invocation sequence:") is free to differ across files.
    source_root = get_source_root()
    missing: list[str] = []
    for rel in CANONICAL_FILES:
        text = _read(source_root, rel)
        if not _chain_citation_lines(text):
            missing.append(rel)
    assert not missing, (
        "Canonical workflow citation missing from these files (expected at least "
        f"one line mentioning ≥2 of {list(CANONICAL_CHAIN)} with an arrow):\n  "
        + "\n  ".join(missing)
    )


def test_chain_citations_follow_canonical_ordering():
    """Wherever the chain is cited, agents must appear in canonical order.

    Phrase-agnostic: this test does not care whether the lead-in says
    "Default workflow path", "Pipeline", or "Recommended invocation
    sequence". It only checks that on any line with ≥ 2 agents and an
    arrow, the agents appear in the canonical sequence
    (story-refiner → slice-planner → xp-pair-programmer → diff-reviewer
    → release-captain).
    """
    source_root = get_source_root()
    failures: list[str] = []
    for rel in CANONICAL_FILES:
        text = _read(source_root, rel)
        for line_no, line in _chain_citation_lines(text):
            violations = _ordering_violations(line)
            if violations:
                failures.append(
                    f"{rel}:{line_no} ordering violation:\n"
                    f"    line: {line.strip()}\n"
                    f"    {'; '.join(violations)}"
                )
    assert not failures, "Agent-chain ordering drift detected:\n\n" + "\n\n".join(failures)


def test_ordering_detector_flags_synthetic_drift():
    """Self-test: the detector must flag obvious drift on a synthetic line.

    Without this, a regression in `_ordering_violations` could let real
    drift slip through the canonical-files test silently. The synthetic
    line below mentions agents in reversed order around an arrow, which
    must surface as at least one violation.
    """
    bad = "xp-pair-programmer → story-refiner → diff-reviewer"
    violations = _ordering_violations(bad)
    assert violations, (
        f"detector failed to flag reversed chain {bad!r} — "
        "the canonical-ordering test would not catch real drift"
    )

    good = "story-refiner → slice-planner → xp-pair-programmer → diff-reviewer"
    assert not _ordering_violations(good), f"detector wrongly flagged canonical chain {good!r}"


def test_ordering_detector_handles_minimal_path_phrasing():
    """Edge case: 'xp-pair-programmer → diff-reviewer. Do not skip story-refiner...'

    The minimal-path sentence in CLAUDE.md mentions `story-refiner` AFTER
    the arrow chain ends, in a follow-up sentence. The detector must NOT
    misread the prose mention as part of the chain — only agents adjacent
    to arrows count.
    """
    line = (
        "**Minimal path (trivial changes):** xp-pair-programmer → diff-reviewer. "
        "Do not skip the story-refiner for non-trivial work."
    )
    assert not _ordering_violations(line), (
        "Detector should ignore prose mentions of agents not adjacent to arrows."
    )


def test_ordering_detector_handles_repeated_head_agent():
    """Edge case: the canonical CLAUDE.md line mentions `story-refiner` twice.

    `story-refiner (refine + story) → story-refiner (refine story...) → slice-planner`
    is single-agent recursion in the chain. The detector must allow
    same-agent → same-agent and continue checking the rest.
    """
    line = (
        "story-refiner (refine + story) → story-refiner (refine story against "
        "codebase) → slice-planner → xp-pair-programmer → diff-reviewer → "
        "release-captain (ship)."
    )
    assert not _ordering_violations(line), (
        "Detector must allow same agent appearing twice consecutively (canonical "
        "two-pass story-refiner usage)"
    )


def test_canonical_chain_uses_known_agents():
    """The canonical chain must only name agents that actually exist in agents/.

    Guards against typos and stale references in this contract module
    after agents are added or renamed (see CONTRIBUTING.md § Renaming).
    """
    source_root = get_source_root()
    agents_dir = source_root / "agents"
    on_disk = {p.stem.removesuffix(".agent") for p in agents_dir.glob("*.agent.md")}
    unknown = [a for a in CANONICAL_CHAIN if a not in on_disk]
    assert not unknown, (
        f"CANONICAL_CHAIN names agents that do not exist in agents/: {unknown}. "
        f"On disk: {sorted(on_disk)}"
    )
