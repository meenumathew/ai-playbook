---
name: intent-interview
description: 'Stable, owned interrogation pattern: five anchors, propose-then-ask, prompt minimization. Replaces external grill-me dependency by citing CLAUDE.md canonical rules.'
user-invocable: false
license: MIT
---

# Intent Interview: Owned Interrogation Pattern

A drift-resistant skill for capturing what the user actually wants before doing the work. This skill **owns nothing of its own**: every rule below is a citation to `CLAUDE.md` § Shared Rules. If a citation conflicts with `CLAUDE.md`, the canonical file wins: fix this skill afterwards.

## When to Use

- Any time an agent receives an idea, ticket, or vague request before refining or planning
- `agents/story-refiner.agent.md` step 1 + step 5: capturing intent on a new story
- `agents/slice-planner.agent.md` Phase 1 step 4: confirming material design questions
- `agents/xp-pair-programmer.agent.md`: minimal-path requests that skipped story-refiner
- Any session where the request is ambiguous and the agent is about to make a scope-changing decision

Not for routine implementation. Not a chat warmup. Use only when intent is genuinely unclear.

---

## Step 1: Capture the Five Anchors

Canonical: `CLAUDE.md` § Shared Rules: "Intent first: the five anchors".

| Anchor | Question it answers |
|--------|--------------------|
| Problem | What's broken or missing today? |
| Desired outcome | What does success look like for the user? |
| Why now | What triggered this work: deadline, incident, dependency? |
| Key constraint | What limits the solution space: tech, time, compliance, scope? |
| Smallest useful change | What's the minimum slice that delivers value? |

**Apply:**

- Explicit in request → use it
- High-confidence-inferable from request / issue / research → state as assumption and proceed
- Missing anchor would change scope, user-visible behaviour, safety, or the smallest useful slice → ask

Bug shape replaces anchors with Symptom / Reproduction / Severity. Spike shape replaces anchors with Question / Timebox / Decision-this-enables. See `agents/story-refiner.agent.md` step 0.

---

## Step 2: Propose Your Answer With Every Question

Canonical: `CLAUDE.md` § Shared Rules: "Propose your answer with every question".

When a material decision needs the user's input:

1. **Recommend** an answer with reasoning grounded in research findings (cite `file:line` when possible)
2. **State the trade-off** in business terms
3. **Ask** for agreement or redirection: one decision at a time, depth-first

Format: *"I'd recommend X because Y. Agree, or do you see it differently?"* extracts more than open-ended questions.

**Walk depth-first.** Resolve one branch's dependent decisions before opening the next. Don't dump unrelated questions in a batch.

---

## Step 3: Prompt Minimization

Canonical: `CLAUDE.md` § Shared Rules: "Prompt minimization".

Default to progress with recorded assumptions. Ask only when the answer changes:

- Scope
- Architecture or data model
- Security posture
- Irreversible behaviour
- User-visible behaviour
- An approval-gated action (artifact save, commit, destructive operation, external side effect)

For reversible implementation details, use the repo's existing pattern or your default, record under Assumptions, continue.

**Never bypass approval gates** for artifacts, staging, commits, destructive operations, or external side effects: minimization reduces *clarification questions*, not *approval gates*. Canonical rule: `CLAUDE.md` § Shared Rules § Approval gate.

---

## Step 4: Concise Communication During the Interview

Canonical: `CLAUDE.md` § Shared Rules: "Concise communication" + "Be terse during implementation".

- Bullets over paragraphs
- No restated context
- No filler, no repeated rationale
- Lead with action or finding

Preserve full clarity for risks, irreversible decisions, commands, test failures, security issues, and approval gates. Do not reduce research depth, validation, artifact quality, or safety checks to be terse.

---

## Step 5: Push Back When Something Is Wrong

Canonical: `CLAUDE.md` § Shared Rules: "Push back when something is wrong".

- Challenge instructions that conflict with the codebase or story
- Flag contradictions explicitly
- Say "I don't know" rather than guess
- Understand *why* before fixing *what*

Disagreement is signal, not friction. Record overrides under `## Discovered` in the plan, never silently accepted (`knowledge-base/working-agreement.md` § Disagreement Protocol).

---

## What This Skill Does NOT Do

- Does not introduce new rules: every rule lives in `CLAUDE.md`
- Does not replace `agents/story-refiner.agent.md`: story-refiner is the workflow; this skill is the technique
- Does not handle issue-tracker fetch: that's `skills/issue-fetch/SKILL.md`
- Does not handle session-end learning: that's `skills/retrospective/SKILL.md`

---

## Why Own This Skill

External interrogation patterns (grill-me and similar) change direction over time. This skill stays stable because:

1. It introduces no independent rules: drift is bounded by CLAUDE.md changes
2. It cites canonical homes: readers always reach the source of truth
3. It composes with the playbook's existing five anchors and approval gates

If you previously cited an external grill-me skill, replace the reference with `skills/intent-interview/SKILL.md` and the canonical CLAUDE.md sections it cites.
