#!/usr/bin/env python3
"""CLAUDE.md size-budget enforcement.

CLAUDE.md is loaded into context every assistant turn — every line
compounds across every adopter's every turn. RFC-0001 plans a trim;
this gate locks no-growth at MAX_LINES so the trim cannot be silently
undone by a later edit.

Usage (CI passes no args; tests pass an explicit synthetic path):

    python tools/check-claude-md-size.py [PATH]

PATH defaults to <REPO_ROOT>/CLAUDE.md.

Exit codes:

    0  size is within budget (or skip flag set)
    1  over MAX_LINES — actual count and threshold printed to stderr

Skip flag: set CLAUDE_SKIP_CLAUDE_MD_SIZE=1 to bypass for emergencies.
Use sparingly — every skip is a deliberate exception.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PATH = REPO_ROOT / "CLAUDE.md"
# Phase 2 ratchet log — each move story tightens the cap as content moves out:
#   initial cap                     340  CLAUDE.md @ 327
#   moved Decision Guide out        325  CLAUDE.md @ 314 after move
#   moved Code Quality out          315  CLAUDE.md @ 304 after move
#   moved Review Rules out          308  CLAUDE.md @ 297 after move
#   moved AC Rules out              303  CLAUDE.md @ 292 after move
#   moved Tool Policy out           288  CLAUDE.md @ 277 after move
#   shrank Commits + Quality Gates  284  CLAUDE.md @ 273 after move
#   moved When to Go Back out       278  CLAUDE.md @ 267 after move
MAX_LINES = 278
# Rationale home: the KB efficiency rule (load smallest source on demand).
RFC_REF = "CLAUDE.md § Knowledge Base (KB) — KB efficiency rule"


def main(argv: list[str]) -> int:
    target = Path(argv[1]) if len(argv) > 1 else DEFAULT_PATH
    text = target.read_text(encoding="utf-8")
    actual = len(text.splitlines())

    if actual <= MAX_LINES:
        return 0

    if os.environ.get("CLAUDE_SKIP_CLAUDE_MD_SIZE") == "1":
        print(
            f"⚠ CLAUDE_SKIP_CLAUDE_MD_SIZE=1 set — bypassing size check "
            f"({actual} > {MAX_LINES} lines in {target}).",
            file=sys.stderr,
        )
        return 0

    print(
        f"✗ {target} is {actual} lines — exceeds budget of {MAX_LINES}.\n\n"
        f"Why this gate exists: keep always-loaded context small — see {RFC_REF}.\n"
        f"To stay under budget, follow the RFC's classification criteria —\n"
        f"send the addition to a KB file or skill instead of CLAUDE.md.\n\n"
        f"Emergency override: CLAUDE_SKIP_CLAUDE_MD_SIZE=1 (sparingly).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
