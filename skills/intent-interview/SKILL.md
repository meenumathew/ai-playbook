---
name: intent-interview
description: 'Stable, owned interrogation pattern: five anchors, propose-then-ask, prompt minimization. Replaces external grill-me dependency by citing CLAUDE.md canonical rules.'
user-invocable: false
license: MIT
---

# Intent Interview: Owned Interrogation Pattern

Capture what the user actually wants before doing the work. This skill **owns nothing of its own**: it is an ordered checklist of `CLAUDE.md` § Shared Rules citations, which are always in context when this skill fires. Read the cited section there; do not expect it restated here. If a citation conflicts with `CLAUDE.md`, the canonical file wins: fix this skill afterwards.

## When to Use

- Any time an agent receives an idea, ticket, or vague request before refining or planning
- `agents/story-refiner.agent.md` step 1 + step 5: capturing intent on a new story
- `agents/slice-planner.agent.md` Phase 1 step 4: confirming material design questions
- `agents/xp-pair-programmer.agent.md`: minimal-path requests that skipped story-refiner
- Any session where the request is ambiguous and the agent is about to make a scope-changing decision

Not for routine implementation. Not a chat warmup. Use only when intent is genuinely unclear.

## The Interview, in Order

Each step applies one canonical rule from `CLAUDE.md` § Shared Rules:

1. **Capture the five anchors** ("Intent first: the five anchors"): explicit → use it; high-confidence-inferable → state as assumption; ask only when a missing anchor changes scope, user-visible behaviour, safety, or the smallest useful slice.
2. **Propose your answer with every question** ("Propose your answer with every question"): recommend with reasoning (cite `file:line`), state the trade-off in business terms, one decision at a time, depth-first.
3. **Minimize prompts** ("Prompt minimization"): default to progress with recorded assumptions; never bypass approval gates (`CLAUDE.md` § Shared Rules § Approval gate).
4. **Stay terse** ("Concise communication", "Be terse during implementation"): full clarity is preserved for risks, irreversible decisions, commands, failures, security, and gates.
5. **Push back when something is wrong** ("Push back when something is wrong"): record overrides under `## Discovered` in the plan, never silently accepted (`knowledge-base/working-agreement.md` § Disagreement Protocol).

**Shape substitution (owned by this skill):** the bug shape replaces the five anchors with Symptom / Reproduction / Severity; the spike shape replaces them with Question / Timebox / Decision-this-enables. See `agents/story-refiner.agent.md` step 0.

## What This Skill Does NOT Do

- Does not introduce new rules: every rule lives in `CLAUDE.md`
- Does not replace `agents/story-refiner.agent.md`: story-refiner is the workflow; this skill is the technique
- Does not handle issue-tracker fetch: that's `skills/issue-fetch/SKILL.md`
- Does not handle session-end learning: that's `skills/retrospective/SKILL.md`

## Why Own This Skill

External interrogation patterns (grill-me and similar) change direction over time. This skill stays stable because it introduces no independent rules (drift is bounded by CLAUDE.md changes), cites canonical homes, and composes with the playbook's existing anchors and gates. If you previously cited an external grill-me skill, replace the reference with `skills/intent-interview/SKILL.md` and the canonical CLAUDE.md sections it cites.
