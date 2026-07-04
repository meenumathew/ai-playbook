# Deprecation Policy

The compatibility promise from [`GOVERNANCE.md`](../GOVERNANCE.md) lives here in machine- and human-readable form. This document is what adopters can rely on when pinning a version and planning upgrades.

---

## Versioning

The playbook follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`).

| Bump | Trigger |
|---|---|
| **PATCH** | Bug fixes, doc fixes, KB prose revisions, internal refactors |
| **MINOR** | New agents, new CLI commands or flags, new KB files, new language support, new config keys (additive) |
| **MAJOR** | Removal or repurposing of any covered surface (see below), required-config-key additions, agent-ID renames |

Pre-1.0 versions (`0.x.y`) treat MINOR as the breaking-change axis. From `1.0.0` onward, the surfaces below are protected by the policy.

---

## Covered Surfaces

These surfaces are part of the public contract. Changes follow the deprecation cycle in the next section.

### 1. CLI

`ai-playbook <command>` subcommands, flags, positional arguments, and exit codes are covered.

| Change | Treatment |
|---|---|
| Add a new subcommand or flag | MINOR, additive |
| Add a new required flag to an existing subcommand | MAJOR |
| Remove a subcommand or flag | MAJOR, after deprecation cycle |
| Rename a subcommand or flag | MAJOR, after deprecation cycle (old name kept as alias during the cycle) |
| Change exit code semantics | MAJOR |
| Reorder positional arguments | MAJOR |

### 2. Agent IDs and Slash-Command Names

Agent IDs (frontmatter `id:` in `agents/<name>.agent.md`) and matching slash-command filenames in `commands/` are covered. Adopter packs, scripts, and CI pipelines reference these by name.

| Change | Treatment |
|---|---|
| Add a new agent | MINOR |
| Rename an agent ID | MAJOR, after deprecation cycle (old ID kept as a forwarding shim during the cycle) |
| Remove an agent | MAJOR, after deprecation cycle |
| Change an agent's tool policy in a way that revokes a previously allowed tool | MAJOR |

### 3. Configuration Schema

`.ai-playbook.toml` keys, `.playbook-version` fields, and the seeded knowledge-base templates are covered.

| Change | Treatment |
|---|---|
| Add an optional config key | MINOR |
| Add a required config key | MAJOR |
| Remove or repurpose a config key | MAJOR, after deprecation cycle |
| Tighten validation on an existing key (rejecting input that previously parsed) | MAJOR |
| Loosen validation on an existing key | MINOR |

### 4. Knowledge-Base File Paths

Paths referenced from agent files (e.g. `knowledge-base/security.md`, `knowledge-base/languages/<lang>.md`) are covered. Adopter packs, deployment overlays, and CI link checkers depend on these.

| Change | Treatment |
|---|---|
| Add a new KB file | MINOR |
| Rename a KB file | MAJOR, after deprecation cycle (old path kept as a stub redirect during the cycle) |
| Move content between KB files without renaming the files | MINOR (file paths preserved) |
| Remove a KB file | MAJOR, after deprecation cycle |

### 5. Deployment Layout

The on-disk structure of `ai-playbook deploy` output (e.g. `.claude/agents/`, `.github/agents/`, `.kiro/agents/`) is covered. Adopters write CI checks against these paths.

| Change | Treatment |
|---|---|
| Add a new tool target | MINOR |
| Rename a deployed file | MAJOR, after deprecation cycle |
| Remove a deployed file | MAJOR, after deprecation cycle |

---

## Not Covered

These surfaces can change at any version without a deprecation cycle. If you depend on them, vendor them into a pack or pin a specific version.

| Surface | Rationale |
|---|---|
| **Knowledge-base prose** (the contents of KB files, not their paths) | Editorial improvements happen continuously; paths are the contract, not wording |
| **Agent prose** (the body of `agents/<name>.agent.md`) | Same as KB prose; the agent's `id`, frontmatter contract, and tool policy are covered, the prose is not |
| **Internal Python API** (`src/deploy_ai_playbook/*` excluding CLI entry points) | Importing from outside the playbook is unsupported |
| **Test fixtures and eval rubrics** | Internal quality tooling, not adopter-facing |
| **Default values** that are not load-bearing (cosmetic ordering, log message wording, doctor warning text) | These improve over time; rely on the validated parse, not the formatted output |
| **The set of files included in `ai-playbook deploy`** when you pass `--no-X` flags | The flags are covered; the file lists they exclude are implementation detail |

---

## Deprecation Cycle

Any breaking change to a covered surface must go through this cycle. The cycle protects adopters who pin a version: they get at least one minor release of warning before a dependency upgrade breaks them.

```text
v1.4.0   v1.5.0 (deprecated)         v2.0.0 (removed)
   |          |                            |
   |          |---- deprecation window ----|
   |          minimum 90 days
   |          minimum 1 minor release
   |          warning surface live
```

| Stage | Required | Duration |
|---|---|---|
| **1. Land replacement** | New surface ships and works | Any release |
| **2. Mark deprecated** | Old surface still works, emits a warning when used, listed in `CHANGELOG.md` § Deprecated, ADR recorded only when the decision meets the ADR criteria | Min. 1 MINOR release **and** ≥ 90 calendar days |
| **3. Remove** | Old surface returns an error explaining the replacement | MAJOR release |

**Warning surface.** Deprecation warnings appear in three places, in order of urgency:

1. The CLI itself: using a deprecated flag, command, or config key prints a `DeprecationWarning`-style stderr line that names the replacement and target removal version.
2. `ai-playbook doctor`: surfaces deprecated agent IDs in deployed projects, deprecated config keys, and deprecated KB paths still referenced from packs.
3. `CHANGELOG.md` § Deprecated: every release lists active deprecations with their target removal version.

**Tracking active deprecations.** Every active cycle gets a row in [`.deprecations.toml`](../.deprecations.toml) at the repo root. The registry is the single source of truth: the `### Deprecated` section of `CHANGELOG.md` and the registry must agree, and `tests/acceptance/test_deprecations.py` enforces that. When a release removes a surface (its `removal_version` ships), delete the row; git history is the audit trail.

**Skipping the cycle.** A deprecation cycle can be skipped only when:

- A security advisory requires it (see [`SECURITY.md`](../SECURITY.md)).
- The surface was added in the most recent MINOR release and never reached a `1.x.0` release boundary (i.e. removing something that no pinned version exposes).
- An ADR justifies the skip and links to this document.

In practice, expect cycles to be honored. The exceptions are exceptional.

---

## Adopter Responsibilities

The promise above is two-sided. Adopters are expected to:

| Expectation | Why |
|---|---|
| Pin a specific version (`ai-playbook==1.4.2`, not `ai-playbook>=1`) | Without a pin, a transitive upgrade can pull in a MAJOR release |
| Read `CHANGELOG.md` § Deprecated before upgrading across a MINOR boundary | The warning is published; reading it is the adopter's job |
| Run `ai-playbook doctor` after every upgrade | Catches deprecated paths still referenced from local packs and customizations |
| Vendor KB prose into a pack if specific wording matters | KB prose is not covered; if your CI greps for a specific phrase, that grep can break on PATCH |
| Keep packs in version control with a tested upgrade workflow | Packs override core; they do not get free deprecation handling for content adopters added themselves |

Teams who do not pin and do not read `CHANGELOG.md` are on a best-effort path. The policy still applies; the warnings still fire; but the support boundary on surprise breakage is "we told you in the changelog."

---

## Examples

**Renaming an agent (covered, deprecation cycle required):**

1. v1.5.0: ship a new `release-engineer` agent alongside the existing `release-captain`. Both work. Calling `release-captain` prints a deprecation warning naming `release-engineer`. Record an ADR only if the rename reflects a durable policy or scope change.
2. v1.6.0 (≥ 90 days later): both still work; warning still fires; `CHANGELOG.md` § Deprecated still lists it.
3. v2.0.0: `release-captain` removed. Calling it returns a clear error pointing to `release-engineer`.

**Adding a new optional config key (additive, no cycle):**

1. v1.7.0: add `[upgrade].notify_on_drift` to `.ai-playbook.toml`. Default preserves prior behavior. Documented in `docs/cli-reference.md`. PATCH could not have shipped this; it requires a MINOR.

**Revising prose in `knowledge-base/testing.md` (not covered, no cycle):**

1. Any release: prose updated, file path unchanged. No deprecation. Adopters who depend on specific wording vendor the file into a pack.

**Tightening validation on `[notifier].provider` (covered, MAJOR):**

1. Old behavior: any string accepted, unknown providers became no-ops.
2. New behavior: only enumerated values accepted, unknown providers raise.
3. Treatment: MAJOR after one-MINOR deprecation cycle. The MINOR ships the new validator behind a config flag; the MAJOR makes it the default.

---

## Cross-References

- [`GOVERNANCE.md`](../GOVERNANCE.md): who decides what counts as breaking
- [`docs/adr/README.md`](adr/README.md): how decisions are recorded
- [`docs/rfcs/README.md`](rfcs/README.md): how proposals are evaluated
- [`SECURITY.md`](../SECURITY.md): what overrides this policy
- [`CHANGELOG.md`](../CHANGELOG.md): where deprecations are announced
