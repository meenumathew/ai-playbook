# RFCs (Requests for Comments)

RFCs are public proposals for changes that are too large for a single PR but smaller than a permanent architectural contract. This directory holds one RFC per file.

If you are not sure whether your change needs an RFC, see [§ When to write an RFC](#when-to-write-an-rfc) below. The default is no: most changes ship as PRs.

---

## Scope

RFCs in this directory propose changes to the AI Playbook repository itself: not changes inside adopter projects. Adopter projects can use the same template if they want a public-comment process of their own; they do so by copying [`../../templates/rfc-template.md`](../../templates/rfc-template.md) into their own repo.

---

## RFC vs ADR vs PR

Three venues, three different jobs. Pick the smallest one that fits.

| Venue | Records | When |
|---|---|---|
| **PR** | A change | Routine work: bug fix, doc fix, refactor, new test, additive feature with one obvious shape |
| **RFC** *(this directory)* | A proposal | Notable work: new agent, new CLI command, KB restructure, anything where the design has multiple plausible shapes and you want comment before building |
| **ADR** *(`docs/adr/`)* | A decision | Architectural work: durable contracts, scope boundaries, technology swaps, anything a future maintainer will ask "why?" about in 6–12 months |

Common patterns:

- A merged RFC often produces an ADR (the proposal becomes the durable record).
- A merged RFC sometimes produces only a PR (the proposal was small enough that no decision needs to outlive the change).
- An ADR rarely produces an RFC: by the time you write an ADR, the decision is already made.

If you find yourself opening an RFC for a change that fits in one paragraph of an existing knowledge-base file, close it and update the file instead.

---

## When to write an RFC

Open an RFC when **all** of the following are true:

| Criterion | Test question |
|---|---|
| **Multiple shapes** | Are there two or more credible designs, and the trade-off is non-obvious? |
| **Crosses files** | Will the change touch agents, CLI, knowledge base, and tests together? |
| **Worth public comment** | Would adopters or contributors want to weigh in before code lands? |

Examples that warrant an RFC:

- Adding a new agent (touches `agents/`, `commands/`, `evals/`, `README.md`, KB routing).
- Adding a new CLI subcommand (touches `cli.py`, `tests/`, `cli-reference.md`, deployment scripts).
- Restructuring the knowledge base (touches dozens of files; adopter packs may break).
- Changing a tool target's deployment layout.
- Adding a new language to the maintained set.
- Introducing a new config key with non-trivial semantics.

Examples that **do not** warrant an RFC:

- Fixing a bug, even a subtle one. Open a PR.
- Adding a test, refactoring, or fixing typos. Open a PR.
- Editing prose in an existing KB file. Open a PR.
- Renaming a function inside `src/`. Open a PR.
- Anything covered by an existing ADR. The decision is already made; just implement.

---

## Process

1. **Copy the template.** `cp templates/rfc-template.md docs/rfcs/NNNN-short-title.md`. Number is monotonic and never reused.
2. **Fill in the template.** Be specific about the problem, alternatives, and the proposal. Vague RFCs collect vague comments.
3. **Open a PR.** The PR title is the RFC title. The PR body says "RFC NNNN: <title>" and links to the RFC file.
4. **Set status to `Proposed`.** The frontmatter status field tracks the lifecycle.
5. **Open a discussion.** Comment on the PR inviting review. Tag adopters or contributors who care about the area if you know them.
6. **Wait for the comment window.** Minimum 7 calendar days from the PR opening (see [`GOVERNANCE.md`](../../GOVERNANCE.md) § Public Comment).
7. **Address comments.** Update the RFC body in response to feedback. The history lives in PR review threads.
8. **Maintainer decides.** Accepted RFCs are merged with status `Accepted`. Rejected RFCs are merged with status `Rejected` and a one-paragraph rationale, so the rejection is searchable. Withdrawn RFCs are closed without merging.

After acceptance:

- If the RFC implies a durable contract, write an ADR referencing the RFC number.
- Implementation lands as one or more follow-up PRs. The RFC is the design; the PRs are the build.
- Update the [Index](#index) below.

---

## Status Lifecycle

| Status | Meaning |
|---|---|
| **Proposed** | Open for comment. PR not yet merged. |
| **Accepted** | Merged. Implementation may be in progress or complete. |
| **Rejected** | Merged with rationale, so the decision is searchable. |
| **Withdrawn** | PR closed without merging. Author chose to abandon. |
| **Superseded by RFC-NNNN** | A later RFC replaced this one. Both files stay; the superseded one points forward. |

Numbers are monotonic and never reused, even for withdrawn or rejected RFCs.

---

## Anti-Patterns

| Anti-pattern | Why it fails |
|---|---|
| Opening an RFC and merging it the same day | Defeats the comment window; if no one had time to read it, the "public" in "public comment" is theatre |
| RFCs that propose three different things | Split them. One RFC, one proposal. |
| RFCs without alternatives | "We should add X" is an opinion, not an RFC. List what you considered and rejected. |
| Implementing before the RFC is accepted | The build pre-commits the decision. Either ship the work as a PR (no RFC needed) or wait for acceptance. |
| Closing a contentious RFC by adding a maintainer comment "decided offline" | The point of the venue is the public record. Decide in the thread or extend the window. |

---

## Index

The list below is kept fresh by hand. When you accept, reject, withdraw, or supersede an RFC, update the row.

| RFC | Title | Status | Date |
|---|---|---|---|
| [0002](0002-lessons-log.md) | A seeded, adopter-owned lessons log for negative results | Proposed | 2026-07-17 |

---

## Cross-References

- [`templates/rfc-template.md`](../../templates/rfc-template.md): copy this to start a new RFC
- [`docs/adr/README.md`](../adr/README.md): for durable architectural decisions
- [`GOVERNANCE.md`](../../GOVERNANCE.md): who accepts and how the comment window works
- [`docs/deprecation-policy.md`](../deprecation-policy.md): what counts as breaking and triggers a deprecation cycle
- [`CONTRIBUTING.md`](../../CONTRIBUTING.md): how PRs are reviewed and merged
