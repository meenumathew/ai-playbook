# Eval Input: Diff Reviewer

## Grounding

This scenario targets the ai-playbook repository itself: the reviewed diff is the real, uncommitted output of the xp-pair-programmer capture session (see `evals/xp-pair-programmer-input.md`), so the review cites real files, real tests it re-ran, and real sandbox probes — the precondition for a `provenance: captured` baseline (see `evals/samples/README.md` § Refreshing a sample, capture prerequisite).

## Request

"use diff-reviewer: review the uncommitted STORY-002 changes against the story's acceptance criteria and the knowledge base."

## Context

- Story: `stories/STORY-002-fix-harness-makefile-stack-override.md` (bug: the harness Makefile's documented Makefile.local rescue path fires `$(error)` at parse time before the include; plus a bare shellcheck suppression in telemetry.sh)
- Diff under review: `harness/Makefile` (override include moved ahead of detection, guard added), the story's new tests in `tests/acceptance/test_harness_release_contracts.py`, and one justification comment in `harness/telemetry.sh`
- Out-of-scope hunks are present in the same files (earlier uncommitted work); the reviewer must scope explicitly
- Production tier: full review scope, AC-coverage table, cognitive debt check, explicit verdict
