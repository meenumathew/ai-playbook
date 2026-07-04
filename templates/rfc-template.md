# RFC-[NNNN]: [Proposal Title]

| Field | Value |
|-------|-------|
| **Status** | Proposed / Accepted / Rejected / Withdrawn / Superseded by RFC-NNNN |
| **Author** | @your-handle |
| **Date** | YYYY-MM-DD |
| **Target version** | vX.Y (the release this would land in if accepted) |
| **Supersedes** | RFC-NNNN or N/A |

## Summary

One paragraph: what you propose, in plain language. A reader should know after this paragraph whether to keep reading.

## Motivation

Why does the current state need to change? What problem are adopters, contributors, or the maintainer hitting that this proposal would resolve? Cite specifics: issue numbers, ADRs, KB sections, real adopter feedback. Avoid generic "this would be nice" framings.

## Proposal

The change in detail. Be specific enough that someone else could implement it from this section without asking you what you meant. Cover:

- Files added, removed, or renamed.
- New CLI commands or flags, with their full signatures.
- Config schema changes.
- Knowledge-base updates.
- Migration path for existing adopters.

If the proposal touches the deprecation policy (renames, removals, contract changes), state which surfaces are affected and which deprecation stage applies. After copying this file into `docs/rfcs/`, link to `../deprecation-policy.md`.

## Alternatives Considered

At least two. "Do nothing" counts as one. For each, say what it would look like and why you rejected it. RFCs without alternatives are opinions, not proposals.

| Alternative | Why rejected |
|---|---|
| | |
| | |

## Impact

What changes for whom?

| Audience | Impact |
|---|---|
| **Adopters who pin this version** | |
| **Adopters who upgrade** | |
| **Contributors** | |
| **Future maintainers** | |

If the proposal would trigger a deprecation cycle, list the deprecated surface, the replacement, and the target removal version.

## Open Questions

Things you do not yet know the answer to and want comment on. Number them so reviewers can reference each one.

1. ...

## Implementation Sketch

Not a full plan: a sketch. Roughly which slices, in what order, with which tests. Detailed planning happens after acceptance, in a `plans/PLAN-NNN-*.md` file or PR description.

---

*After copying this file into `docs/rfcs/`, link to `README.md` for the RFC process, status lifecycle, and what counts as "merge-able." Delete sections that do not apply rather than leaving them empty: but keep **Summary**, **Motivation**, **Proposal**, **Alternatives**, and **Impact** in every RFC.*
