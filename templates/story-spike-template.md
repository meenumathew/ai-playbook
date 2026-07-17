---
issue-ref:
type: spike            # story | spike | bug | chore
status: refining       # refining | ready | in-progress | blocked | done
workspace:             # optional: name of the workspace this spike belongs to (e.g. apps/api). Empty = repo default.
depends-on: []         # [STORY-003]: spikes rarely depend on other work; usually empty
blocks: []             # [STORY-008]: stories this spike unblocks once the question is answered
timebox:               # ISO 8601 duration (PT4H) or wall-clock budget: required before starting
deliverable:           # research/RESEARCH-NNN-<slug>.md: required, the spike's only artefact
---

# SPIKE-NNN: [Question Being Investigated, in Question Form]

> Filename prefix is `SPIKE-NNN-` (e.g. `stories/SPIKE-007-postgres-vs-clickhouse.md`).
> Spikes are timeboxed *learning* work: the deliverable is a research file, not code.
> Spike code is throwaway and never committed to main (see `CLAUDE.md` § Workflow).
> Spikes do **not** carry AC or story points. If you find yourself writing them, you have a story, not a spike.

## Question

**What we need to learn:** [the single question that, when answered, unblocks the next decision]
**Why we don't know yet:** [what's missing: is it tooling, data, prior art, prototype evidence?]
**Decision this enables:** [the call we'll make once the question is answered]

## Timebox

**Budget:** [hours / days: match the frontmatter `timebox:`]
**Stop condition:** "We stop when [the question above is answered to the confidence threshold below], OR when the timebox expires: whichever comes first."
**Confidence threshold:** [low / medium / high: high needs a working prototype; low needs a written argument]

## Approach

How we'll investigate. List the cheapest paths first; abandon expensive ones if the cheap paths answer the question.

1. [Read existing docs, prior incidents, ADRs, related code]
2. [Talk to N humans who've touched this area]
3. [Build the smallest possible prototype to test the riskiest assumption]
4. [Compare options on the dimensions that matter: list them]

## Out of Scope

What this spike will *not* answer. Write these down so the spike doesn't expand into a full design.

- [Adjacent question explicitly deferred to a follow-up spike or story]

## Deliverable

**Research file:** `research/RESEARCH-NNN-<slug>.md`: the spike's only output. If story-refiner already saved this file while refining the spike, **extend it** with the findings below: append new sections, never overwrite the refinement research. Contents:

- The question (verbatim from above)
- The answer, with confidence level
- Evidence: prototypes built, sources read, humans consulted
- Recommended next step: a story, another spike, or "drop this: not worth pursuing"

**No code is committed to main from a spike.** Throwaway prototypes live in a branch that is *not* merged.

## Assumptions

- [What we're taking as given without verifying: call out so the spike doesn't accidentally validate them]

## Risks *(omit if none)*

| Risk / Dependency | Impact | Mitigation |
|-------------------|--------|------------|
| [risk] | [what breaks if this risk lands during the spike] | [how to handle] |

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Spikes have a *reduced* DoD: record only spike-specific evidence.

- [ ] Question answered with stated confidence, OR timebox expired and findings recorded honestly
- [ ] Research file saved at `research/RESEARCH-NNN-<slug>.md`
- [ ] Recommended next step written: story, follow-up spike, or "drop"
- [ ] Throwaway prototype branch deleted or marked `do-not-merge`
- [ ] Decision-makers notified (link the research file in the relevant chat / ticket)
