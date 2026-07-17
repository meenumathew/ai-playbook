# RFC-0002: A seeded, adopter-owned lessons log for negative results

| Field | Value |
|-------|-------|
| **Status** | Proposed |
| **Author** | @meenu |
| **Date** | 2026-07-17 |
| **Target version** | v1.1 |
| **Supersedes** | N/A |

## Summary

Add `knowledge-base/lessons.md`: a small, dated, append-then-curate log of negative results ("we tried X in this codebase; it failed because Y") that agents load at plan time and the retrospective skill sweeps with a promote-or-expire policy. To make the file writable by adopters without fighting the deploy machinery, introduce a **seeded file class**: a file the playbook copies on first deploy, then never overwrites, never prunes, and excludes from the drift fingerprint. The log is a staging tier for the learning hierarchy, not a destination: entries that recur get promoted into a KB rule or a contract test; entries that go stale get deleted.

## Motivation

The playbook already externalizes learning at the strong end of the hierarchy. `skills/retrospective` turns session friction into KB proposals, and recurring mistakes become KB rules or contract tests that block the mistake mechanically (`philosophy.md` § Code Quality Signals: a fix needed across sessions belongs in the environment, not the prompt).

One class of learning has no home: **negative results**. The retrospective's Step 2 routes findings to targets (`design-patterns.md`, `domain-language.md`, `docs/limitations.md`, ADRs, `testing.md`, `performance.md`), and every target holds positive knowledge: a rule, a term, a limitation, a decision. "We tried the async consumer refactor and it deadlocked under the test harness; don't re-try without fixing the harness first" fits none of them. A full KB rule is too heavy for a one-off dead end, and an ADR records decisions, not failed attempts. So dead ends today live in the weakest tier: someone re-explains them in the prompt each session, which costs tokens and fails silently when nobody remembers to.

There is also a mechanical blocker that any design must solve first, and it is why this needs an RFC rather than a PR. Every file the playbook deploys is expected to match source byte for byte:

- `upgrade.py` compares a fingerprint of deployed files against source; any adopter append would register as permanent `drift`, and the next `deploy` would overwrite the adopter's accumulated lessons.
- `fs.py` (`expected_deployed_files`) treats deployed files with no source counterpart as orphans, so `--prune` would delete a lessons file the adopter created themselves. Disabled agent files (`*.agent.md.disabled`) are already special-cased at prune time, which proves the need for a preserved class but does not cover this case.

Playbook content is maintainer-owned; lessons are adopter state. The current machinery has no file class for adopter state that the playbook seeds.

## Proposal

### 1. Seeded file class in the deploy pipeline

Add a `SEEDED_FILES` set (initially `{"knowledge-base/lessons.md"}`) with these semantics:

- **Deploy:** copy the file only when it is absent at the destination. Report per-file status `seeded` on first copy and `preserved` after that (alongside the existing copy statuses in `fs.py`).
- **Fingerprint:** exclude seeded files from `compute_source_fingerprint` and from the deployed-side comparison, so adopter appends never register as `drift` in `upgrade.py`.
- **Prune and doctor:** always include seeded files in the expected set regardless of content, the same preservation rule `expected_deployed_files` already documents for disabled agent files. `doctor` reports the file as `adopter-owned (seeded)` instead of comparing it to source.
- **Backup:** `deploy` never overwrites the file, so the existing backup flow needs no change; state this in a test rather than assuming it.

### 2. The seed file

`knowledge-base/lessons.md` ships with standard KB frontmatter, a scope statement, and an entry format. Scope, stated in the file itself:

- **In scope:** dead ends and negative results specific to this project. "Tried X, failed because Y, evidence Z."
- **Out of scope:** rules (belong in a KB file), terms (`domain-language.md`), decisions (ADRs), limitations (`docs/limitations.md`). An entry that restates a rule from another KB file is a promotion candidate, not a lesson.

Entry format, one per lesson:

```markdown
## 2026-07-17: async consumer refactor deadlocks under test harness
- Tried: moving the consumer loop to asyncio while keeping the sync harness
- Failed because: harness fixtures block the event loop; consumer never acks
- Evidence: PR #142 CI run, `test_consumer_ack` timeout
- Status: active
```

`Status` is one of `active`, `promoted: <target file or test>`, or `expired`. Promoted and expired entries are deleted at the next sweep; the status field exists so a sweep is reviewable before the deletion lands.

### 3. Loading trigger

Recall, not storage, is the hard problem: a lesson helps only when it is loaded at the moment the mistake is about to recur. The file gets a Triggered row in `knowledge-base/INDEX.md`: load at plan time, before proposing an approach in an area the log names. The planning agents (`slice-planner`, `xp-pair-programmer` at its plan step) name it explicitly in their KB-loading lists. The file is never always-loaded; an always-loaded memory file grows into the token cost this proposal is trying to remove.

### 4. Curation: promote or expire

The retrospective skill gains two things:

- Step 2's target map gains one row: dead end or negative result routes to `lessons.md` (append, subject to the same approval gate as every other retrospective change, `CLAUDE.md` § Shared Rules § Approval gate). Each entry must carry date and evidence so a wrong diagnosis can be challenged later instead of persisting as fact.
- A sweep step: an entry that has recurred (the same dead end hit again, or cited in two or more sessions) gets promoted up the hierarchy into a KB rule or a contract test and marked `promoted`; an entry that has not been cited within the expiry horizon gets marked `expired`. Marked entries are deleted at the next sweep.

A size cap keeps the pressure mechanical: `doctor` warns when the deployed `lessons.md` exceeds the cap (proposed: 120 lines). The cap is the forcing function that stops the middle rung from becoming a junk drawer and keeps the incentive to push learning down to contract tests intact.

### 5. Source-repo guardrails

- Contract tests: seed file exists with valid frontmatter; `INDEX.md` has the row; the retrospective skill references `lessons.md` in its target map; planning agents reference it.
- Unit tests on the seeded class: deploy copies when absent, preserves when present, fingerprint ignores it, prune preserves it, `doctor` reports `adopter-owned (seeded)`.
- The KB duplication guard (12-word n-gram test in `test_kb_integrity.py`) applies to the seed as shipped; the seed is static in source, so this costs nothing and keeps the scope statement from restating rules that live elsewhere.
- `CLAUDE.md` gains at most one pointer line, inside the current `MAX_LINES` budget in `tools/check-claude-md-size.py`.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Do nothing: retrospective + KB rules cover it | Negative results fit no existing retrospective target; a full KB rule per dead end is too heavy, so dead ends stay in the prompt tier and get re-explained (or forgotten) each session |
| Always-loaded memory file (a "memories" section in `CLAUDE.md` or an always-on KB file) | Token cost grows without bound and violates the KB efficiency rule; the goal is to stop paying tokens for re-guidance, not to relocate the payment |
| Per-user assistant memory outside the repo | Not shared across the team or across agents, not reviewable, not versioned with the code it describes |
| Promote everything straight to a contract test | Right destination for recurring lessons, and this proposal keeps that pressure; wrong weight for a one-off dead end that may never recur |
| One ADR per dead end | ADRs record decisions a future maintainer will ask "why?" about; a failed attempt is not a decision, and the volume would bury real decisions |
| Ship no seed; document a convention for adopters to create their own file | Prune deletes files with no source counterpart, so the convention breaks the first time an adopter runs `deploy --prune`; the deploy machinery change is required either way, and the seed makes the format discoverable |

## Impact

| Audience | Impact |
|---|---|
| **Adopters who pin this version** | None. No deployed file changes until they upgrade. |
| **Adopters who upgrade** | Next `deploy` seeds `lessons.md` (the file is absent, so the seed-once rule copies it). Existing files are untouched. No deprecation cycle: the change is additive. |
| **Contributors** | One new deploy concept (seeded files) documented in `docs/architecture.md`; new tests to keep green. |
| **Future maintainers** | The seeded class is generic; any future adopter-state file reuses it instead of inventing another special case. |

## Open Questions

1. **Cap value and enforcement.** Is 120 lines right, and should `doctor` warn or fail when exceeded? Warn keeps the adopter in control; fail makes the sweep unavoidable.
2. **Expiry horizon.** What marks an entry stale: N retrospectives without citation, a calendar window (90 days), or maintainer judgment at sweep time?
3. **Workspace overlays.** Should monorepo adopters get per-workspace lessons files via the existing `knowledge-base/workspaces/<path>/` overlay mechanism, or does one root file suffice until someone asks?
4. **Name.** `lessons.md` reads broad; `dead-ends.md` states the scope in the filename. Scope creep toward "general agent memory" is the main failure mode, so the name is not cosmetic.

## Implementation Sketch

1. **Deploy machinery:** `SEEDED_FILES` in `paths.py`; seed-once copy and `seeded`/`preserved` statuses in `fs.py`; fingerprint exclusion in `fs.py` + `upgrade.py`; prune preservation; `doctor` reporting and size warning. Unit tests alongside each.
2. **Content:** the seed file, the `INDEX.md` row, the `CLAUDE.md` pointer line, agent KB-loading references.
3. **Retrospective skill:** target-map row and sweep step.
4. **Guardrails and docs:** contract tests in `tests/acceptance/contract_data.py` and `tests/unit/`, `docs/architecture.md` section on the seeded class, `docs/cli-reference.md` notes for `deploy`/`doctor` output changes.

Slices 1 and 2 are independent until the contract tests in slice 4 tie them together; detailed planning happens after acceptance.

---

See [`README.md`](README.md) for the RFC process, status lifecycle, and what counts as merge-able.
