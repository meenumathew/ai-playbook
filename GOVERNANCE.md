# Governance

How decisions get made in the AI Playbook project, who can make them, and how that will change as the project grows.

This document is the contract between maintainers and adopters. If you depend on this playbook, the rules below are what you can rely on.

---

## Project Status

**Single-maintainer.** AI Playbook is currently designed, written, and released by one maintainer. There is no committee, no RFC quorum, no formal voting: the maintainer owns every decision and is accountable for every release.

Single-maintainer is a starting state, not a permanent one. The transition criteria below define when this changes.

---

## Roles

| Role | Who | Responsibilities |
|---|---|---|
| **Maintainer** | The named owner in `pyproject.toml` (`authors`) | Merges PRs, cuts releases, decides scope, owns security response, has final say on every decision |
| **Contributor** | Anyone who opens a PR or issue | Proposes changes via PR, follows [`CONTRIBUTING.md`](CONTRIBUTING.md), participates in review |
| **Adopter** | Any team or individual using the playbook | Pins versions, reads release notes, files issues, follows the deprecation policy |

There is no separate "reviewer," "committer," or "TSC" role today. When the project moves to multi-maintainer, those roles will be defined in this file as part of the transition.

---

## Decision-Making

Decisions fall into three sizes. Each size has its own venue.

| Size | Use | Venue | Approver |
|---|---|---|---|
| **Routine** | Bug fix, doc fix, test addition, refactor that does not change a contract | PR | Maintainer review on the PR |
| **Notable** | New agent, new CLI command, new KB file, new language support, breaking-but-contained change | RFC under [`docs/rfcs/`](docs/rfcs/) | Maintainer accepts or rejects after public comment window (≥ 7 days) |
| **Architectural** | Durable boundary, public contract, technology swap, scope reversal | ADR under [`docs/adr/`](docs/adr/) when it meets the ADR criteria | Maintainer. ADRs record decisions, not routine release work. |

Choosing the venue:

- A change too large for a single PR but smaller than a permanent contract → **RFC** (see [`docs/rfcs/README.md`](docs/rfcs/README.md)).
- A decision that is durable, surprising without context, and costly to reverse → **ADR** (see [`docs/adr/README.md`](docs/adr/README.md)).
- Something that fits in a paragraph of an existing knowledge-base file → no RFC, no ADR: update the file.

RFCs and ADRs are not interchangeable. RFCs propose; ADRs record. A merged RFC produces an ADR only when the accepted decision meets the ADR bar; routine implementation remains PR + changelog.

---

## Public Comment

For RFCs, the maintainer opens a discussion thread on the PR and waits at least 7 calendar days before merging or rejecting. The clock can be paused for holidays, security embargoes, or maintainer absence; resumption is announced in the thread.

Routine PRs and ADRs (which record an already-made decision) do not require a comment window. Security fixes follow [`SECURITY.md`](SECURITY.md) and may merge immediately.

### Decision SLA and intake limits

Single-maintainer projects fail when RFCs age silently. Three explicit rails keep throughput predictable:

| Rule | Value | Rationale |
|---|---|---|
| **Decision SLA** | The maintainer resolves an RFC (Accepted, Rejected, Request changes, or Withdrawn) within **14 calendar days** after the comment window closes. | Bounds the worst-case wait from "indefinite" to a fortnight. Bound is on the maintainer, not the proposer. |
| **Pause discipline** | If the maintainer will be unavailable for more than 7 consecutive days, they post a `Status: paused; back YYYY-MM-DD` comment on every open RFC and resume the clock on return. | Replaces silent drift with public absence. |
| **Open-RFC cap** | At most **3 RFCs in `Status: Proposed` at any one time**. Additional proposals are queued in a single tracking issue (`RFC backlog`) until capacity reopens. | Bounds concurrent cognitive load. Backlog issue is public so contributors see the queue. |

The decision SLA does not require acceptance: `Request changes` (with concrete revisions) is a valid resolution that resets the comment window for the new revision. What is not valid is no comment at all.

### Accepting / rejecting an RFC (operational steps)

The rules above say "what": these steps say "how". Apply them in order; deviating from this sequence has caused index drift in the past.

**Accepted:**

1. Update the RFC's frontmatter table: change `**Status**` to `Accepted`, add an `**Accepted**` row with today's date.
2. If the RFC's design has already been implemented in the same PR or a recent merged PR, also add a `**Landed in**` row pointing at the implementation (commits, KB files, or the changelog entry that records the move). For RFCs accepted ahead of implementation, leave `**Landed in**` blank: fill it when the implementation lands.
3. Update [`docs/rfcs/README.md`](docs/rfcs/README.md) `## Index` row: change `Proposed` → `Accepted`, refresh the date column.
4. Decide whether the acceptance also needs an ADR. The bar lives in [`docs/adr/README.md`](docs/adr/README.md): durable contracts and "future-maintainer-asks-why" decisions get an ADR; routine implementation does not. If yes, write the ADR before merging the RFC PR so the ADR number is visible in the RFC's `Related` section.
5. Merge the RFC PR. The merge commit subject is `rfc: accept RFC-NNNN: <short title>` (Conventional Commit `rfc:` is reserved for this).
6. If the RFC creates follow-up work (an implementation effort that doesn't land with the acceptance), open the tracking issue or issues and link from the RFC's `Implementation sketch` section.

**Rejected:**

1. Frontmatter `**Status**` → `Rejected`. Add a `**Rejected**` row with the date and a one-paragraph rationale (this is the searchable record).
2. Index row: `Proposed` → `Rejected`.
3. Merge the RFC PR (yes, merge: the rejection is the historical artefact). Commit subject: `rfc: reject RFC-NNNN: <short title>`.
4. If the rejection encloses a counter-proposal worth pursuing later, open a backlog issue and link from the RFC's `Alternatives` section.

**Withdrawn:**

1. Frontmatter `**Status**` → `Withdrawn`. Add `**Withdrawn**` with the date and a brief reason (one or two lines).
2. Index row: `Proposed` → `Withdrawn`.
3. Close the RFC PR without merging. Withdrawn RFCs do not enter the historical record by merge: the closed PR carries the discussion.

In all three cases: never delete an RFC file or recycle its number. Numbers are monotonic and permanent (RFCs README § Status Lifecycle).

---

## Compatibility Promise

The playbook follows [Semantic Versioning](https://semver.org/). What "breaking" means in practice is defined in [`docs/deprecation-policy.md`](docs/deprecation-policy.md): that document is the binding contract.

Summary, in priority order:

1. **CLI surface** (`ai-playbook` subcommands, flags, exit codes): covered by SemVer; deprecation cycle required before removal.
2. **Agent IDs and slash-command names**: covered by SemVer; renames require a deprecation cycle.
3. **Configuration schema** (`.ai-playbook.toml`, `.playbook-version`): covered by SemVer; new keys are additive minor changes; removed or repurposed keys are breaking.
4. **Knowledge-base file paths** referenced from agents: covered by SemVer; renames require a deprecation cycle so adopter customizations and packs do not silently break.
5. **Knowledge-base file contents**: not covered by SemVer. Prose can be revised at any time. If your team depends on specific wording, vendor it into a pack.
6. **Internal Python API** (`src/deploy_ai_playbook/*` excluding the CLI entry points): not covered. Importing it from outside the playbook is unsupported.

Full details, deprecation timelines, and the warning surface in `ai-playbook doctor` live in [`docs/deprecation-policy.md`](docs/deprecation-policy.md).

---

## Conflict Resolution

In single-maintainer mode the maintainer has final say. Adopters who disagree have three remedies, in order of cost:

1. **Open an RFC.** Proposals with a credible alternative are considered on the merits.
2. **Pin the previous version.** SemVer guarantees a stable surface within a major.
3. **Fork.** The MIT license permits this. The maintainer will not block forks and will not pursue trademark claims against fair-use derivatives.

When the project moves to multi-maintainer, conflict resolution will switch to a documented voting model defined in this file at that time.

---

## Security

Security reports follow [`SECURITY.md`](SECURITY.md), not this document. Security fixes can ship outside the normal RFC and deprecation cycles.

---

## Transition to Multi-Maintainer

This project will move out of single-maintainer mode when **all** of the following are true:

| Criterion | Why |
|---|---|
| At least one external contributor has merged 5+ non-trivial PRs over 90+ days | Demonstrates sustained engagement, not a drive-by |
| The original maintainer formally invites them | Maintainership is granted, not claimed |
| The new maintainer accepts in writing (PR to this file) | Public, durable record |
| An ADR records the transition | Future maintainers can audit how the role was added |

When that happens, this document will be updated to define:

- How maintainers are added and removed.
- The voting threshold for contested decisions (default proposal: simple majority, with the longest-tenured maintainer breaking ties).
- How RFC acceptance changes (default proposal: any maintainer can accept after the comment window; any maintainer can block, escalating to a vote).
- A code-of-conduct enforcement process beyond [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) § Enforcement.

Until then, the rules above are the rules.

---

## Changes to This Document

Material changes to decision rights, compatibility promises, or maintainer transition criteria require an ADR under [`docs/adr/`](docs/adr/). Editorial clarifications and examples use the normal PR path.
