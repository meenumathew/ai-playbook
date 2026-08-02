---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-26
---

# Baseline Sample: code-inspector

Active agent: code-inspector

## Scope and priority grouping

Language/stack: POSIX shell scripts plus YAML/JSON/Make config templates (no pyproject/package.json inside harness/ itself; this is the playbook's shipped harness). 9 files enumerated:

| Priority | Files |
|----------|-------|
| P0 Security | telemetry.sh, read-budget.sh, security.yml, pre-commit-config.yaml, settings.example.json (secrets, payload handling, path traversal, action pinning) |
| P1 Domain/boundaries | All scripts (glue/infra code: P1 gate applies, assess separation of concerns only) |
| P2 Test quality | Coverage of harness scripts in tests/ (test_read_budget_hook.py, test_telemetry_rotation.py, test_telemetry.py, test_harness_release_contracts.py) |
| P3 Public API | check-teachback.sh CLI contract, Makefile target contract, settings.example.json hook schema |
| P4 Performance | telemetry.sh transcript passes, read-budget.sh per-Read hook cost |
| P5 Service/error handling | Fail-open/never-block policies, stderr messaging, skip flags |
| P6 Infrastructure | ci.yml, dependabot.yml, Makefile stack detection, twin-file sync |

Start with P0?

*[Developer: yes, run all priority groups P0-P6.]*

Review performed: all 9 files read in full; suppression-pragma sweep run at every level (2 shellcheck disables found, 1 justified, 1 not); shellcheck executed live (clean); the Makefile.local rescue path executed live in a sandbox (broken, exit 2); cross-file contract tests in tests/ verified by grep.

---

# AUDIT-002: harness/

**Auditor:** code-inspector
**Date:** 2026-07-26
**Scope:** `harness/` directory: telemetry.sh, read-budget.sh, check-teachback.sh, settings.example.json, ci.yml, security.yml, Makefile, pre-commit-config.yaml, dependabot.yml
**Read budget:** 10 / 50 (plus grep sweeps and two live executions: shellcheck, Makefile rescue-path test)

## Summary

The harness is in strong shape overall: every GitHub Action is pinned to a full 40-char SHA, payload-derived values are sanitized with an explicit character allowlist before filesystem use, fail-open and never-block policies are documented in each script header and honored in the code, and the repo-own-twin sync (harness/ci.yml vs .github/workflows/ci.yml, shared pre-commit hook SHAs) is contract-tested in `tests/acceptance/test_harness_release_contracts.py`.

Two Must Fix items. The highest-risk finding is a verified functional bug in `harness/Makefile`: its own error message tells adopters on unrecognised stacks to "set STACK and *_CMD vars in Makefile.local", but the `$(error)` at line 64 fires at parse time, before `-include Makefile.local` at line 68 is ever reached, so the documented rescue path cannot work. Reproduced live: a Makefile.local defining STACK and all five *_CMD vars still exits 2 with "Cannot continue without a known stack". The second is a suppression-pragma justification gap in telemetry.sh. Neither blocks current adopters on supported stacks; the scope is release-ready after M1 is fixed.

## Findings by Priority

### Must Fix

| ID | Finding | Evidence and impact | KB rule |
|----|---------|---------------------|---------|
| M1 | Makefile.local cannot rescue an unknown stack, contradicting the Makefile's own error message | `harness/Makefile:57-68`: the unknown-stack `$(error Cannot continue without a known stack)` (line 64) evaluates during parsing of the `else` branch, before `-include Makefile.local` (line 68). Verified live: `Makefile.local` with `STACK := shell` and all five `*_CMD` vars still fails, exit 2. Any adopter on an unsupported stack (shell-only repo, Elixir, PHP, ...) is hard-blocked despite following the documented fix, and `harness/ci.yml`'s `make quality` step fails for them. Fix is bounded: move `-include Makefile.local` above stack detection and guard detection with `ifndef STACK`. | `knowledge-base/quality-gates.md` (project gate contract); CLAUDE.md § Quality Gates |
| M2 | `# shellcheck disable=SC2086` without an inline justification | `harness/telemetry.sh:143`: the disable above `set -- $ROLLUP` carries no comment stating that unquoted word-splitting is intentional (splitting the five space-separated rollup fields into positional parameters). The sibling disable at line 62 (SC2012) is correctly justified inline. Trivial fix: one comment line, e.g. "word-splitting is the point: ROLLUP is five space-separated fields". **Marked trivial: may go straight to xp-pair-programmer.** | CLAUDE.md § Quality Gates; `knowledge-base/style-guide.md` § No Suppression Without Justification |

### Should Fix

| ID | Finding | Recommendation |
|----|---------|----------------|
| S1 | telemetry.sh fallback agent list is hardcoded and not contract-tested | `harness/telemetry.sh:113` greps for exactly eight agent names (story-refiner ... docs-maintainer). The `agents/` directory currently holds exactly those eight, but nothing pins the two lists together (grep across `tests/` finds no test asserting the fallback list matches `agents/*.agent.md` ids). A ninth agent would silently fall out of fallback attribution. Add a contract test in `test_harness_release_contracts.py` that derives the expected list from `agents/` and asserts each id appears in the script's fallback pattern. |
| S2 | harness/Makefile has zero test coverage | No test in `tests/` exercises `harness/Makefile` (grep for it across `tests/` returns nothing; `test_harness_release_contracts.py:540` only reads the root Makefile). The M1 bug is exactly the class of defect a stack-detection + Makefile.local-override characterization test would have caught. Add acceptance tests: each stack sentinel file selects the right STACK; Makefile.local overrides *_CMD; unknown stack plus Makefile.local succeeds (regression test for M1). |

### Suggestions

| ID | Opportunity | Benefit |
|----|-------------|---------|
| O1 | Extract the duplicated payload-parse and agent-attribution logic shared by telemetry.sh and read-budget.sh into a sourced helper, or add a drift contract test | The jq/sed payload fallback (`telemetry.sh:74-83` vs `read-budget.sh:42-51`), the `Active agent:` transcript extraction (`telemetry.sh:103-111` vs `read-budget.sh:61-69`), and the sanitization allowlist `A-Za-z0-9._:-` (`telemetry.sh:188-190` vs `read-budget.sh:84-85`) are copy-pairs. Each side references the other in comments, but nothing enforces sync; a security-relevant fix to one allowlist could miss the other. |
| O2 | check-teachback.sh trailer-block detection strips all blank lines before isolating the trailing block | `harness/check-teachback.sh:86` runs `sed '/^[[:space:]]*$/d'` over the whole message, so a mid-body `Teach-back:` line followed only by `Key: value` shaped body lines would be accepted as part of the trailer block, weakening the "stray mention mid-body still fails" guarantee in the comment at lines 82-85. Low likelihood; preserve blank-line structure and require the block to be the final paragraph if tightening. |
| O3 | `harness/ci.yml:64` installs pre-commit with a version pin but no hash pin | `pip install --user pre-commit==4.3.0` is version-pinned (good) while everything else in the template is SHA/hash-pinned. Consider `--require-hashes` with a small requirements file, or note the delta as accepted in the header comment. |

## Cross-File Issues

- **Acknowledged but unenforced duplication** between telemetry.sh and read-budget.sh (see O1). Not architecture drift, both scripts are single-concern and cleanly bounded, but the shared parsing/sanitization core has no sync mechanism.
- **Agent-registry drift risk** between `harness/telemetry.sh:113` and `agents/` (see S1).
- **Twin-file sync is healthy**: harness/ci.yml vs .github/workflows/ci.yml deltas are declared intentional in headers and pinned by `test_harness_release_contracts.py` (full-SHA pinning test at line 53, shared pre-commit hook SHA sync at line 465, teach-back enforcement in both CIs at lines 304-310). No drift found.
- **Dead code / flag debt**: none found. The two skip flags (CLAUDE_SKIP_TEACHBACK, CLAUDE_SKIP_READ_BUDGET) are documented escape hatches with stderr notices, not feature flags needing registry entries.
- **P1 note (gate applied)**: harness/ is glue/infrastructure code with no business rules; separation of concerns is clean (one script per concern, config templates side-effect free), so no missing-DDD findings were reported, per the P1 gate.
- **P4/P5 note**: no findings. read-budget.sh does one full-transcript jq pass per Read call inside a 5s hook timeout; the single-slurp design in telemetry.sh (comment at lines 117-121) shows the team already optimizes for this. Failure policies (never-block, fail-open, silent degrade) are consistent between header docs and code. shellcheck passes clean on all three scripts.

## Health Score

| Area | Result |
|------|--------|
| Security | Pass |
| Domain and architecture | Pass |
| Tests and evaluation | Warn (harness/Makefile untested; agent fallback list unpinned) |
| Documentation and contracts | Pass |
| Release readiness | Warn (M1: documented Makefile.local rescue path is broken) |

## Recommended Actions

1. Fix `harness/Makefile` include ordering so Makefile.local can define STACK/*_CMD before the unknown-stack error fires (M1), with a regression test (S2).
2. Add the one-line justification comment for the SC2086 disable in telemetry.sh (M2, trivial).
3. Add a contract test pinning telemetry.sh's fallback agent list to `agents/*.agent.md` ids (S1).

---

Audit preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to audits/AUDIT-002-harness.md. Anything else and I'll revise.

*[Developer: approved]*

```text
Audit saved to audits/AUDIT-002-harness.md

2 Must Fix | 2 Should Fix | 3 Suggestions

Top 3 actions:
1. Fix harness/Makefile include ordering: Makefile.local cannot rescue an unknown stack (M1, verified live)
2. Justify or remove the SC2086 shellcheck disable in telemetry.sh line 143 (M2, trivial)
3. Contract-test telemetry.sh's hardcoded agent fallback list against agents/ (S1)

Say 'use story-refiner for audit findings in audits/AUDIT-002-harness.md' to turn Must Fix items into bug/chore stories citing the audit file.
Trivial fixes the audit explicitly marks as trivial can go straight to xp-pair-programmer (M2 is marked trivial).
```

After this audit, I can also run `skills/retrospective/SKILL.md` to capture KB lessons (e.g. "parse-time $(error) vs -include ordering" as a Make gotcha) if you want.

No source or test code was written during this audit; writes were scoped to audits/ only. Read count: 10 of 50.
