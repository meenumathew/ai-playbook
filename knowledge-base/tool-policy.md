---
id: tool-policy
size: small
tldr: Per-agent tool allowance matrix and the vendor-neutral operation-ID rule. Agents cite this when picking a tool; deltas live in each agent file.
load_when: tool policy, permission, host adapter, issue fetch, notifier, vendor-neutral, operation ID, agent ↔ skill
audience: all
canonical_for: per-agent tool allowance matrix, operation-ID enforcement in agent tool policy, agent-skill operation contract
cross_refs: design-patterns.md, skills/host-adapter/SKILL.md, skills/notifier/SKILL.md, skills/issue-fetch/SKILL.md
verified: 2026-07-30
---

# Tool Policy

## Agent Use

- **Read first:** the matrix below: it is the per-agent default; each agent file may declare deltas, never restate cells.
- **Load deeper only on trigger:** vendor-neutral operation IDs (`design-patterns.md` § Vendor-Neutral by Design) when an agent action would shell out to a vendor command.

## Per-Agent Matrix

Columns are tool families. Rows are agents. Use `allowed`, `denied`, and `read-only` as the cell states.

| Agent | Issue tracker | Context7 | Host PR/MR | Git (commit) | Git (tag/push) | Local exec (build/test/lint) | Notifier | Web search |
|---|---|---|---|---|---|---|---|---|
| story-refiner | read-only (best-effort) | allowed | denied | denied | denied | denied | denied | allowed |
| slice-planner | read-only (best-effort) | denied | denied | denied | denied | denied | denied | denied |
| xp-pair-programmer | read-only (session start only) | denied | denied | allowed (commit only) | denied | allowed (test/lint/format loop) | denied | denied |
| diff-reviewer | read-only | denied | allowed via host-adapter (`host.pr.diff`, `host.pr.review`) | denied | denied | allowed (verify-only: run the suite, e.g. refactoring PRs; never edit) | denied | denied |
| release-captain | read-only | denied | allowed via host-adapter (`host.pr.create`, `host.pr.checks`, `host.pr.merge`) | allowed (release commit) | allowed (tag + push, approval-gated per push) | allowed (release gates + smoke) | allowed via notifier skill (smoke / release events) | denied |
| incident-responder | read-only | denied | read-only via host-adapter (`host.pr.diff`, `host.pr.checks`) | denied | denied | denied (recommend, never execute) | allowed via notifier skill (SEV1 approval-gated) | denied |
| code-inspector | denied | denied | denied | denied | denied | denied (read and grep only) | denied | denied |
| docs-maintainer | denied | allowed (ADR / how-to research) | denied | denied | denied | allowed (doc lint gates only) | denied | denied |

## Vendor-Neutral Operation IDs

Agents call dotted operation IDs (`host.pr.create`, `notify(release_shipped, …)`, `issue.fetch`): never vendor commands (`gh`, `glab`, `tea`, Bitbucket REST, `curl` chat APIs, `jira-cli`). The skill maps the operation ID to whatever provider `.ai-playbook.toml` selects.

Detail and exceptions: `knowledge-base/design-patterns.md` § Vendor-Neutral by Design.

## Routing Rules

- **Host PR/MR ops** always go through `skills/host-adapter/SKILL.md`.
- **Outbound notifications** go through `skills/notifier/SKILL.md`. Default notifier provider is `none` (no-op); adopters opt in via `.ai-playbook.toml [notifier]`.
- **Issue fetch** goes through `skills/issue-fetch/SKILL.md`.
- **Local file tools** (Glob, Grep, Read, Write) are always available; each agent's write scope is bound by the deltas in its own `## Tool Policy` section (e.g. code-inspector writes to `audits/` only).

Agents may note **true deltas** in their own `## Tool Policy` section but must not restate cells from the matrix above.
