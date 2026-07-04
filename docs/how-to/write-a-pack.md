# How to write a pack

Goal: ship project-specific agents, skills, KB pages, or templates *without forking the playbook*. A **pack** is a directory under your repo whose files layer over the core playbook on every `ai-playbook deploy`.

## Prerequisites

- The playbook is deployed (`ai-playbook deploy --tool <tool>` worked at least once).
- You can write to your repo root.
- You've identified content that genuinely belongs in your project, not in the upstream playbook. Examples:
  - A `django-pack` that adds Django-specific KB pages and an agent that knows your auth middleware.
  - A `mobile-pack` that overrides the default `release.md` with iOS/Android-specific gates.
  - A team-wide pack that adds your domain glossary to `knowledge-base/domain-language.md`.

If you want to upstream the content (it's general-purpose, not project-specific), open an RFC instead: see [`docs/rfcs/README.md`](../rfcs/README.md).

## Steps

### 1. Decide the pack name and location

A pack lives anywhere inside your repo. The convention is `.ai-playbook/packs/<pack-name>/` so multiple packs share a parent directory:

```text
your-repo/
├── .ai-playbook/
│   └── packs/
│       └── django/
│           ├── agents/                   # any *.agent.md
│           ├── knowledge-base/           # any *.md (overrides core if filename collides)
│           ├── skills/                   # SKILL.md per skill subdir
│           ├── templates/                # any *.md
│           └── pack.toml                 # optional metadata
└── .ai-playbook.toml                     # registers the pack with the CLI
```

Rule of thumb: pack names are kebab-case, descriptive, and stable. The name appears in `doctor` output and override warnings. Names must be unique across the `packs = [...]` list: deploy fails on a duplicate `name` (the directory name when no `pack.toml` declares one).

Packs can ship `agents/`, `knowledge-base/`, `skills/`, and `templates/` content. The `commands/` directory (slash-command shims) is core-only: packs cannot ship custom shim content: but deploy auto-generates a standard shim for every pack agent, so `/your-agent` works out of the box. Need bespoke shim prose? Propose it upstream via RFC.

### 2. Author at least one file

Pack content uses the same shape as core content. The simplest pack is a single agent or KB file.

For an agent, copy [`templates/agent-template.md`](../../templates/agent-template.md) and fill in the frontmatter contract (every field is required). Save as `<pack>/agents/<id>.agent.md`. The CLI discovers agents by the `.agent.md` suffix, so the filename's stem is the agent id.

For a KB page, write a normal markdown file with the 8-key frontmatter that core KB files use (`id`, `size`, `tldr`, `load_when`, `audience`, `canonical_for`, `cross_refs`, `verified`). Adopters routing keywords through `load_when` will land on your page when the keyword matches.

Both contracts are checked mechanically: `ai-playbook config validate` fails (exit 1) on a pack agent or KB file with missing/empty required frontmatter, and `ai-playbook doctor` reports the same finding as a warning: so a typo'd `load_when:` surfaces before it silently breaks routing.

For a skill, create `<pack>/skills/<skill-name>/SKILL.md` and follow the structure in `skills/host-adapter/SKILL.md` (an `## Operations` section is the contract).

### 3. Override core content (optional)

Pack files override core files when their *relative path* matches. Concrete example: if your pack ships `agents/release-captain.agent.md`, your version replaces the core `release-captain` everywhere: `ai-playbook deploy` writes the pack version, and `ai-playbook doctor` prints an `override` warning so the change is visible.

Override sparingly. Each override is a divergence point that needs a reason. Two healthy patterns:

- **Add fields, not replace prose.** Inherit from core wording and append your domain-specific notes in a new section.
- **Use a separate id when the change is large.** Instead of overriding `release-captain`, create `mobile-release-captain` so adopters can opt in.

For team and org adoption, make overrides reviewable: add `ai-playbook doctor --strict --tool <tool>` to CI. Overrides surface as doctor warnings and `--strict` exits 1 on warnings, so a new override fails the pipeline until reviewed: the difference between a visible divergence and an approved one. This matters most when a pack overrides a gate-bearing agent (release-captain, incident-responder).

### 4. Add pack metadata (recommended)

Create `<pack>/pack.toml`:

```toml
name = "django"
version = "1.0.0"
min_playbook_version = "1.0.0"
```

`min_playbook_version` makes deploy fail fast if your pack relies on a feature that the adopter's CLI is too old to provide; `max_playbook_version` (optional, rare) caps the other end. Without metadata, the CLI assumes the pack works on any playbook version and uses the directory name as the pack name.

### 5. Register the pack

Edit your repo's `.ai-playbook.toml`:

```toml
packs = [".ai-playbook/packs/django"]
```

Multiple packs are listed in array order, and **last pack wins** on relative-path collisions. With `packs = ["packs/base", "packs/django"]`, a `knowledge-base/release.md` in both packs deploys the `django` copy; `django` also beats core for any path both define. Deploy prints a `Pack overrides:` line for every collision so the winner is visible. Pack paths must stay inside the project root (the CLI rejects `../` escapes for safety).

Removing a pack from the list leaves its deployed files behind as orphans; the next `ai-playbook deploy --prune` lists them with a `packs no longer in .ai-playbook.toml` warning before asking to delete.

### 6. Deploy and verify

```bash
ai-playbook deploy --tool claude
```

Expected output:

- A `Pack overrides:` section listing every file the pack replaces, if any.
- The pack files copied alongside core files into `.claude/` (or your tool's destination).

Run `ai-playbook doctor --tool claude` and confirm pack files are recognized: they should appear with their `pack:<name>` origin in any drift warnings.

Run `ai-playbook diff --tool claude --json` to inspect what changed; the `sections[].changes[].file` list will include pack-origin paths.

### 7. Test the pack in CI

Treat the pack as adopter-side code. Recommended additions to your CI:

- `ai-playbook upgrade-check --tool <tool>`: non-zero exit when the pack fingerprint drifts from what's deployed.
- `ai-playbook doctor --tool <tool> --strict`: non-zero exit on issues.

Pack content is text; standard markdown lint and link checking apply.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `pack <name> requires ai-playbook >= X.Y.Z (current A.B.C)` | The CLI on PATH is older than the pack's `min_playbook_version` | `uv tool upgrade ai-playbook` |
| `Pack path must stay inside the project root` | `.ai-playbook.toml` has a `packs = [...]` entry that escapes the repo | Use a path relative to the repo root, no `../` |
| Pack files appear in `doctor` as orphaned after a rename | The old filename is still deployed | Run `ai-playbook deploy --prune --tool <tool> --yes` |
| `Pack overrides:` warning fires every deploy and you don't expect it | Two packs override the same path; the later one wins | Re-order the `packs = [...]` array, or move the override into a single pack |
| Pack agent doesn't show up in `ai-playbook list` | The file isn't named `<id>.agent.md` or doesn't have valid frontmatter | Re-check filename suffix and frontmatter against [`templates/agent-template.md`](../../templates/agent-template.md) |
| `Duplicate pack name: <name>` on deploy | Two packs resolve to the same name (declared or directory-derived) | Rename one pack or set a distinct `name` in its `pack.toml` |
| Pack agent's slash command has generic wording | Deploy auto-generates a standard shim; packs cannot ship custom shim content | Use the generated shim (it forwards arguments correctly), or propose custom shim support via RFC |

## Related

- [CLI Reference § Packs](../cli-reference.md#packs): full pack spec, override-precedence rules, and operational guarantees.
- [`templates/agent-template.md`](../../templates/agent-template.md): required agent frontmatter contract.
- [`docs/how-to/setup-multi-repo.md`](setup-multi-repo.md): sharing a pack across repos.
- [`knowledge-base/workspaces/README.md`](../../knowledge-base/workspaces/README.md): workspace overlays inside a monorepo (a related but distinct mechanism).
