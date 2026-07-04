# Architecture Decision Records (ADRs)

This directory holds one ADR per file, following a [Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)-style minimal format with Status and Date frontmatter. See [`../../templates/adr-template.md`](../../templates/adr-template.md).

## Scope

The ADRs in this directory record decisions about the AI Playbook repository itself: not decisions made inside adopter projects. The directory is deliberately outside the `ai-playbook deploy` path. Adopters create their own `docs/adr/` in their own repository, using [`../../templates/adr-template.md`](../../templates/adr-template.md) as the starter.

## Convention

- **One file per decision.** `NNNN-short-title-in-kebab-case.md`.
- **Numbering:** zero-padded, monotonic, never reused (if you deprecate an ADR its number stays; a new ADR supersedes it).
- **Status lifecycle:** `Proposed` → `Active` → (`Superseded by ADR-NNNN` | `Deprecated`).
- **Template:** copy [../../templates/adr-template.md](../../templates/adr-template.md) to start a new ADR.

## Why `docs/adr/` and not a single file

Industry standard (Nygard 2011, MADR, arc42, Spotify, AWS Well-Architected) is one file per decision in `docs/adr/`:

- **Small diffs**: a new ADR touches one file; no merge conflicts with unrelated decisions.
- **Discoverability**: file-system listing is the index; search engines and IDEs index each title.
- **Link stability**: an ADR file's path is permanent; linking to a line range inside a monolithic file breaks when others add entries.
- **Agent parity**: slice-planner, code-inspector, diff-reviewer, docs-maintainer, and story-refiner all glob `docs/adr/**/*.md` and surface the result; no single file has to hold every decision.

The single-file `decisions.md` that earlier drafts used is no longer shipped: adopters stamp each decision as its own file from [`../../templates/adr-template.md`](../../templates/adr-template.md).

## When to write an ADR

Record an ADR when, and only when, the decision still matters to a reader **six to twelve months from now**.

### ADR Decision Criteria (Recommended Standard)

Use a high bar so ADRs stay sparse, searchable, and useful. This matches common ADR practice: record durable decisions and their context, not routine implementation work.

Create an ADR only when all three criteria are true:

| Criterion | Test question | ADR-worthy signal |
|---|---|---|
| **Hard to reverse** | Would changing this later be meaningfully expensive? | Data model, public contract, architecture boundary, provider choice, compliance constraint |
| **Surprising without context** | Would a future maintainer ask "why this way?" | The decision rejects the obvious/default path or depends on non-obvious constraints |
| **Real trade-off** | Were there viable alternatives with different costs? | The team chose one option over another for explicit reasons |

**Write an ADR when:**

| Trigger | Example |
|---|---|
| Someone sets or changes a scope boundary | "Drop Python 3.11 support," "Drop Jira integration" |
| Someone establishes a convention or contract | "Every agent must declare a read budget," "Stories > 3 points require a plan file" |
| The team chooses a technology over alternatives | "Typer over Click," "uv over pip," "MADR over Nygard" |
| A trade-off is likely to be re-litigated | "Feature flags default OFF," "No network calls in tests" |
| An earlier decision reverses | Creates a new ADR that supersedes the old one |
| An external constraint locks in | "Must stay MIT licensed," "Must support offline mode" |

**Do *not* write an ADR for:**

| Anti-trigger | Why not |
|---|---|
| In-flight cleanup or sprint work | Belongs in a plan or story, not the decision log |
| "Renamed X to Y" | After the rename lands, the old name disappears; migrations are not decisions |
| Bug fixes, refactors, or feature additions | These are commits and PRs |
| Personal preferences or code style | Belongs in `knowledge-base/style-guide.md` |
| Anything expressible in one paragraph of an existing KB file | Update the KB file instead |

**Lifecycle rules:**

- Status progresses: `Proposed` → `Active` → (`Superseded by ADR-NNNN` \| `Deprecated`).
- Numbering is monotonic and permanent: never reused, even if an ADR is withdrawn.
- One decision per file. If you catch yourself writing "and also decided Y," split it into two ADRs.
- When superseding, link both directions: the new ADR references the old; the old ADR's status points to the new one.

**Heuristic:** *"Would a maintainer want to link someone to this ADR six months from now when they ask why X happened?"* If yes → ADR. If no → plan, story, commit message, or KB update.

## Index

- [ADR-0001: Bitbucket Server / Data Center is not supported](0001-bitbucket-server-not-supported.md): Active, 2026-05-20

> `tests/acceptance/test_harness_release_contracts.py::test_adr_index_in_readme_matches_adr_files` keeps the index fresh. When you add or update an ADR, run the test: on drift it prints the corrected bullet block ready to paste.
