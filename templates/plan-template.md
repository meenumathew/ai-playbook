# PLAN-NNN: [Story Title]

<!-- STATUS: NOT_STARTED -->
<!-- CURRENT_TASK: 1 -->
<!-- CURRENT_STEP: RED -->
<!-- LAST_GREEN_COMMIT: none -->

**Story:** stories/STORY-NNN-slug.md | PROJ-NNNN

---

## Architecture Overview

**Domain objects:** [list]
**Services:** [list]
**Infrastructure:** [list]
**Feature flags:** [flag-name: default OFF/ON] *(omit if none)*

## Context *(omit if straightforward)*

[2–3 sentences: what is being built, where it lives, current state of the repo]

**Constraints / overrides:**

- [Each user constraint or AC override]

## Assumptions

- [Recommended default used without prompting because it is reversible / follows repo pattern]

## Files to Create / Modify

[Directory tree or bullet list]

## Design Questions *(for medium/large or ambiguous work)*

- [Question 1: include the trade-off and chosen direction]
- [Question 2: include the trade-off and chosen direction]

## Fixtures / Setup *(test suite stories only)*

[Fixture contracts in plain English: scope, what they provide, teardown]

---

## Progress

- [ ] Task 1: [Name]
- [ ] Task 2: [Name]

## Tasks

### Task N: [Name: Layer]
>
> [One sentence: what this delivers and why]

**Layer:** Domain | Service | Infrastructure
**Depends on:** Task N-1 | Nothing

TDD Steps:

- [AT] RED `test_ac_<what>_<condition>` (real entry point, fakes at external boundaries) → GREEN
- [Unit] RED `test_name` → GREEN → REFACTOR
- [Integration] RED `test_name` (real external service) → GREEN → REFACTOR
- COMMIT `feat(scope): ...` once, after the task's last step (one commit per task, never per TDD step)

---

## Test Summary

| Type | Count | Target |
|------|-------|--------|
| Unit | N | |
| AT (acceptance) | N | One per AC |
| Integration | N | Only if story touches external service |
| Post-deploy | N | Only if story creates/modifies them |

---

## CI / Workflow *(omit if no CI changes)*

[Trigger, inputs, steps outline: highlight secrets scoping and failure behaviour]

## Risks

[Each risk on its own line: flag destructive PROD operations and blast radius prominently]

## Discovered

[Work discovered during implementation: added by xp-pair-programmer at runtime. User decides: now or later.]

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Do not copy the checklist here; record only plan-specific evidence or approved exceptions.

- [ ] DoD met: yes / no
- [ ] Exceptions: none / [link to approved exception]
- [ ] Plan-specific evidence: [commands, test suites, rollout checks]
