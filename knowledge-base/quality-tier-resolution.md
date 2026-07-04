---
id: quality-tier-resolution
size: small
tldr: How the active quality tier is resolved (per-agent override, then workspace overlay, then root) and announced; the master ceremony table stays in CLAUDE.md.
load_when: quality tier resolution, tier override, per-agent tier, workspace overlay tier, tier announcement, ai-playbook status tier, monorepo tier
audience: all
canonical_for: tier resolution order, per-agent tier override, workspace tier overlay, tier announcement wording
cross_refs: CHEATSHEET.md
verified: 2026-07-17
---

# Quality Tier Resolution

The master ceremony table and the root `quality-tier:` switch live in `CLAUDE.md` § Quality Tier. This file holds the resolution order, override mechanics, and announcement wording that were factored out to keep `CLAUDE.md` lean.

## Agent Use

- **Read first:** Resolution order, Tier announcement.
- **Load deeper only on trigger:** Per-agent override and Workspace overlay, only when configuring `.ai-playbook.toml` or a monorepo overlay.

---

## What Each Tier Is For

Prototype = learning spikes, throwaway experiments, early shaping. Production = durable code that will be deployed, maintained, or reviewed.

## Resolution order

Resolve the active tier in this order (first match wins):

1. Per-agent override in `.ai-playbook.toml` under `[quality_tiers.agents]`, keyed by the active agent id.
2. Workspace overlay `knowledge-base/workspaces/<workspace>/quality-tier.md`, when the loaded story declares `workspace: <path>`.
3. Root `quality-tier:` line in `CLAUDE.md` § Quality Tier.

The tier table binds behaviour; resolution just decides which column applies.

## Tier announcement

Recommended, not required. When clarity matters (long sessions, a tier change, or a user request), state the active tier in one line so behaviour is unambiguous:

- `Tier: production (preview-and-approve gates ON, full TDD, complete DoD).`
- `Tier: prototype (gates skipped, save-and-summarize, lean artifacts).`

This avoids the prototype-mode surprise where users expect approval gates that do not fire.

## Per-agent override

Adopter projects may set one agent to a different ceremony level without changing the whole repo:

```toml
[quality_tiers.agents]
xp-pair-programmer = "production"
docs-maintainer = "prototype"
```

Use only `production` or `prototype`. `ai-playbook status` shows the effective tier for deployed agents (it resolves the config override and repo default; the workspace overlay is story-scoped and agent-honored at runtime); `ai-playbook doctor` warns if an override names an unknown agent.

## Workspace overlay (monorepos)

When a story declares `workspace: <path>` in frontmatter, step 2 of the resolution order applies via `knowledge-base/workspaces/<path>/quality-tier.md`. Overlay layout, file format, story wiring, and deliberate non-features: `knowledge-base/workspaces/README.md`.
