---
name: retrospective
description: 'Session-end learning loop: surface friction, propose knowledge base improvements, and capture reusable lessons. Use at the end of a story, after a code audit, or when the agent hits repeated friction during a session.'
user-invocable: false
license: MIT
---

# Retrospective: Learning Loop

Turn session experience into durable KB improvements.

## When to Run

- End of story or audit
- Repeated friction (same issue 3+ times)
- Explicit user request

---

**Blameless norm** (retrospective Prime Directive): findings target process, prompts, and KB content, never a person or agent "doing badly": everyone acted reasonably given what they knew at the time.

## The Loop

1. Review signals
2. Surface reusable patterns
3. Propose small KB updates
4. Get explicit approval per `CLAUDE.md` § Shared Rules § Approval gate
5. Apply and stage

---

## Step 1: Review Signals

Scan:

- plan `## Discovered`
- review/audit findings
- repeated TDD friction
- repeated agent lookup/correction friction

---

## Step 2: Surface + Filter

Map findings to target:

- missing rule/pattern -> `design-patterns.md` / `style-guide.md`
- term drift -> `knowledge-base/domain-language.md`
- known limitation -> `docs/limitations.md`
- architecture decision -> `docs/adr/NNNN-*.md`
- testing/perf lesson -> `testing.md` / `performance.md`

Capture only if:

1. likely to recur
2. useful to future sessions
3. not already obvious from code

---

## Step 3: Propose

Use one small proposal per change:

```text
## Proposed KB Updates

### 1. [Category]: [short description]
**File:** knowledge-base/[target].md
**Section:** [existing section or "new section"]
**Change:** [add/update/remove]
**Content preview:**
> [2-3 line preview of what would be added]
**Why:** [one sentence: what friction does this prevent?]
```

Keep proposals surgical (one rule/pattern/term), not full rewrites.

---

## Step 4: Approve

Require explicit approval for each proposal (`CLAUDE.md` § Shared Rules).

---

## Step 5: Apply

1. Open target KB file.
2. Add/update minimal section.
3. Update `knowledge-base/INDEX.md` if a new topic/section was added (the routing table).
4. Update `knowledge-base/CHEATSHEET.md` only if the rule is high-leverage and one-line-summarisable (digest covers ~80%; not every change belongs).
5. Stage, show diff, follow commit approval gate per `CLAUDE.md` § Shared Rules § Approval gate.

**Commit type:** `docs(kb): <description>`: for example `docs(kb): add retry pattern to design-patterns`. `kb` scope reserved per `skills/git/SKILL.md` § Scope.

---

## What NOT to Capture

- code-level fixes already represented in code
- one-off debugging steps without reusable rule
- session-local noise
- preference-only changes without consensus
