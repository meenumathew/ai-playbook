# RESEARCH-NNN: [Story Title]

**Story:** stories/STORY-NNN-slug.md | PROJ-NNNN
**Date:** YYYY-MM-DD
**Type:** story-refiner | spike

<!-- Spike-only fields (delete if type = story-refiner): -->
**Timebox:** [agreed limit, e.g. 2 hours, half day]
**Decision:** proceed → story | discard | extend timebox (needs justification)

---

## Research Questions

1. [Question raised by the story]

## Findings

### Q1: [Question]

[Answer with `file:line` citations. Note what does NOT exist yet.]

**Confidence:** High / Medium / Low: *High = verified in source; Medium = inferred from patterns; Low = assumed or needs spike*

---

## Assumptions

Recommended defaults used without prompting because they are reversible or follow existing repo patterns. Material decisions go under Design Questions, not here.

- [Assumption]: [evidence or reason]

---

## Design Questions

Open questions asked one at a time, in priority order, with trade-offs grounded in research findings.

1. **[Question]**: [Options with trade-offs, citing `file:line`]
   - *Answer:* [User's response]

---

## ADR Candidates *(omit if none)*

Record only decisions that pass `docs/adr/README.md` § ADR Decision Criteria: hard to reverse, surprising without context, real trade-off.

| Decision | Why ADR-worthy | Chosen trade-off | Next step |
|----------|----------------|------------------|-----------|
| [Decision] | [Reason] | [Chosen option over alternatives] | docs-maintainer ADR / no ADR |

---

## What We're NOT Doing

- [Explicit scope boundaries: things this work intentionally does not address]

---

## Unknowns & Risks

- [Each unknown or risk on its own line]

---

## Read Budget

How many of the agent's read budget were used during this research, so future runs can judge whether the spend was proportionate to the question.

- **Reads used:** N / 20 *(or N / 10 at prototype tier; N / 40 if user said "deep research")*
- **Notable expensive lookups:** [files that took multiple hops to understand, or large files read in full: surface these so a similar future story can scope research faster]
