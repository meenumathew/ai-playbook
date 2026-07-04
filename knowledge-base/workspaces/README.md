---
id: workspaces
size: small
tldr: "Per-package KB overlays for monorepos: quality tier, language conventions, and other per-package knowledge; the repo root stays the source of truth."
load_when: A story declares `workspace:` frontmatter, or the user mentions a monorepo subpath, or an agent is asked to apply per-workspace settings.
audience: all
canonical_for: "Per-workspace KB overlays: quality tier, language conventions, and other per-package knowledge in a monorepo."
cross_refs:
  - CLAUDE.md § Quality Tier
  - knowledge-base/INDEX.md
  - templates/story-template.md
verified: 2026-06-08
---

# Workspaces

Per-package overlays for monorepos. The repo root is still the source of truth: workspaces only override what they need to.

## When to use

Use a workspace when one repo holds multiple packages with **materially different operating conditions**:

| Signal | Example |
|---|---|
| Different quality tiers | `apps/api` ships to prod (production tier); `apps/playground` is a learning sandbox (prototype) |
| Different language stacks | `apps/web` is TypeScript; `services/billing` is Python |
| Different compliance scope | `services/payments` is PCI; the rest of the repo is not |
| Different release cadence | A library publishes weekly; a customer-facing app ships nightly |

If every package operates the same way, **skip workspaces**: the repo root settings already cover you.

## Layout

```text
knowledge-base/
├── quality-gates.md              # repo default (always applies unless overridden)
├── languages/
│   └── python.md                 # repo default conventions
└── workspaces/
    ├── README.md                 # this file
    └── apps/
        └── api/
            ├── quality-tier.md   # overrides repo tier for this workspace
            └── languages/
                └── python.md     # overrides repo Python conventions for apps/api
```

The path under `workspaces/` mirrors the actual workspace path in the repo (`apps/api/`, `services/billing/`, `packages/lib-x/`).

## Precedence

Most specific wins:

1. **Workspace overlay**: `knowledge-base/workspaces/<workspace>/<file>`
2. **Repo root**: `knowledge-base/<file>`
3. **Template**: `templates/<file>` (only used to seed a missing root file)

A workspace overlay is a *partial*: it only needs to declare the rules it changes. Anything not redeclared falls through to the repo root.

## Wiring it into a story

Set `workspace:` in story frontmatter:

```yaml
---
issue-ref: PROJ-1234
type: story
status: refining
workspace: apps/api
---
```

When an agent loads the story, it resolves the workspace path and layers the overlay on top of the repo defaults. Empty `workspace:` (or no field) = repo default; no overlay applied.

## Quality tier override

A workspace's `quality-tier.md` contains a single fenced block:

```markdown
quality-tier: prototype (gates skipped, save-and-summarize, lean artifacts).
```

Agents use this for stories declared in that workspace when no per-agent override exists in `.ai-playbook.toml` `[quality_tiers.agents]`. The session-start tier announcement reflects the resolved tier.

## What workspaces do *not* do today

- **No deploy-time selection.** `ai-playbook deploy` writes to the repo root regardless. Adopters who want per-workspace deploy targets should open a story.
- **No automatic doctor checks.** Doctor validates the root config, not workspace overlays.
- **No directory enforcement.** A story can declare `workspace: apps/api` even if no overlay exists for it: agents just fall through to repo defaults. Lint-style enforcement is out of scope until usage shows it's needed.

These boundaries are deliberate: workspace overlays are a *knowledge* feature first. Tooling-level workspace support is a separate decision (a future ADR if/when adopters ask).
