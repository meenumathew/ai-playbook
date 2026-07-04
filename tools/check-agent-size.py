#!/usr/bin/env python3
"""Loaded-surface size-budget enforcement (agents, CHEATSHEET, INDEX, skills).

Each agents/*.agent.md file is loaded in full on every invocation of that
agent; CHEATSHEET loads in most sessions, INDEX on routing misses, and a
SKILL.md whenever its skill fires. For these frequently-loaded surfaces the
cost compounds across every adopter's every session. This gate mirrors
tools/check-claude-md-size.py: per-file caps lock no-growth, and each trim
tightens the cap (ratchet).

Usage (CI passes no args; tests pass an explicit synthetic repo root):

    python tools/check-agent-size.py [REPO_ROOT]

Files without a cap entry get the matching DEFAULT_* cap — add an explicit
entry when a new agent or skill ships.

Exit codes:

    0  all budgeted files within budget (or skip flag set)
    1  at least one file over budget — details printed to stderr

Skip flag: set CLAUDE_SKIP_AGENT_SIZE=1 to bypass for emergencies.
Use sparingly — every skip is a deliberate exception.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
# Ratchet log — caps set at first-gate sizes + ~10 lines slack.
# When a file slims down (content moved to KB/skills), tighten its cap here
# in the same commit, like the CLAUDE.md ratchet.
AGENT_MAX_LINES: dict[str, int] = {
    "code-inspector.agent.md": 110,
    "diff-reviewer.agent.md": 155,
    "release-captain.agent.md": 155,
    "incident-responder.agent.md": 160,
    "docs-maintainer.agent.md": 185,
    "slice-planner.agent.md": 200,
    "xp-pair-programmer.agent.md": 270,
    "story-refiner.agent.md": 270,
}
DEFAULT_AGENT_MAX_LINES = 200
# Other frequently-loaded surfaces (repo-root-relative).
SURFACE_MAX_LINES: dict[str, int] = {
    "knowledge-base/CHEATSHEET.md": 275,
    "knowledge-base/INDEX.md": 225,
    "skills/retrospective/SKILL.md": 115,
    "skills/intent-interview/SKILL.md": 135,
    "skills/story-writing/SKILL.md": 150,
    "skills/host-adapter/SKILL.md": 165,
    "skills/issue-fetch/SKILL.md": 200,
    "skills/notifier/SKILL.md": 225,
    "skills/git/SKILL.md": 245,
}
DEFAULT_SKILL_MAX_LINES = 200
RATIONALE = "CLAUDE.md § Knowledge Base (KB) — KB efficiency rule"


def _over_budget(path: Path, cap: int, label: str) -> str | None:
    actual = len(path.read_text(encoding="utf-8").splitlines())
    if actual > cap:
        return f"  {label}: {actual} lines (budget {cap})"
    return None


def _collect_failures(root: Path) -> list[str]:
    failures: list[str] = []
    for agent_file in sorted((root / "agents").glob("*.agent.md")):
        cap = AGENT_MAX_LINES.get(agent_file.name, DEFAULT_AGENT_MAX_LINES)
        if failure := _over_budget(agent_file, cap, agent_file.name):
            failures.append(failure)
    for rel, cap in SURFACE_MAX_LINES.items():
        surface = root / rel
        if surface.exists() and (failure := _over_budget(surface, cap, rel)):
            failures.append(failure)
    for skill_file in sorted((root / "skills").glob("*/SKILL.md")):
        rel = str(skill_file.relative_to(root))
        if rel in SURFACE_MAX_LINES:
            continue
        if failure := _over_budget(skill_file, DEFAULT_SKILL_MAX_LINES, rel):
            failures.append(failure)
    return failures


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else REPO_ROOT
    failures = _collect_failures(root)

    if not failures:
        return 0

    if os.environ.get("CLAUDE_SKIP_AGENT_SIZE") == "1":
        print(
            "⚠ CLAUDE_SKIP_AGENT_SIZE=1 set — bypassing size check:\n" + "\n".join(failures),
            file=sys.stderr,
        )
        return 0

    print(
        "✗ Loaded-surface file(s) exceed their size budget:\n"
        + "\n".join(failures)
        + f"\n\nWhy this gate exists: these files are paid in full whenever"
        f"\nthey load — see {RATIONALE}."
        f"\nMove rarely-hit sections to an on-demand KB file instead of growing"
        f"\nthe surface; tighten the cap in tools/check-agent-size.py when you"
        f"\ntrim.\n\nEmergency override: CLAUDE_SKIP_AGENT_SIZE=1 (sparingly).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
