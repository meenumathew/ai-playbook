---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-26
---

# Baseline Sample: xp-pair-programmer

Active agent: xp-pair-programmer

Loaded: story (STORY-002, type: bug, 2 points). Regression-test-first discipline applies: slice 1 is the failing regression test encoding the reproduction; the fix turns it green. Dependency check: Task 2 (suppression justification) starts only after Task 1 completes and is verified.

**Reproduction (pre-fix, manual):** sandbox with Makefile.local defining STACK plus all five *_CMD vars, no sentinel files:

```text
ERROR: No recognised stack detected.
Fix: create one of the above, or set STACK and *_CMD vars in Makefile.local.
Makefile:64: *** Cannot continue without a known stack.  Stop.
exit=2
```

## Task 1: Makefile.local rescue path (AC1, AC2)

Outer loop first: wrote the failing acceptance test `test_makefile_local_rescues_unknown_stack` before touching implementation (test before code), with helper `_run_harness_make` (copies harness/Makefile into a tmp_path sandbox, runs `make -f Makefile -n <goals>` via subprocess, so sentinels and overrides are controlled and no real toolchain executes).

RED confirmed — ran it and read the failure output:

```text
>       assert "Cannot continue without a known stack" not in result.stderr
E       AssertionError: assert 'Cannot cont... known stack' not in 'Makefile:64...ck.  Stop.\n'
FAILED tests/acceptance/test_harness_release_contracts.py::test_makefile_local_rescues_unknown_stack
1 failed, 62 deselected in 0.25s
```

GREEN — smallest change that passes, no extra features: moved `-include Makefile.local` above stack detection with a comment explaining parse-time `$(error)` semantics; added `ifdef STACK` as the first detection branch (`else ifneq` chains from it); removed the old post-detection include. Rerun: `1 passed, 62 deselected in 0.13s`.

AC2 (characterization, passed immediately as expected since behaviour must not change): `test_stack_detection_still_selects_known_stack`: pyproject.toml sentinel, asserts `Detected stack: python` and `uv run ruff format` in help output. `2 passed`.

Negative path (story constraint, one test at a time): `test_unknown_stack_without_override_still_fails_with_guidance`: no sentinel, no override; asserts non-zero exit, the error message, and the `set STACK and *_CMD vars in Makefile.local` guidance survive. `3 passed`.

Format and lint after GREEN: `uv run ruff format` clean; `uv run ruff check --fix` flagged S607 (partial executable path `"make"`). Fixed by resolving via `shutil.which("make")` instead of suppressing. Re-ran format and lint: `1 file left unchanged`, `All checks passed!`.

Manual verification of the original reproduction on the fixed Makefile: same sandbox setup, real (non dry-run) run: all five echo commands executed, `exit=0`; `make help` prints `Detected stack: custom`.

Comprehension check (grounded in the changed code): can you walk me through why the original `-include Makefile.local` position could never rescue an unknown stack?

*[Developer: walk me through it in the summary.]*

Teach-back: make evaluates conditional directives and `$(error)` at parse time, top to bottom. The `else` branch's `$(error)` aborted parsing before make ever reached the include below it, so nothing Makefile.local said could matter. Moving the include above detection and adding `ifdef STACK` as the first detection branch means an override defines STACK before the conditionals run, the override branch matches, and the error branch is never parsed as active. With no override and no sentinel, the else branch still fires exactly as before.

## Task 2: suppression justification contract (AC3)

RED confirmed — wrote `test_shellcheck_disables_carry_justification` (scans `harness/*.sh` for `shellcheck disable` lines, requires a non-shellcheck comment on the preceding line or an inline reason after the directive), ran it:

```text
E       AssertionError: shellcheck disable without justification comment:
E           telemetry.sh:143: # shellcheck disable=SC2086
FAILED ... 1 failed, 65 deselected in 0.27s
```

GREEN: added above the SC2086 pragma in harness/telemetry.sh: `# Word splitting is intentional: ROLLUP is five space-separated fields.` Rerun: `1 passed`. The existing SC2012 pragma already passes the scanner via its comment above.

Format and lint after GREEN: `ruff format --check` clean, `ruff check` All checks passed. `shellcheck harness/telemetry.sh` exit=0.

Refactor while green: none needed beyond the S607 cleanup; helper and tests match the existing file style. Re-ran focused tests after cleanup: green.

Reviewed the diff with fresh eyes (`git diff`): harness/Makefile now includes Makefile.local before detection with a why-comment, `ifdef STACK` short-circuits detection, error branch unchanged; telemetry.sh gains one justification line; the test file gains one helper plus four tests matching existing conventions (file-level `repo_contract` marker, `get_source_root()`, justified `# noqa: S603` matching the file's existing pattern). No artifact IDs cited in code, no em dashes.

## AC verification before staging

```text
uv run pytest tests/acceptance/ -q -k "makefile or shellcheck or stack"
6 passed, 557 deselected in 0.34s

uv run pytest tests/ -q
2 failed, 954 passed in 47.86s
```

The two failures were stash-verified as pre-existing: with all changes stashed they fail identically on the untouched tree (docs pointer drift, outside this story's blast radius). Verify before claiming: the focused and full suites above ran in this session with output shown; no pass claim rests on anyone's word.

| AC | Positive | Negative | Edge coverage |
|---|---|---|---|
| AC1 Makefile.local rescues unknown stack | `test_makefile_local_rescues_unknown_stack` (override present, quality succeeds) | `test_unknown_stack_without_override_still_fails_with_guidance` (no override: error and guidance kept) | Real non-dry-run manual verification: all five commands execute, exit 0 |
| AC2 known stack unchanged | `test_stack_detection_still_selects_known_stack` (pyproject.toml selects python, ruff commands wired) | Covered by AC1 negative (detection else-chain still reachable) | Sandbox isolates sentinels so the repo's own pyproject.toml cannot leak in |
| AC3 suppression justification | `test_shellcheck_disables_carry_justification` (scans all harness/*.sh, both pragmas pass) | RED run proved it catches the bare SC2086 pragma | Accepts comment-above or inline-reason form; a shellcheck directive line cannot justify itself |

## Task boundary: staging preview (one commit per task, no inner-loop commits)

```text
git diff --cached --stat
 harness/Makefile                                   | 24 ++++++++-----
 harness/telemetry.sh                               |  1 +
 tests/acceptance/test_harness_release_contracts.py | 96 ++++++++++++++++++++++
```

Would-be Conventional Commit for Task 1:

```text
fix(harness): include Makefile.local before stack detection

The unknown-stack $(error) fires at make parse time, so an include
placed after detection could never rescue an adopter on an
unrecognised stack even though the error text told them to use it.
Including the override first and guarding detection with ifdef STACK
lets a Makefile.local win while keeping the guidance error for
adopters with no override. Recognised-stack behaviour is unchanged
and pinned by a characterization test.

Teach-back: make evaluates conditionals and $(error) top-to-bottom at
parse time, so the rescue include must precede the detection block.
```

Would-be Conventional Commit for Task 2 (after Task 1's commit, with plan progress updated in between):

```text
test(harness): require justification on shellcheck disable pragmas

Adds the missing rationale to the SC2086 suppression in telemetry.sh
and a contract test scanning harness/*.sh so any future bare
suppression fails loudly instead of shipping unexplained.

Teach-back: the scanner accepts a plain comment on the preceding line
or an inline reason after the directive; a shellcheck directive line
cannot justify itself.
```

Updated plan progress: Task 1 complete, Task 2 complete. Discovered work: none (nothing added beyond the plan; the S607 fix was in-scope lint hygiene on the new test helper).

Changes staged. Say 'commit' to proceed.

## Review round: addressing diff-reviewer findings M1 and S1

*[Developer: use xp-pair-programmer — address review findings M1 and S1 for STORY-002.]*

The review reproduced a real regression my fix introduced (M1: a `Makefile.local` overriding only `*_CMD` values on a recognised stack is clobbered, because the pre-detection include lets detection's `:=` assignments run last) and a behaviour change (S1: `ifdef STACK` answers to inherited environment variables).

RED confirmed for M1 — `test_makefile_local_partial_override_wins_on_recognised_stack` (pyproject sentinel plus a `FORMAT_CMD`-only override; asserts the custom command wins) fails against the reviewed code. GREEN: re-include `Makefile.local` after detection too (assignments are `:=` and idempotent, so the double include is safe), restoring the documented "override any *_CMD" contract while keeping the pre-detection include the rescue path needs.

RED confirmed for S1 — `test_environment_stack_variable_does_not_bypass_detection` (python sandbox with `STACK=weird` exported; asserts detection still selects python) fails against `ifdef`. GREEN: guard on `ifeq ($(origin STACK),file)` so only a Makefile.local assignment short-circuits detection. Test hermeticity per the review: `_run_harness_make` now strips `STACK` from the subprocess environment.

Format and lint after GREEN: `1 file left unchanged`, `All checks passed!`. Focused rerun:

```text
uv run pytest tests/acceptance/test_harness_release_contracts.py -q -k "makefile or shellcheck or stack or environment"
8 passed, 60 deselected in 0.28s
```

Updated AC coverage: AC2's negative and edge columns now include the partial-override and env-var regression tests the review demanded. Re-review requested on the amended diff.

Changes staged. Say 'commit' to proceed.
