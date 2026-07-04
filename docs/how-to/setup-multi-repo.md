# How To Set Up Multi-Repo Teams

## Goal

Share domain vocabulary across multiple repositories for the same business while keeping per-repo constraints independent.

## Prerequisites

- AI Playbook deployed in each target repository.
- A canonical source for the shared vocabulary (a shared repo, an internal wiki, or a private package).

## Steps

### 1. Decide What Is Shared

| File | Shared? | Reason |
|---|---|---|
| `knowledge-base/domain-language.md` | Yes | Same business vocabulary across all repos |
| `knowledge-base/quality-gates.md` | No | Different test commands per repo |
| `docs/limitations.md` | No | Different constraints per repo |
| `docs/adr/` | No | Different technology choices per repo |

### 2. Establish a Canonical Domain Language

Author the shared `domain-language.md` in one authoritative location:

- A shared internal repo (for example `team-standards`).
- A private npm or PyPI package that ships the markdown.
- An internal wiki page with export support.

### 3. Sync to Each Repo

The recommended sync mechanism is **adopter-local packs**: see [CLI Reference § Packs](../cli-reference.md#packs). Other options trade off versioning, automation, and drift.

| Mechanism | Pros | Cons |
|---|---|---|
| **Pack (recommended)** | Playbook-native; `uv tool upgrade ai-playbook` (or `pip install -U`) propagates core; pack content survives prune and doctor | Adopter authors `.ai-playbook.toml` once per repo |
| Private package | Versioned, CI-friendly | Build step required |
| `git subtree` | Self-contained history | Manual sync |
| `git submodule` | Always current | Requires submodule-update discipline |
| CI Action or bootstrap script | Automated PR on change | Requires CI setup |
| Manual copy | Simple | Drifts silently |

The playbook does not prescribe one: agents only require that `knowledge-base/domain-language.md` exists and is current.

### 4. Configure a Shared Pack

When multiple repos share the same domain language with per-repo overrides:

1. Publish the shared content as a private package, or vendor a `git subtree` into each repo, at a known path: for example `.ai-playbook/packs/shared/`.
2. In each adopter repo, add `.ai-playbook.toml`:

   ```toml
   packs = [".ai-playbook/packs/shared", ".ai-playbook/packs/<this-repo>"]
   ```

   Shared content lands first; per-repo overrides win on collision (last-pack-wins).

3. Run `ai-playbook deploy`. It merges core, shared, and per-repo files. Override warnings show exactly which file came from which layer.

### 5. Verify Consistency

After syncing, spot-check that agents in each repo use consistent terminology:

```text
Use code-inspector: audit domain language usage in src/
```

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent uses a different term in repo B | `domain-language.md` not synced | Pull the latest from the canonical source |
| Merge conflicts in domain language | Two repos edited independently | Edit only in the canonical source, then sync outward |
| Agent ignores the domain language | File missing or path wrong | Verify `knowledge-base/domain-language.md` exists |

## Related

- [User Guide § Before You Start](../user-guide.md#2-before-you-start): project-specific files to configure
- [CLI Reference § Knowledge Base Files](../cli-reference.md#knowledge-base-files): what gets deployed
