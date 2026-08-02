---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-26
---

# Baseline Sample: diff-reviewer

Active agent: diff-reviewer

# Review: STORY-002 fix harness Makefile stack-override rescue path

**Story:** `stories/STORY-002-fix-harness-makefile-stack-override.md`
**Tier:** production (full review scope)

## Review scope

- In scope: `git diff HEAD -- harness/Makefile` (override include moved ahead of detection, `ifdef STACK` guard added) and the story-relevant hunks of `tests/acceptance/test_harness_release_contracts.py` (`_run_harness_make` helper plus `test_makefile_local_rescues_unknown_stack`, `test_stack_detection_still_selects_known_stack`, `test_unknown_stack_without_override_still_fails_with_guidance`, `test_shellcheck_disables_carry_justification`), and the single justification comment in `harness/telemetry.sh` ("Word splitting is intentional: ROLLUP is five space-separated fields.") above the SC2086 pragma.
- Out of scope, explicitly: all other hunks in `harness/telemetry.sh` (earlier hardening from a prior session). Additionally, the test-file diff carries hunks that belong to other uncommitted work; I did not review those on their merits, but see Should Fix S2 on commit hygiene.

## Verification (run in this session)

- `uv run pytest tests/acceptance/test_harness_release_contracts.py -q -k "makefile or shellcheck or stack"` gave **6 passed, 60 deselected**. All four story tests exist and pass.
- Sandbox probe 1: recognised stack (pyproject.toml) plus a `Makefile.local` overriding only `FORMAT_CMD`. The old Makefile (HEAD) uses the local command; the new Makefile silently uses the detected stack's command instead. Regression confirmed empirically (finding M1 below).
- Sandbox probe 2: `STACK=weird make help` in an otherwise-python sandbox. The new Makefile skips detection entirely on an environment variable; the old Makefile ignored it. Behaviour change confirmed (finding S1 below).

## Findings

### Must Fix

**M1. Partial `*_CMD` overrides on recognised stacks are now silently clobbered.** The old ordering (detection, then `-include Makefile.local`) let a `Makefile.local` containing only `FORMAT_CMD := black .` win on a Python repo, because the later `:=` overrides. The new ordering includes `Makefile.local` first; when it does not set `STACK`, the detection branch still runs and its `:=` assignments overwrite the local `*_CMD` values. This breaks the file's own contract ("Override commands in Makefile.local") and violates the story constraint "Behaviour for recognised stacks must not change". Domain-correctness findings are Must Fix (`knowledge-base/CHEATSHEET.md` § Review Rules). Possible directions, developer's choice: change detection assignments to `?=` so pre-included local values survive, or include `Makefile.local` both before and after detection. Add a regression test for the partial-override-on-recognised-stack case; none of the four new tests covers it (`knowledge-base/testing.md`: AC and constraint coverage).

### Should Fix

**S1. `ifdef STACK` also fires on an inherited environment variable.** `ifdef` sees make-imported environment variables, so a user or CI job with `STACK` exported (a common matrix variable name) now silently bypasses detection and gets empty `*_CMD`s that only fail at target time. The old Makefile's `:=` assignments overrode env vars, so this is a second unintended behaviour change for recognised stacks. Consider guarding on `$(origin STACK)` being `file` so only Makefile.local (not the environment) short-circuits detection. Anchor: story constraint "no behaviour change for recognised stacks"; `knowledge-base/testing.md` favours a test pinning this once decided. Related test hardening: `_run_harness_make` inherits the parent environment, so a developer with `STACK` exported would see these tests behave differently; strip `STACK` from the subprocess env for hermeticity.

**S2. Commit hygiene: the story's hunks are interleaved with unrelated uncommitted work in the same test file.** `CLAUDE.md` § Commits requires one logical change per commit. Whoever stages this must use hunk-level staging or the story commit will drag in unrelated changes. Flagging so it is not silently accepted.

### Suggestions

**G1.** `test_shellcheck_disables_carry_justification` accepts any non-shellcheck comment on the preceding line as a justification, including an unrelated comment that happens to sit there. Acceptable for a contract test; if false positives ever show up, tighten to require the comment to be contiguous and contentful. (`knowledge-base/style-guide.md` § No Suppression Without Justification is about the *reason*, not just a comment's presence.)

**G2.** In `test_makefile_local_rescues_unknown_stack`, also asserting `echo format-check` appears in stdout would pin that the override commands are actually wired, not merely that the error is absent. Minor; returncode 0 with `-n` already implies recipes expanded.

### What is good (kept brief)

- The root-cause fix matches the diagnosed mechanism: `$(error)` fires at parse time, so only a pre-detection include can rescue; the new Makefile comment explains exactly that in the code's own terms, no artifact IDs (`CLAUDE.md` § Code Quality).
- The else-branch `$(error)` plus guidance message survives for the no-override case, and `test_unknown_stack_without_override_still_fails_with_guidance` pins both the failure and the guidance text.
- Test quality: names follow `test_<what>_<condition>` (`knowledge-base/testing.md`), sandboxed via `tmp_path` with the Makefile copied in so sentinel files are fully controlled, `-n` so no real toolchain runs, `shutil.which("make")` gives an absolute path, list-form `subprocess.run` with no `shell=True`, and the `# noqa: S603` carries an inline justification consistent with the file's existing pattern.
- The telemetry.sh justification comment satisfies the suppression rule, and the contract test makes it hold for future pragmas, not just this one.

## Cognitive debt check

**Question:** The `ifdef STACK` guard makes the entire detection chain conditional on a variable that can arrive from three origins (Makefile.local, environment, command line). What guarantees that only the intended origin short-circuits detection, and what happens to a Makefile.local that overrides commands without setting STACK?

**Developer's answer:** "the override branch must come first so a Makefile.local STACK short-circuits detection; the else chain is unchanged for everyone else"

**Assessment:** The first half is correct and shows the parse-time `$(error)` mechanism is understood: the include must precede detection or the rescue can never fire. The second half is the gap. The else chain's *text* is unchanged, but its *effect* is not: because the include now runs first, the chain's `:=` assignments clobber any `*_CMD`-only Makefile.local on a recognised stack (M1), and `ifdef` answering to environment variables means "everyone else" includes anyone with `STACK` exported (S1). The mental model covers the rescue path but not the origin-sensitivity the reordering introduced. M1's regression test will close that gap durably.

## Verdict

**Request changes.**

M1 is a confirmed, empirically reproduced behaviour regression against the story's own constraint ("Behaviour for recognised stacks must not change") and the Makefile's documented contract, with no covering test. S1 should be decided (and pinned by a test) in the same pass since it shares the root cause. The three ACs as literally written are all covered and passing; the verdict turns on the constraint violation, not the ACs.

| AC | Test | Status |
|----|------|--------|
| AC1: Makefile.local rescues unknown stack, no parse error | test_makefile_local_rescues_unknown_stack | Pass (verified this session) |
| AC2: recognised sentinel still detected, behaves as before | test_stack_detection_still_selects_known_stack | Pass, but incomplete: partial-override case regresses (M1), env-var case changes (S1) |
| AC3: every shellcheck disable carries justification | test_shellcheck_disables_carry_justification | Pass (verified this session; telemetry.sh comment present) |
| Constraint: unknown stack, no override, fails with guidance | test_unknown_stack_without_override_still_fails_with_guidance | Pass (verified this session) |

Read count: 12 (well under budget). No files modified; nothing committed. Handoff: `Say 'use xp-pair-programmer — address review findings M1 and S1 for STORY-002'`.
