---
name: story-writing
description: Write implementation-ready story artifacts from tracker work items, ideas, bugs, chores, or spikes following knowledge base standards
user-invocable: false
license: MIT
---

# Story Writing Skill

## Goal

Produce a single-sprint story artifact with INVEST quality, test-mapped AC, and justified sizing.

External project-management tools can call the source object an issue, ticket, task, story, bug, or project item. The playbook keeps that provider language at the boundary (`issue-ref:`) and normalizes implementation work into an internal artifact under `stories/`.

---

## INVEST Quick Check

| Letter | Meaning | Check |
|--------|---------|-------|
| **I**: Independent | Delivers value without relying on incomplete work | Can this be built and shipped alone? |
| **N**: Negotiable | Scope adjustable without losing core outcome | Is the how flexible, only the what fixed? |
| **V**: Valuable | Outcome and benefit explicit | Does "so that" state real business value? |
| **E**: Estimable | Enough info to size and plan | Are unknowns called out? |
| **S**: Small | Fits one sprint (1–8 points) | If >8, split it |
| **T**: Testable | AC objectively verifiable | Does each criterion map to a test? |

---

## Story Point Sizing

| Points | What it means |
|--------|--------------|
| 1 | Trivial: config change, minor text update |
| 2 | Small: single component, well understood |
| 3 | Medium: some investigation, a few components |
| 5 | Complex: multiple components, moderate design |
| 8 | Large: significant design, cross-domain coordination |

**>8 points → split before saving.** Include size rationale, unknowns, and spike note when needed.

---

## Spike Stories

Use `SPIKE-NNN`. Spikes are timeboxed and do not carry normal AC/story points (`CLAUDE.md` § Workflow).

---

## Feature Flag Stories

Apply `knowledge-base/feature-flags.md`. Flags add at least +1 point (create + cleanup), and AC must cover both flag states.

---

## Acceptance Criteria

**Behaviour, not implementation.** AC describes observable behaviour: never prescribes technology, libraries, paths, or implementation patterns. Tech choices belong in research or plan files, not story AC.

**Exception:** when a technology IS the constraint (infra mandate, regulatory requirement, integration contract). Cite the ADR or constraint inline so reviewers can verify the lock-in is real.

**Vendor-neutral by design.** Story body, AC, and `domain-language.md` use capability names ("chat notifier", "object store", "identity store"), not products ("Slack", "S3", "Auth0"). Same principle applies agent ↔ skill (`host.pr.create`, never `gh pr create`). Detail and exceptions: `knowledge-base/design-patterns.md` § Vendor-Neutral by Design.

**Sizing.** Prefer 3–5 AC. 5–7 is the upper useful range. 8+ means the story is too large: split it or remove AC that are really implementation/test details.

**Independently testable.** Each AC must be independently testable and map to one `test_<what>_<condition>`.

Write ACs in Given/When/Then to pin precondition, action, outcome (not full BDD/Gherkin):

```text
AC:   Given a valid session, when 15 minutes elapse with no activity, then the token expires
Test: test_token_expires_after_15_minutes_of_inactivity
```

Avoid vague AC like "session expiry works": Given/When/Then forces precision.

---

## Story Template

Pick by work shape: `type:` frontmatter selects it:

| `type:` | Filename prefix | Template | When |
|---|---|---|---|
| `story` | `STORY-NNN-` | [`templates/story-template.md`](../../templates/story-template.md) | New behaviour: feature, enhancement, refactor with user-visible value |
| `bug` | `BUG-NNN-` | [`templates/story-bug-template.md`](../../templates/story-bug-template.md) | Broken behaviour: repro, expected vs actual, regression coverage |
| `spike` | `SPIKE-NNN-` | [`templates/story-spike-template.md`](../../templates/story-spike-template.md) | Timeboxed learning: research file deliverable, no code on main, no AC, no points |
| `chore` | `CHORE-NNN-` | [`templates/story-template.md`](../../templates/story-template.md) | Tidy/upkeep, no user-visible change: default template, lean AC |
| `test-story` | `STORY-NNN-` | [`templates/story-template.md`](../../templates/story-template.md) | Retrofitting coverage onto existing untested code: AC are coverage targets (modules, routes, risk areas), not feature outcomes |

Can't tell story / bug / spike? Ask. Wrong shape produces a bad story.

## Frontmatter Fields

Frontmatter is the machine-readable layer. Agents grep `stories/` for ready-set, blockers, dependencies: keep accurate.

**`type:`**: `story` | `spike` | `bug` | `chore` | `test-story`. Must match filename prefix (`test-story` keeps the `STORY-NNN-` prefix).

**`status:`**: lifecycle, advanced by the agent owning the transition:

| Status | Set by | When |
|---|---|---|
| `refining` | story-refiner | Initial draft during refinement |
| `ready` | story-refiner | After preview approval and save: ready for slice-planner / xp-pair-programmer |
| `in-progress` | xp-pair-programmer | First task started |
| `blocked` | xp-pair-programmer | External blocker the agent can't resolve |
| `done` | xp-pair-programmer | All tasks complete, committed, tests green |

diff-reviewer may revert `done` → `in-progress` if changes are requested.

**`depends-on:` / `blocks:`**: dependency graph.

- `depends-on: [STORY-003]`: must be done before this can start. slice-planner reads each blocker's `status:` and STOPs if any aren't `done`.
- `blocks: [STORY-008]`: what this unblocks once done. Optional, useful for downstream visibility.

Use story IDs (`STORY-NNN`), not file paths. Empty arrays `[]` when no dependencies.

**`priority:`**: `low` | `normal` | `high` | `critical`. Optional; default `normal`. Set by story-refiner when creating incident-originated stories from the postmortem follow-up checklist (→ `high`) or on named urgency, and by release-captain (hotfix). Tie-breaker among `ready` stories.

**`incident-ref:`**: `INC-YYYY-MM-DD-slug`. Optional. Set by story-refiner when creating stories from the postmortem follow-up checklist. Traces back to `incidents/`.

---

## File Naming

```text
stories/STORY-001-short-slug.md
stories/BUG-002-stale-cache-on-rotate.md
stories/SPIKE-003-investigate-topic.md
stories/CHORE-004-bump-deps.md
```

- Prefix matches `type:` frontmatter.
- 3-digit zero-padded number; **shared number space across prefixes** (STORY-001 and BUG-001 can't both exist).
- Lowercase hyphenated slug, max 5 words.
- Check existing files for the next number.
