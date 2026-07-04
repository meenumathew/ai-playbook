---
issue-ref:
type: story            # story | spike | bug | chore | test-story (test-story keeps the STORY- prefix)
status: refining       # refining | ready | in-progress | blocked | done
priority: normal       # low | normal | high | critical: default normal
workspace:             # optional: name of the workspace this story belongs to (e.g. apps/api). Empty = repo default. See knowledge-base/workspaces/README.md.
depends-on: []         # [STORY-003, STORY-004]: must be done before this story can start
blocks: []             # [STORY-008]            : stories this one unblocks once done
incident-ref:          # optional: INC-YYYY-MM-DD-slug if this story comes from a postmortem
---

# STORY-NNN: [Short Title Using Domain Language]

## Intent

**Problem:** [who is struggling and what is broken or costly today]
**Desired outcome:** [what changes for the user or business]
**Why now:** [why this matters now]
**Key constraint:** [speed / cost / safety / accuracy / scale / maintainability]
**Smallest useful change:** [the smallest slice that meaningfully improves the outcome]

**As a** [persona], **I want** [outcome], **so that** [business benefit].

## Acceptance Criteria

<!-- Given/When/Then. Prefer 3–5 AC; 8+ means split the story. -->

- [ ] Given [precondition], when [action], then [expected outcome]
- [ ] Given [precondition], when [action], then [expected outcome]

## TDD Test Names

- `test_<what>_<condition>`: maps to AC above

## Assumptions

- [Inferred default or reversible decision: source/reason]

## Estimate

**Points:** [1 / 2 / 3 / 5 / 8]: [one-line justification, including unknowns]

## Boundaries *(omit empty subsections)*

**Constraints:** [tech, contract, performance, compliance: surfaced during research]
**Out of scope:** [intentional exclusions to prevent scope creep]
**Success signal:** [how we will know this story improved the situation]

## Risks *(omit if none)*

| Risk / Dependency | Impact | Mitigation |
|-------------------|--------|------------|
| [risk] | [what breaks] | [how to handle] |

## Feature Flag *(omit if none)*

`flag-name`: default OFF, [audience], cleanup after [milestone or date]. Registry row added to `knowledge-base/feature-flag-registry.md`.

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Do not copy the checklist here; record only story-specific evidence or approved exceptions.

- [ ] DoD met: yes / no
- [ ] Exceptions: none / [link to approved exception]
- [ ] AC walkthrough: each AC verified against running code (not skimmed)
- [ ] Before/after evidence: [metric, screenshot, or log line: match what the AC promised]
- [ ] Rollout notes: [feature-flag state, migration order, smoke checks: omit only if not user-visible]

---

## Implementation *(reserved: appended only for ≤3pt stories)*

For small stories (≤ 3 story points), slice-planner may append implementation detail here
instead of creating a separate `plans/PLAN-NNN-*.md`. See `agents/slice-planner.agent.md` § Save and handoff.
Contents: design approach, vertical slices, TDD steps, risks.
