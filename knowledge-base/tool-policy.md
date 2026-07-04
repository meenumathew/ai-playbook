---
id: tool-policy
size: small
tldr: Per-agent tool allowance matrix and the vendor-neutral operation-ID rule. Agents cite this when picking a tool; deltas live in each agent file.
load_when: tool policy, permission, host adapter, issue fetch, notifier, vendor-neutral, operation ID, agent ↔ skill
audience: all
canonical_for: per-agent tool allowance matrix, vendor-neutral operation-ID rule, agent-skill operation contract
cross_refs: design-patterns.md, skills/host-adapter/SKILL.md, skills/notifier/SKILL.md, skills/issue-fetch/SKILL.md
verified: 2026-05-28
---

# Tool Policy

## Agent Use

- **Read first:** the matrix below: it is the per-agent default; each agent file may declare deltas, never restate cells.
- **Load deeper only on trigger:** vendor-neutral operation IDs (`design-patterns.md` § Vendor-Neutral by Design) when an agent action would shell out to a vendor command.

## Per-Agent Matrix

Columns are tool families. Rows are agents. `✓` allowed, `✗` denied, `R` read-only.

| Agent | Issue tracker | Context7 | Host PR/MR | Git (commit) | Git (tag/push) | Notifier | Web search |
|---|---|---|---|---|---|---|---|
| story-refiner | R (best-effort) | ✓ | ✗ | ✗ | ✗ | ✗ | ✓ |
| slice-planner | R (best-effort) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| xp-pair-programmer | R (session start only) | ✗ | ✗ | ✓ (commit only) | ✗ | ✗ | ✗ |
| diff-reviewer | R | ✗ | ✓ via host-adapter (`pr.diff`, `pr.review`) | ✗ | ✗ | ✗ | ✗ |
| release-captain | R | ✗ | ✓ via host-adapter (`pr.create`, `pr.checks`, `pr.merge`) | ✓ (release commit) | ✓ (tag + push, approval-gated per push) | ✓ via notifier skill (smoke / release events) | ✗ |
| incident-responder | R | ✗ | R via host-adapter (`pr.diff`, `pr.checks`) | ✗ | ✗ | ✓ via notifier skill (SEV1 approval-gated) | ✗ |
| code-inspector | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| docs-maintainer | ✗ | ✓ (ADR / how-to research) | ✗ | ✗ | ✗ | ✗ | ✗ |

## Vendor-Neutral Operation IDs

Agents call dotted operation IDs (`host.pr.create`, `notify(release_shipped, …)`, `issue.fetch`): never vendor commands (`gh`, `glab`, `tea`, Bitbucket REST, `curl` chat APIs, `jira-cli`). The skill maps the operation ID to whatever provider `.ai-playbook.toml` selects.

Detail and exceptions: `knowledge-base/design-patterns.md` § Vendor-Neutral by Design.

## Routing Rules

- **Host PR/MR ops** always go through `skills/host-adapter/SKILL.md`.
- **Outbound notifications** go through `skills/notifier/SKILL.md`. Default notifier provider is `none` (no-op); adopters opt in via `.ai-playbook.toml [notifier]`.
- **Issue fetch** goes through `skills/issue-fetch/SKILL.md`.
- **Local file tools** (Glob, Grep, Read, Write) are always available.

Agents may note **true deltas** in their own `## Tool Policy` section but must not restate cells from the matrix above.
