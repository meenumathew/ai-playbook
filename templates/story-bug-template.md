---
issue-ref:
type: bug              # story | spike | bug | chore
status: refining       # refining | ready | in-progress | blocked | done
priority: normal       # low | normal | high | critical: default normal; raise on SEV1/SEV2 or postmortem follow-ups
workspace:             # optional: name of the workspace this bug belongs to, for example apps/api. Empty = repo default.
depends-on: []         # [STORY-003, STORY-004]: must be done before this fix can land
blocks: []             # [STORY-008]            : stories this fix unblocks once done
severity:              # SEV1 / SEV2 / SEV3 / SEV4: see knowledge-base/incident-response.md
regression-since:      # commit / version / date when the bug was introduced, if known
incident-ref:          # optional: INC-YYYY-MM-DD-slug if this bug came out of a postmortem
---

# BUG-NNN: [Short Symptom Using Domain Language]

> Filename prefix is `BUG-NNN-`, for example `stories/BUG-042-stale-cache-on-rotate.md`.
> Use this template when the deliverable is *fixing broken behaviour*: not new behaviour.
> If you're adding a feature, use `templates/story-template.md` instead.

## Symptom

**What is broken:** [observable behaviour, in user-visible terms: not the suspected cause]
**Who is affected:** [user segment, environment, scope]
**First reported:** [date / commit / version when noticed; not when introduced]
**Severity:** [SEV1 / SEV2 / SEV3 / SEV4: match the frontmatter]

## Reproduction

Minimal steps to trigger the bug. If it is not reliably reproducible, say so explicitly and link any captured evidence (logs, traces, screenshots).

1. [step]
2. [step]
3. [step]

**Expected:** [what should happen]
**Actual:** [what does happen]

**Reproduction rate:** [always / N out of M attempts / only under load / not reliably reproducible]

## Evidence

- [Log line, trace ID, screenshot, error message: link or quote, with PII stripped per `knowledge-base/security.md` § Data Handling]

## Suspected Root Cause *(omit if unknown)*

[1–3 sentences. State as a hypothesis with confidence level. If unknown, say "unknown: investigation needed" and consider a spike.]

## Regression Scope

**Introduced:** [commit / PR / version, if `regression-since` is set; otherwise "unknown"]
**Affected versions:** [range or list]
**Exposure:** [how many users / requests / records hit this path]

## Acceptance Criteria

<!-- Bug AC pin "the broken case is now correct": ideally one AC for the bug itself, plus regression-coverage AC. Prefer 2-4 total. -->

- [ ] Given the preceding reproduction steps, when [action], then [expected outcome from § Reproduction]
- [ ] A regression test fails before the fix and passes after: committed in the same change
- [ ] Adjacent behaviour [list explicitly] still works: characterization tests added if not covered

## TDD Test Names

- `test_<what>_<condition>`: the regression test mapping to AC #2

## Assumptions

- [Inferred default or reversible decision: source/reason]

## Estimate

**Points:** [1 / 2 / 3 / 5 / 8]: [one-line justification, including investigation cost]

## Boundaries *(omit empty subsections)*

**Constraints:** [tech, contract, performance, compliance: surfaced during investigation]
**Out of scope:** [related bugs intentionally not fixed in this story; link to follow-up stories]
**Success signal:** [evidence that this story fixed the situation in production: error rate drop, user reports, etc.]

## Risks *(omit if none)*

| Risk / Dependency | Impact | Mitigation |
|-------------------|--------|------------|
| [risk] | [what breaks] | [how to handle] |

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Do not copy the checklist here; record only bug-specific evidence or approved exceptions.

- [ ] DoD met: yes / no
- [ ] Exceptions: none / [link to approved exception]
- [ ] Bug-specific evidence: [regression test name, before/after error-rate metrics, customer comm if user-visible]

---

## Implementation *(reserved: appended only for ≤3pt fixes)*

For small fixes (≤ 3 story points), slice-planner may append implementation detail here
instead of creating a separate `plans/PLAN-NNN-*.md`. See `agents/slice-planner.agent.md` § Save and handoff.
Contents: design approach, regression test strategy, blast radius, rollback plan.
