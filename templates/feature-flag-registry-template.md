---
id: feature-flag-registry
size: small
tldr: '<one sentence: e.g. "Live flag inventory: 2 active release flags, next cleanup due 2026-07-01">'
load_when: <comma-separated active flag names, plus "flag registry, flag inventory, flag cleanup">
audience: all
canonical_for: live flag inventory, flag owners, flag cleanup dates
cross_refs: feature-flags.md
verified: <YYYY-MM-DD>
---

<!-- When seeding to knowledge-base/feature-flag-registry.md, fill in the frontmatter above and delete this comment. -->

# Feature Flag Registry

Single source of truth for every flag in this project. Lifecycle rules, categories, and naming live in `feature-flags.md`; this file records only project state. Registering a flag here is part of the Definition of Done (`CLAUDE.md` § Definition of Done).

---

## Active Flags

| Flag | Category | Default | Owner | Story | Created | Cleanup due | Status |
|------|----------|---------|-------|-------|---------|-------------|--------|
| `[flag-name]` | release / experiment / ops / permission | OFF | [person or team] | STORY-NNN | YYYY-MM-DD | YYYY-MM-DD | dark-launch / 10% / 50% / 100% |

Rules:

- **Add the row when the flag is created**: same commit as the flag's first test.
- **Default is OFF on first deploy**: no exceptions (`feature-flags.md` § Business Behaviour).
- **Cleanup due is a date, not a milestone.** Ops and permission flags use a review date instead; if permanent, document them in `docs/limitations.md`.
- **Update Status as rollout advances** (`feature-flags.md` § Flag Lifecycle).

---

## Cleanup Debt

A flag is cleanup debt when its cleanup-due date has passed, or a release flag survives two release cycles (`feature-flags.md` § Flag Categories). diff-reviewer and code-inspector report cleanup debt as findings: schedule the removal story instead of bumping the date a second time.

---

## Removed Flags

Keep the history: it answers "was X ever flagged?" during incident triage.

| Flag | Category | Removed | Removal story | Outcome |
|------|----------|---------|---------------|---------|
| `[flag-name]` | release | YYYY-MM-DD | STORY-NNN | shipped at 100% / experiment lost, path removed |
