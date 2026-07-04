# CLI Reference

Full reference for the `ai-playbook` command.

The CLI deploys packaged playbook assets (agents, skills, KB, templates, rules, and harness files). Vendor-neutral skills such as `host-adapter`, `issue-fetch`, and `notifier` are markdown operation contracts for agents/adopters; they are not Python runtime services inside the CLI.

---

## Installation

```bash
# From PyPI
uv tool install ai-playbook
# or:  pipx install ai-playbook
# or:  pip install ai-playbook

# From source
uv tool install --editable /path/to/ai-playbook

# Force reinstall after an update
uv tool install --force --editable /path/to/ai-playbook

# Verify
ai-playbook list
```

---

## Commands

### Deploy agents

```bash
ai-playbook deploy [--agent <names>] [--tool <tool>] [--target-dir <path>] [--language <lang>] \
                   [--dry-run] [--no-rules] [--no-mcp] [--no-harness] [--harness-force] \
                   [--prune] [--yes]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--agent`, `-a` | `all` | `all` or comma-separated names, for example `story-refiner,xp-pair-programmer` |
| `--tool`, `-T` | `claude` | `claude`, `copilot`, `cursor`, or `kiro` |
| `--target-dir`, `-t` | current directory | Override the target project directory |
| `--language`, `-l` | all | Deploy only active KB files for a maintained language. Currently: `python`. For other languages, the adopting team seeds files from the blank templates. |
| `--dry-run` | off | Preview what the command would deploy without writing anything |
| `--no-rules` | off | Skip deploying the rules file (CLAUDE.md / copilot-instructions.md / ai-playbook.mdc / rules.md) |
| `--no-mcp` | off | Skip deploying MCP server configuration entirely. Without this flag, the Atlassian MCP is deployed only when `.ai-playbook.toml` sets `[issue-tracker] provider = "jira"`; other providers (or none) already skip MCP setup |
| `--no-harness` | off | Skip deploying starter harness files (`Makefile`, `.pre-commit-config.yaml`, CI workflow, teach-back hook, telemetry hook example) and the Claude telemetry Stop-hook merge. Existing files are kept: this flag suppresses the initial copy only. |
| `--harness-force` | off | Overwrite existing harness files with the upstream copy. Default keeps adopter edits in place; opt in when an upstream fix needs to land. |
| `--prune` | off | After deploy, remove orphaned files in deployed dirs that have no source counterpart, for example files left over from a renamed or removed agent. **Preserves `*.disabled` files** (user-managed state). **Confirms before deleting** unless `--yes` or `--dry-run` is also passed. |
| `--yes`, `-y` | off | Skip the prune confirmation prompt. No effect without `--prune`. |

**Examples:**

```bash
# Deploy everything to Claude
ai-playbook deploy --agent all --tool claude

# Preview without writing
ai-playbook deploy --agent all --tool claude --dry-run

# Deploy specific agents only
ai-playbook deploy --agent story-refiner,xp-pair-programmer --tool claude

# Deploy to a different project directory
ai-playbook deploy --agent all --tool claude --target-dir /path/to/project

# Deploy to Copilot, Cursor, or Kiro
ai-playbook deploy --agent all --tool copilot
ai-playbook deploy --agent all --tool cursor
ai-playbook deploy --agent all --tool kiro

# Skip the rules file (preserves a customised CLAUDE.md)
ai-playbook deploy --agent all --tool claude --no-rules

# Deploy only Python knowledge-base files
ai-playbook deploy --agent all --tool claude --language python

# Remove files left over from renamed or removed agents
ai-playbook deploy --agent all --tool claude --prune --dry-run   # preview
ai-playbook deploy --agent all --tool claude --prune              # apply (prompts before delete)
ai-playbook deploy --agent all --tool claude --prune --yes        # apply in CI / scripts

# Pull fresh harness files (telemetry.sh, CI workflow) over local edits
ai-playbook deploy --agent all --tool claude --harness-force
```

`--prune` removes deployed files that no longer have a source counterpart. It preserves `*.disabled` files. To remove `*.disabled` files, delete them by hand before running `--prune`. Interactive runs prompt before deleting; pass `--yes` in CI. When pruning would delete files originating from a pack you have just removed from `.ai-playbook.toml`, the prompt surfaces the pack name so an accidental config edit doesn't quietly purge agents.

**What gets deployed:**

| | Claude | Copilot | Cursor | Kiro |
|--|--------|---------|--------|------|
| Agents | `.claude/agents/` | `.github/agents/` | `.cursor/agents/` | `.kiro/agents/` |
| Knowledge Base | `.claude/knowledge-base/` | `.github/knowledge-base/` | `.cursor/knowledge-base/` | `.kiro/knowledge-base/` |
| Skills | `.claude/skills/` | `.github/skills/` | `.cursor/skills/` | `.kiro/skills/` |
| Templates | `.claude/templates/` | `.github/templates/` | `.cursor/templates/` | `.kiro/templates/` |
| Commands | `.claude/commands/` | `.github/prompts/` | `.cursor/commands/` |: |
| Rules | `CLAUDE.md` | `.github/copilot-instructions.md` | `.cursor/rules/ai-playbook.mdc` | `.kiro/steering/rules.md` |
| MCP (work item / tracker fetch) | `.claude/settings.json` | `.vscode/mcp.json` | `.cursor/mcp.json` | `.kiro/settings/mcp.json` |
| Harness | `Makefile` + `.pre-commit-config.yaml` + `.github/workflows/ci.yml` + `.github/workflows/security.yml` + `harness/check-teachback.sh` + `harness/telemetry.sh` + `harness/settings.example.json` | ← same | ← same | ← same |

For Claude deploys, the harness step also merges a `hooks.Stop` command into `.claude/settings.json` so completed sessions append telemetry to `.claude/usage.jsonl`. The deploy command preserves existing settings and copies malformed JSON aside instead of overwriting it.

Deployed content is rewritten per tool: `knowledge-base/`, `skills/`, and `templates/` references take the tool's path prefix, and `CLAUDE.md` citations become the tool's rules file (`.github/copilot-instructions.md` for Copilot, `.cursor/rules/ai-playbook.mdc` for Cursor, `.kiro/steering/rules.md` for Kiro). `diff` and `doctor` apply the same rewrite, so rewritten references never report as drift.

For Claude deploys, agent frontmatter is also materialized from `[model_tiers]`: `model: advisor`/`model: executor` becomes the configured model (`model: opus`/`model: sonnet`/`model: haiku`) so Claude Code routes each agent to the right model natively. Only values Claude Code recognizes (`opus`/`sonnet`/`haiku`/`inherit` or a `claude-*` model ID) are rewritten; other values (e.g. `ollama:qwen3:32b`) keep the tier name and deploy prints a note. Source `agents/` files always keep tier names, and `diff`/`doctor` apply the same rewrite so a clean deploy never reports drift. Copilot, Cursor, and Kiro have no per-agent model field and are never rewritten. Tier contract: [Model Tier](../knowledge-base/model-tier.md).

Deploy is **idempotent**: running it again on an unchanged playbook shows `unchanged` for every file.

---

### Scaffold a project

```bash
ai-playbook init [--target-dir <path>]
```

Creates the six artifact directories (`stories/`, `research/`, `plans/`, `audits/`, `reviews/`, `incidents/`, each with a `.gitkeep`) and a commented starter `.ai-playbook.toml`. Idempotent: existing directories and config are kept, never overwritten. Run it once before the first deploy; it replaces the manual `mkdir` step.

---

### List available agents

```bash
ai-playbook list [--target-dir <path>] [--json]
```

Lists all agents available from the playbook core and any packs configured in `.ai-playbook.toml`. The Origin column shows the winning source (`core` or `pack:<name>`), so pack overrides of bundled agents are visible. If you omit `--target-dir` or no `.ai-playbook.toml` exists, the list shows only core agents. `--json` emits the same inventory as `{"agents": [{"name", "file", "origin"}]}` for CI scripts and editor integrations (STORY-001).

---

### Check deployment status

```bash
ai-playbook status [--tool <tool>] [--target-dir <path>] [--json]
```

Lists agents currently deployed in the target directory, marks each as active or off, and shows the resolved quality tier. The status output labels per-agent overrides as `override`.

Use `--json` in scripts to read `deployed`, `tool`, and the agent list without parsing Rich tables.

---

### List Resumability Artifacts

```bash
ai-playbook artifacts [--target-dir <path>] [--query <text>] [--json]
```

Lists story, research, plan, audit, review, and incident artifacts in the target project. Use `--query` to search by path or file contents when you do not remember the exact story or plan filename.

Use `--json` for automation; it returns `count` and an `artifacts` array with `type`, `path`, and `status`.

---

### Set Artifact Tracking Policy

```bash
ai-playbook artifact-policy local [--target-dir <path>] [--dry-run]
ai-playbook artifact-policy shared [--target-dir <path>] [--dry-run]
ai-playbook artifact-policy status [--target-dir <path>]
```

Manages a marked `.gitignore` block for generated playbook artifacts. Use `local` when story, plan, research, audit, review, and incident files should stay out of Git. Use `shared` when you want to commit or govern those artifacts manually; the command removes only the playbook-managed block and preserves the rest of `.gitignore`.

---

### Show what changed

```bash
ai-playbook diff [--tool <tool>] [--target-dir <path>] [--exit-code]
```

Compares the playbook source against the deployed copy in the target project. Lists files that changed or are not yet deployed; if it finds no differences, prints a single up-to-date message.

By default, `diff` always exits 0 and is informational. Pass `--exit-code` in CI to fail with exit 1 when drift is detected: useful for gating merges on the deployment staying in sync with `.playbook-version`.

```bash
ai-playbook diff --tool claude
ai-playbook diff --tool claude --exit-code   # CI gate
ai-playbook deploy --agent all --tool claude
```

---

### Disable agents

```bash
ai-playbook disable <agent> [--tool <tool>] [--target-dir <path>] [--dry-run]
```

Renames the agent file to `agent-name.agent.md.disabled`. The AI tool ignores files with that suffix; the command deletes nothing. `--dry-run` previews the rename without touching files.

```bash
ai-playbook disable xp-pair-programmer --tool claude
ai-playbook disable xp-pair-programmer,slice-planner --tool claude
ai-playbook disable all --tool claude
```

---

### Check deployment health

```bash
ai-playbook doctor [--tool <tool>] [--target-dir <path>] [--json] [--strict]
```

Reports stale files, missing agents, agents turned off, and missing runtime directories in one pass.

```bash
ai-playbook doctor --tool claude
ai-playbook doctor --tool claude --target-dir /path/to/project
ai-playbook doctor --tool claude --strict       # CI: exit 1 on issues, 2 on not-deployed
```

Output categories:

- **Issues** (red): missing agents, missing rules file: deployment has a critical problem.
- **Warnings** (yellow): stale files, agents turned off, missing runtime directories: deployment functions but content has drifted.

Use `--json` in CI or scheduled health checks. The JSON payload contains `healthy`, `status`, `issues`, and `warnings`.

**Exit codes** (default: preserves the legacy contract):

- `0`: healthy, or deployed-with-warnings, or deployed-with-issues.
- `1`: nothing deployed for this tool.

**Exit codes (`--strict`)**: opt-in 3-state contract for CI:

- `0`: healthy, no issues or warnings.
- `1`: deployed but issues or warnings exist.
- `2`: nothing deployed for this tool.

---

### Rollback deployment

```bash
ai-playbook rollback [--tool <tool>] [--target-dir <path>] [--force] [--dry-run]
```

Restores the previous backed-up overlay deployment for the selected tool. Backups are tool-scoped: a Copilot backup is never used for `--tool claude`, and vice versa.

Use `--force`, `-f` to skip the interactive confirmation prompt. Use `--dry-run` to see which backup would be restored without restoring anything.

Rollback covers the managed overlay files that deploy backs up before each write: agents, knowledge base, skills, templates, commands, rules, and `.playbook-version`. It does not restore MCP settings or starter harness files; rerun `ai-playbook deploy` or the relevant `telemetry` command to repair those files.

**Packs and rollback:** rollback restores the deployment snapshot from before the last deploy, but leaves `.ai-playbook.toml` and your pack directories untouched. If the restored snapshot pre-dates a pack addition or removal, `doctor` reports stale or orphaned files until you run `ai-playbook deploy` again to re-sync.

```bash
ai-playbook rollback --tool claude
ai-playbook doctor --tool claude
```

---

### Enable agents

```bash
ai-playbook enable <agent> [--tool <tool>] [--target-dir <path>] [--dry-run]
```

Restores an agent from off to active. `--dry-run` previews the rename without touching files.

```bash
ai-playbook enable xp-pair-programmer --tool claude
ai-playbook enable all --tool claude
```

---

### Check for playbook drift

```bash
ai-playbook upgrade-check [--tool <tool>] [--target-dir <path>] [--json]
```

Compares the deployed playbook fingerprint (recorded in `.playbook-version`) against the current source. Designed for CI: a non-zero exit code means the deployment needs attention before merging.

| Exit | Meaning |
|---|---|
| `0` | Up to date: deployed fingerprint matches source |
| `1` | Drift or tool mismatch detected: redeploy, or run with the tool recorded in `.playbook-version` |
| `2` | Never deployed in this project (no `.playbook-version`) |

Output also surfaces:

- The current `ai-playbook` package version.
- The last deploy timestamp, tool, and language filter (when recorded).
- Deployed and source fingerprints side-by-side.
- A tool-mismatch failure when `--tool` differs from the tool recorded in `.playbook-version`.

Use `--json` when wiring this into CI. The exit-code contract is unchanged; the payload includes `status`, fingerprints, deploy metadata, selected tool, and notes.

CI usage:

```bash
ai-playbook upgrade-check --tool claude || {
  echo "::warning::ai-playbook drift detected: redeploy before merging"
  exit 1
}
```

---

### Validate configuration

```bash
ai-playbook config validate [--target-dir <path>] [--json]
```

Validates `.ai-playbook.toml`, configured pack paths, optional `pack.toml` metadata, model tier mapping shape, and quality tier overrides. Missing `.ai-playbook.toml` is valid and means a core-only deploy. Warnings report non-fatal issues such as an override that names no discovered agent.

---

### Manage telemetry Stop hook

```bash
ai-playbook telemetry status  [--target-dir <path>]
ai-playbook telemetry enable  [--target-dir <path>]
ai-playbook telemetry disable [--target-dir <path>]
```

Manages the Claude `hooks.Stop` entry that appends per-session telemetry to `.claude/usage.jsonl`. `ai-playbook deploy --tool claude` configures the hook automatically; these subcommands are for adopters who deployed with `--no-harness`, removed the hook by hand, or want to verify the wiring.

| Subcommand | Effect |
|---|---|
| `status` | Prints the Stop hook status, where `settings.json` lives, whether `harness/telemetry.sh` is present, and the size of the usage log |
| `enable` | Idempotent: adds the AI Playbook entry to `hooks.Stop` if missing. Preserves other hooks and unrelated settings. Warns if `harness/telemetry.sh` is not deployed yet. |
| `disable` | Removes only the AI Playbook entry from `hooks.Stop`. Preserves other hooks and unrelated settings, then removes the empty `Stop` block. |

If `.claude/settings.json` contains malformed JSON, both `enable` and `disable` refuse to overwrite it and copy the broken file aside as `settings.json.broken-<timestamp>` for the adopter to repair.

---

## Agents

| Agent | File | Purpose |
|-------|------|---------|
| `story-refiner` | `story-refiner.agent.md` | Refines ideas and stories: researches the codebase, surfaces contradictions, writes verified stories |
| `slice-planner` | `slice-planner.agent.md` | Designs approach, structures vertical slices with test checkpoints, outputs a tactical plan |
| `xp-pair-programmer` | `xp-pair-programmer.agent.md` | TDD pair programmer: acceptance tests from acceptance criteria (outer loop), then unit TDD red-green-refactor (inner loop), commits after approval on green |
| `diff-reviewer` | `diff-reviewer.agent.md` | Reviews diffs and PRs against acceptance criteria and knowledge-base standards |
| `release-captain` | `release-captain.agent.md` | Owns the path from approved review to tagged release: opens PR/MR, watches CI, merges on approval, version bump + tag, post-deploy smoke |
| `incident-responder` | `incident-responder.agent.md` | Triages production incidents: builds the timeline, runs ranked hypotheses, writes the blameless postmortem (read-only on production) |
| `code-inspector` | `code-inspector.agent.md` | Audits modules or repos for architecture, security, and quality: outputs a scored report |
| `docs-maintainer` | `docs-maintainer.agent.md` | Writes and maintains onboarding guides, API docs, runbooks, and ADRs in the repo |

For workflow modes (full, minimal, spike, solo, team), see **[User Guide § The Loop](user-guide.md#3-the-loop)**.

---

## Skills

| Skill | File | Purpose |
|-------|------|---------|
| `git` | `skills/git/SKILL.md` | Conventional commits, branching, worktrees (parallel sprints), PRs, squashing, merge conflict resolution |
| `host-adapter` | `skills/host-adapter/SKILL.md` | PR/MR operations across GitHub, GitLab, Bitbucket SaaS, and Gitea/Forgejo: used by diff-reviewer and release-captain |
| `intent-interview` | `skills/intent-interview/SKILL.md` | Stable questioning pattern for ambiguous requests: five anchors, propose-then-ask, prompt minimization |
| `issue-fetch` | `skills/issue-fetch/SKILL.md` | Resolving work item references (Jira, GitHub Issues/Projects, GitLab, Bitbucket, Linear) to local story artifacts, then tracker API/MCP |
| `notifier` | `skills/notifier/SKILL.md` | Outbound notifications (Slack, email, generic webhook) for release-captain and incident-responder; default provider `none` |
| `retrospective` | `skills/retrospective/SKILL.md` | Session-end learning loop: surface friction and propose knowledge base improvements |
| `story-writing` | `skills/story-writing/SKILL.md` | Story creation conventions |

---

## Knowledge Base Files

Agents load knowledge-base files on demand based on their task and loading rules.

**Universal: any language or stack:**

| File | Covers |
|------|--------|
| `philosophy.md` | XP + DDD principles, pure domain model, creative exploration, context engineering (token efficiency), cognitive health, AI workflow anti-patterns (incl. LLM non-determinism mitigation) |
| `style-guide.md` | Naming, SOLID, KISS, YAGNI, DRY |
| `testing.md` | Short mandatory testing rules: TDD, AT standards, test quality, doubles, coverage, testability |
| `testing-techniques.md` | Optional triggered testing techniques: mutation, property-based, contract, async/event-driven, Python pytest edge cases |
| `design-patterns.md` | Hexagonal architecture, module depth + seams, DDD tactical + strategic, preferred patterns, anti-patterns, dual-message exceptions (CWE-209) |
| `security.md` | Secrets, input validation (OWASP Top 10), JWT + timing attacks, STRIDE design-phase threat modeling, PII, dependencies, API security, CWE-209 error response pattern, AI safety (prompt injection, drift, accountability), review checklist |
| `debugging.md` | Iron Law (root cause first), 4-phase loop, 9 ranked feedback-loop types, 3-Fix architectural stop rule, backward tracing, ranked falsifiable hypotheses, verification protocol, red flags |
| `observability.md` | Log levels, structured logging, correlation IDs, sensitive data masking, health checks (live / ready) |
| `performance.md` | Algorithmic complexity, data structures, N+1 queries, caching rules, review checklist, profile-first rule |
| `refactoring.md` | When/how to refactor, smells → moves (Strangler Fig, Parallel Change, Feature Envy), inline vs planned |
| `feature-flags.md` | When to use, AC pattern, lifecycle, evaluation layer, test isolation, naming |
| `working-agreement.md` | AI pairing modes, collective ownership, scaling across team sizes |

> On first use, `ai-playbook` seeds adopter-specific singletons from `templates/`. `knowledge-base/domain-language.md` and adopter `docs/limitations.md` start from templates; `knowledge-base/quality-gates.md` ships a default quality contract that each project can edit. ADRs live in the adopter's `docs/adr/`, seeded from `templates/adr-template.md`.

**Language-specific:**

| File | Covers |
|------|--------|
| `languages/python.md` | PEP 8, type hints, ruff, pyright, src/ layout: **reference implementation** |
| `languages/testing-python.md` | pytest fixtures, mocks, parametrize: **reference implementation** |
| `templates/language-conventions-template.md` | Blank template: copy to `languages/<lang>.md` to add a new language |
| `templates/testing-language-template.md` | Blank template: copy to `languages/testing-<lang>.md` to add a new language |

To add a new language: copy `templates/language-conventions-template.md` to `knowledge-base/languages/<language>.md` and `templates/testing-language-template.md` to `knowledge-base/languages/testing-<language>.md`. Use `knowledge-base/languages/python.md` as the reference implementation.

---

## Templates

| Template | Seeded as | Purpose |
|----------|-----------|---------|
| `templates/story-template.md` | `stories/STORY-NNN-slug.md` | User story artifact (story / chore) |
| `templates/story-bug-template.md` | `stories/BUG-NNN-slug.md` | Bug story: Symptom / Reproduction / Severity, regression-test-first |
| `templates/story-spike-template.md` | `stories/SPIKE-NNN-slug.md` | Spike: timeboxed exploration; deliverable is a research file, no code on main |
| `templates/plan-template.md` | `plans/PLAN-NNN-slug.md` | Implementation plan artifact |
| `templates/research-template.md` | `research/RESEARCH-NNN-slug.md` | Research / spike findings |
| `templates/adr-template.md` | `docs/adr/NNNN-title.md` | Architecture Decision Record |
| `templates/how-to-template.md` | `docs/how-to/[topic].md` | Developer task recipe |
| `templates/runbook-template.md` | `docs/runbooks/[scenario].md` | Operational response guide |
| `templates/postmortem-template.md` | `incidents/INC-YYYY-MM-DD-slug.md` | Blameless postmortem: used by incident-responder |
| `templates/domain-language-template.md` | `knowledge-base/domain-language.md` | Project vocabulary (singleton) |
| `templates/quality-gates-template.md` | `knowledge-base/quality-gates.md` | Project verification gates (singleton) |
| `templates/limitations-template.md` | `docs/limitations.md` | Known limitations registry (singleton) |
| `templates/language-conventions-template.md` | `knowledge-base/languages/<lang>.md` | Language conventions for detected project stack |
| `templates/testing-language-template.md` | `knowledge-base/languages/testing-<lang>.md` | Language-specific testing conventions |
| `templates/review-template.md` | (inline in review output) | Code review report |
| `templates/changelog-template.md` | `CHANGELOG.md` (project root) | Changelog seed (Keep a Changelog 1.1.0 + SemVer): skip if project uses automated changelog tooling |
| `templates/module-readme-template.md` | Module-level `README.md` | Module documentation seed (purpose, responsibilities, usage, key classes, dependencies, limitations) |
| `templates/importlinter-template.toml` | `pyproject.toml` (Python): `[tool.importlinter]` | Layered-architecture and forbidden-imports contracts to enforce Domain → Service → Infra in CI |

---

## Packs

Adopter-local packs let you layer project-specific agents, skills, KB pages, or templates over the playbook core without forking. Core updates still flow through `uv tool upgrade ai-playbook` (or `pip install -U ai-playbook`); pack content survives.

For a step-by-step authoring walkthrough, see [How to write a pack](how-to/write-a-pack.md). The rest of this section is the reference.

In v1, packs cover `agents`, `knowledge-base`, `skills`, and `templates`. The `commands/` directory is core-only: packs cannot ship custom shim content: but deploy auto-generates a standard slash-command shim for every pack agent, so pack agents are slash-invocable like core agents (shown as `(generated)` in deploy output).

### Configuration: `.ai-playbook.toml`

Place this file at your project root:

```toml
packs = [".ai-playbook/packs/django", ".ai-playbook/packs/internal"]

[model_tiers]
advisor = "opus"
executor = "sonnet"

[quality_tiers.agents]
xp-pair-programmer = "production"
docs-maintainer = "prototype"
```

- `packs` is a list of directories relative to the project root
- Order matters: last pack in the list wins on relative-path collisions
- Omit the file (or use `packs = []`) for a core-only deploy
- Pack files must be real UTF-8 text files inside the pack tree; discovery ignores symlinked source files.
- `model_tiers` declares the intended advisor/executor model mapping; `ai-playbook doctor` warns if the table is missing or incomplete. Single-model setups can use the same model for both tiers.
- `quality_tiers.agents` overrides the root `quality-tier:` for named agents. Values must be `production` or `prototype`; `ai-playbook status` shows effective tiers and `doctor` warns about unknown agent names.
- Run `ai-playbook config validate --json` in CI when packs or tier overrides are managed by automation.

### Optional pack manifest: `pack.toml`

Each pack can declare metadata in a `pack.toml` file at the pack root. The manifest is optional so existing local packs continue to work.

```toml
name = "django"
version = "1.2.3"
min_playbook_version = "1.0.0"
max_playbook_version = "1.9.0"
```

- `name` defaults to the pack directory name when omitted and must be unique across configured packs
- `version`, `min_playbook_version`, and `max_playbook_version` use semantic-version strings such as `1.2.3`
- Deployment, diff, doctor, and `config validate` check `min_playbook_version` and `max_playbook_version` before reading pack content
- Incompatible packs stop with a config error that names the required AI Playbook version

When a pack declares metadata, `deploy` prints a "Pack metadata" block and records the selected pack versions in `.playbook-version`:

```text
Pack metadata:
  django 1.2.3

pack: django@1.2.3
```

### Pack directory layout

Each pack mirrors the core overlay structure. Add only the files you customise:

```text
.ai-playbook/packs/django/
  agents/                       # optional: *.agent.md files
    django-model-reviewer.agent.md
  knowledge-base/               # optional
    django-patterns.md
  skills/                       # optional
    django-migration/SKILL.md
  templates/                    # optional
```

The four overlay dirs are `agents`, `knowledge-base`, `skills`, `templates`. `commands` is not pack-aware in v1.

### Precedence

For each relative path:

1. Core ships first
2. Each listed pack layers on top, in declared order
3. Last write wins

Examples:

| Setup | Winning source for `agents/story-refiner.agent.md` |
|---|---|
| no packs | core |
| `[django]`, django provides nothing for that path | core |
| `[django]`, django provides an override | django |
| `[django, internal]`, both provide overrides | internal (last in list) |

### Override warnings

`ai-playbook deploy` prints a "Pack overrides" block whenever a pack replaces a previously seen file. Each line names the new origin, previous origin, and the relative path: so silent overrides are not possible:

```text
Pack overrides:
  pack:internal overrides core at agents/story-refiner.agent.md
  pack:project-a overrides pack:internal at agents/story-refiner.agent.md
```

`ai-playbook doctor` surfaces the same overrides as warnings in its health report.

To make overrides **reviewable rather than merely visible**, run `ai-playbook doctor --strict --tool <tool>` in CI: overrides are warnings, and `--strict` exits 1 on warnings: so a new pack override fails the pipeline until someone acknowledges it. This matters most for overrides of gate-bearing agents (release-captain, incident-responder), where a pack can otherwise weaken approval gates with only a deploy-time warning.

### Operational guarantees

| Surface | Behavior with packs |
|---|---|
| `deploy` | Pack files copy alongside core, last-wins, with override warnings |
| `deploy --prune` | The command recognizes pack files as expected and never deletes them as orphans |
| `diff` | The command compares pack files against the winning pack/core source |
| `doctor` | Pack files first-class; staleness compared against pack source for overridden files |
| `.playbook-version` fingerprint | Includes pack content: pack edits change the fingerprint |

### Failure modes

| Cause | Behavior |
|---|---|
| `.ai-playbook.toml` malformed | Deploy, diff, doctor, and `config validate` stop with `Error: Malformed .ai-playbook.toml: ...` |
| `packs` is not a list of project-relative strings | Deploy stops with a config error |
| Duplicate, empty, absolute, or escaping pack path | Deploy stops with a config error |
| Duplicate pack name | Deploy, diff, doctor, and `config validate` stop with a config error so pack origins stay unambiguous |
| Pack path missing on disk | Deploy stops with `Error: Pack directory does not exist: ...` |
| Pack agent/KB file breaks its frontmatter contract | `config validate` exits 1 naming the file and missing keys; `doctor` reports the same finding as a warning (gate it in CI with `--strict`) |
| `pack.toml` malformed, invalid, or incompatible | Deploy, diff, doctor, and `config validate` stop with a config error |
| Hand-edit of deployed file | Lost on next deploy (same as pre-pack behavior): put overrides in a pack |

### Out of scope (v1)

- Publishable / pip-installable packs
- Pack dependency graphs
- Per-pack feature flags (`--language`, `--no-mcp`)
- Pack-level CLI commands (`ai-playbook pack add/list/remove`)
- `commands/` directory pack overlay

See [`docs/how-to/setup-multi-repo.md`](how-to/setup-multi-repo.md) for the multi-project sharing pattern that builds on packs.

---

## Developing the CLI

The CLI source lives in `src/deploy_ai_playbook/`, split across `cli.py`, `paths.py`, `config.py`, `fs.py`, `discovery.py`, `mcp.py`, and `backup.py`. The eval harness lives in `evals/run_eval.py`.

```bash
# Install with dev dependencies
uv sync --dev

# Run tests (CLI, contracts, evals)
uv run pytest tests/ -v

# Lint and format
uv run ruff check src/ tests/ evals/
uv run ruff format src/ tests/ evals/

# Verify eval files parse
python evals/run_eval.py check-structure

# Validate committed eval samples without an API key
python evals/run_eval.py validate-samples

# Validate agent output against rubric
python evals/run_eval.py validate <agent-name> <output-file>
```

All tests must pass and linting must be clean before committing.

---

## CI Setup Examples

The deployed `ci.yml` runs `make quality`: add language setup steps before it.

### Python (uv)

```yaml
      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: "3.12"

      - name: Set up uv
        uses: astral-sh/setup-uv@d4b2f3b6ecc6e67c4457f6d3e41ec42d3d0fcb86 # v5
        with:
          enable-cache: true

      - name: Install dependencies
        run: uv sync --dev
```

### Node.js / TypeScript

```yaml
      - name: Set up Node.js
        uses: actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020 # v4
        with:
          node-version: "20"
          cache: "npm"

      - name: Install dependencies
        run: npm ci
```

### Go

```yaml
      - name: Set up Go
        uses: actions/setup-go@40f1582b2485089dde7abd97c1529aa768e1baff # v5
        with:
          go-version-file: go.mod
```

### Rust

```yaml
      - name: Set up Rust
        uses: dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8 # stable
        with:
          components: clippy, rustfmt

      - name: Cache cargo
        uses: Swatinem/rust-cache@42dc69e1aa15d09112580998cf2ef0119e2e91ae # v2
```

Add these steps between the pinned checkout step and the `make quality` step.

---

## Environment

| Variable | Effect |
|---|---|
| `NO_COLOR=1` | Disables ANSI color in all CLI output: honored automatically by the Rich console used internally. Standard convention from [no-color.org](https://no-color.org/); set in CI logs or accessibility-sensitive terminals. |
| `TERM=dumb` | Same effect as `NO_COLOR=1`; honored by Rich. |
| `CLAUDE_PROJECT_DIR` | Read by `harness/telemetry.sh` to locate `.claude/usage.jsonl` when the Stop hook fires from a project root that differs from the working directory. |
| `CLAUDE_USAGE_MAX_BYTES` | Override the telemetry log rotation threshold (default `1048576` = 1 MiB). Set to `0` to disable rotation entirely. |
| `CLAUDE_USAGE_KEEP_ARCHIVES` | Number of rotated archives to keep (default `12`). Older archives are pruned. |
| `EVAL_JUDGE_MODEL` | Override the LLM judge model used by `evals/run_eval.py judge` and `eval-drift.yml`. Defaults to the most specific stable id for the pinned judge (`claude-sonnet-4-6`, which ships as an alias with no dated form); rotation cadence in [`evals/rubrics/README.md`](../evals/rubrics/README.md). |
| `ANTHROPIC_API_KEY` | Required only when running `evals/run_eval.py judge`. The structural eval path does not need it. |
| `CLAUDE_SKIP_TEACHBACK` | Bypass the Teach-back commit-msg gate for emergency commits. Use sparingly; documented in `harness/check-teachback.sh`. |
| `CLAUDE_SKIP_CLAUDE_MD_SIZE` | Bypass the CLAUDE.md size gate. Same emergency-only spirit. |

---

## See Also

- [Getting Started](getting-started.md): quick start and first feature walkthrough
- [User Guide](user-guide.md): full workflows, project-management tool setup, team usage
- [How-to Guides](how-to/): focused task recipes (invoke agents, resume sessions, quality gates)
- [Known Limitations](limitations.md): what the system does not do or assumes
- [Architecture](architecture.md): design decisions and repo structure
- [Contributing](../CONTRIBUTING.md): how to update the playbook
