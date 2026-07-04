---
id: debugging
size: medium
tldr: "Iron Law: no fixes without root cause; after 3 failed attempts stop and question the architecture."
load_when: test fail, bug, regression, build failure, deploy failure, fix attempt, flaky test, root cause
audience: xp-pair-programmer, code-inspector
canonical_for: Iron Law, 3-fix stop rule, verification protocol, root cause investigation
cross_refs: testing.md, refactoring.md
verified: 2026-05-19
---

# Debugging

Source of truth for the debugging methodology. Cited from `CLAUDE.md` § Shared Rules (Debugging discipline) and `CHEATSHEET.md` § Decision Guide.

## Agent Use

- **Read first:** Iron Law, When to Apply, Phase 1 feedback loop, Verification.
- **Load deeper only on trigger:** backward tracing, 3-fix stop rule, non-deterministic bugs, and architectural retry guidance.

---

## Iron Law

```text
NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
```

Symptom fixes are failure. Quick patches mask underlying issues. If you have not completed Phase 1, you cannot propose a fix.

---

## When to Apply

| Trigger | Apply? |
|---------|--------|
| Test failure, production bug, unexpected behaviour | Yes |
| Build or deploy failure, integration regression | Yes |
| Performance regression | Yes |
| Already tried 1+ fix | Yes: especially |
| Under time pressure | Yes: guessing is slower than systematic |
| Issue "seems simple" | Yes: simple bugs have root causes too. Proportionality: when Phases 1–3 collapse into one obvious step (typo, off-by-one with a failing test in hand), say so in one line and move on: the Iron Law demands a named root cause, not ceremony |
| Active production impact | Stabilise FIRST per `incident-response.md` § Triage Flow (flag off / rollback / scale): mitigation is not a fix and needs no root cause. Root-cause debugging starts after the bleeding stops |

---

## The Four Phases

Complete each phase before moving on.

### Phase 1: Investigate: Build a Feedback Loop

**This is the skill.** A fast, deterministic, agent-runnable pass/fail signal finds the cause. Without one, no amount of staring at code saves you. Spend disproportionate effort here.

| Step | Action |
|------|--------|
| 1 | Read the error message and full stack trace: note line numbers, paths, codes |
| 2 | **Build a feedback loop**: a repeatable pass/fail signal. Try in order: |

| Priority | Loop type | When to use |
|----------|-----------|-------------|
| 1 | **Failing test** (unit, integration, or AT) | Default: fastest, most precise |
| 2 | **HTTP script** (curl / httpie against dev server) | Bug is in a running service |
| 3 | **CLI invocation** with fixture input, diffing output against known-good | CLI tool or batch process |
| 4 | **Headless browser script** (Playwright / Puppeteer) | Bug is in UI behaviour |
| 5 | **Replay a captured trace** (saved request, payload, event log) | Bug from production traffic |
| 6 | **Throwaway harness** (minimal subset, mocked deps, single call) | System too heavy to boot fully |
| 7 | **Property / fuzz loop** (1000 random inputs) | Bug is "sometimes wrong output" |
| 8 | **Bisection harness** (`git bisect run`) | Bug appeared between two known states |
| 9 | **Differential loop** (old vs new version, diff outputs) | Regression with known-good baseline |

**Iterate on the loop itself.** Treat it as a product. Faster (cache setup, skip unrelated init)? Sharper (assert on specific symptom, not "didn't crash")? More deterministic (pin time, seed RNG, isolate I/O)?

**Non-deterministic bugs:** goal is higher reproduction rate, not a clean repro. Loop the trigger 100x, add stress, narrow timing windows. A 50% flake is debuggable; 1% is not: keep raising the rate.

**Cannot build a loop?** Stop. List what you tried. Ask for: environment access, captured artifact (log dump, HAR, screen recording), or permission to add temporary instrumentation. Do not proceed to Phase 2 without a loop.

| Step | Action |
|------|--------|
| 3 | Check recent changes: `git log`, `git diff`, new deps, config drift |
| 4 | Multi-component systems: instrument every boundary (log entry data, exit data, env state): run once to identify which layer breaks |
| 5 | Trace data flow backward: see § Backward Tracing |

### Phase 2: Pattern

| Step | Action |
|------|--------|
| 1 | Find a working example of the same shape in this codebase |
| 2 | Read any reference implementation completely: never skim |
| 3 | List every difference between working and broken: however small |
| 4 | Understand dependencies, settings, env, assumptions |

### Phase 3: Hypothesis

| Step | Action |
|------|--------|
| 1 | Generate **3–5 ranked falsifiable hypotheses** before testing any: single-hypothesis generation anchors on the first plausible idea. Each must be falsifiable: "If X is the cause, then changing Y makes the bug disappear." If you can't state the prediction, the hypothesis is a vibe: discard or sharpen it. |
| 2 | Show the ranked list to the user: domain knowledge often re-ranks instantly ("the team just deployed a change to #3"). Cheap checkpoint. Don't block if user is AFK. |
| 3 | Test the top hypothesis minimally: smallest possible change, one variable at a time |
| 4 | Verify: worked → Phase 4. Didn't work → next hypothesis from the list. Do NOT stack fixes |
| 5 | When you don't know, say so: don't pretend |

### Phase 4: Fix

| Step | Action |
|------|--------|
| 1 | Write a failing test for the broken behaviour: simplest possible repro |
| 2 | Implement ONE fix: address the root cause, not the symptom |
| 3 | Verify: failing test now passes, no other tests broken (see § Verification) |
| 4 | If the fix didn't work, count attempts → see 3-Fix Stop Rule below |

---

## 3-Fix Architectural Stop Rule

After 3 failed fix attempts, **STOP**. Do not attempt fix #4.

Pattern signalling architectural problem (not failed hypothesis):

- Each fix reveals a new problem in a different place
- Fixes require "massive refactoring" to implement
- Each fix creates new symptoms elsewhere

**Action:** stop fixing. Ask: is this pattern fundamentally sound, or should the architecture change? Discuss with the user before further attempts.

NOT a failed hypothesis: a wrong architecture.

---

## Backward Tracing

Bugs often manifest deep in the call stack. Fixing where the error fires treats a symptom.

| Step | Action |
|------|--------|
| 1 | Observe the symptom (where the error fires) |
| 2 | Identify immediate cause: what code directly produces the bad output? |
| 3 | Ask "what called this with the bad value?": walk up one level |
| 4 | Continue until you find the source: the original trigger of the bad value |
| 5 | Fix at the source |
| 6 | Add validation/defense at intermediate layers so the same class of bug becomes impossible |

**Can't trace manually?** Instrument: log inputs, outputs, and `new Error().stack` (JS) or `traceback.format_stack()` (Py) at the suspected boundary. Run once. Analyse. **Tag every debug log with a unique prefix** (e.g. `[DEBUG-a4f2]`): cleanup is one `grep`. Untagged logs leak into commits.

---

## Verification

Before claiming you fixed the bug:

| Check | Why |
|-------|-----|
| Run the verification command in *this* session | Past runs aren't evidence; the code may have changed |
| Read the full output, not just exit code | Warnings often contain the next bug |
| Run the regression test red → green: write test, pass, revert fix, MUST FAIL, restore fix, pass | Proves the test actually catches the bug |
| Run the full test suite, not just the touched file | Fixes leak |

See `CLAUDE.md` § Shared Rules § Verify before claiming complete.

---

## Red Flags: STOP and Return to Phase 1

If you catch yourself thinking any of these:

- "Quick fix for now, investigate later"
- "Just try changing X and see if it works"
- "Skip the test, I'll verify manually"
- "It's probably X, let me fix that"
- "I don't fully understand but this might work"
- "Pattern says X but I'll adapt it differently"
- "One more fix attempt" (when 2+ have already failed)
- Proposing solutions before tracing data flow

All of these mean: STOP. Return to Phase 1.
