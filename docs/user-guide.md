# User Guide

Day-to-day usage of AI Playbook: installation, workflows, agent invocation, and team setup. For a 5-minute walkthrough, see [Getting Started](getting-started.md).

---

## 1. Install

```bash
uv tool install ai-playbook            # from PyPI (recommended)
# or:  uv tool install --editable /path/to/ai-playbook   # from a local clone
ai-playbook list   # should list 8 agents
```

---

## 2. Before You Start

1. Deploy the playbook into the target project: `ai-playbook deploy --agent all --tool <claude|copilot|cursor|kiro>`.
2. Create the runtime artifact directories if they do not exist: `stories/`, `plans/`, `research/`, `audits/`, `reviews/`, and `incidents/`.
3. Decide whether generated artifacts should be tracked. Use `ai-playbook artifact-policy local` to keep stories, research, plans, audits, reviews, and incidents out of Git, or `ai-playbook artifact-policy shared` when those records should be committed or governed manually.

Then review and edit the project-specific files below. Agents seed any missing template-backed file on first use and announce what they created: the seed is a starting point, not team policy.

| File | Seeded from | Purpose |
|------|-------------|---------|
| `knowledge-base/domain-language.md` | `templates/domain-language-template.md` | Project vocabulary: agents use it to name things consistently |
| `knowledge-base/quality-gates.md` | `templates/quality-gates-template.md` | Verification commands and coverage thresholds |
| `docs/limitations.md` | `templates/limitations-template.md` | What the system does not do, does not support, or assumes |
| `docs/adr/NNNN-*.md` | `templates/adr-template.md` | One file per architectural decision already made |
| `knowledge-base/feature-flags.md` | (deployed as-is) | Feature-flag provider and naming conventions |

**Rules file (`CLAUDE.md`).** Keep it lean in your deployed project. Periodically remove rules that current models handle natively.

For multi-repo teams sharing domain vocabulary, see [How To Set Up Multi-Repo Teams](how-to/setup-multi-repo.md).

---

## 3. The Loop

**Default invocation sequence:**

```text
story-refiner → slice-planner → xp-pair-programmer → diff-reviewer → release-captain
```

**Minimal invocation sequence (trivial changes):**

```text
xp-pair-programmer → diff-reviewer
```

For path selection guidance, see [How To Choose the Right Workflow Path](how-to/choose-workflow-path.md).

### What each agent does

| Agent | Input | Output |
|-------|-------|--------|
| **story-refiner** | Idea, description, or issue reference | Verified story with acceptance criteria |
| **slice-planner** | Story (and optional research) | Tactical plan with vertical slices and TDD steps |
| **xp-pair-programmer** | Plan or story | Tested code staged at the commit approval gate (acceptance tests, then unit TDD) |
| **diff-reviewer** | Diff or PR reference | Review against acceptance criteria, KB standards, and Definition of Done |
| **release-captain** | Story, branch, PR/MR reference, or version | Opened PR/MR, watched CI, merged on approval, version bump and tag, post-deploy smoke |
| **incident-responder** | Incident reference, alert, or telemetry paths | Triage timeline, ranked hypotheses, blameless postmortem in `incidents/` (read-only on production) |
| **code-inspector** | Module path, layer, or whole-repo audit request | Prioritised findings report in `audits/` |
| **docs-maintainer** | Module, feature, or `adr` request | Documentation or ADR in `docs/` |

**retrospective** is a skill, not an agent. After completing a story or hitting repeated friction, it surfaces learnings and proposes knowledge-base updates.

### Solo vs. Team

| Mode | Workflow path | Notes |
|------|----------|-------|
| **Solo** | xp-pair-programmer → diff-reviewer → fixes → merge | diff-reviewer replaces peer review |
| **Team** | Full workflow path for shared features | Keep `domain-language.md` and `docs/adr/` team-owned |

---

## 4. Invoking Agents

Full reference: [How To Invoke Agents](how-to/invoke-agents.md).

**Quick form:**

```text
Use <agent-name>: <input>
```

Always name the agent explicitly. Without a name, the AI tool guesses: and may guess wrong.

**Work item input: four valid formats:** playbook story number (`STORY-001`), file path, inline paste, or external tracker reference. Any of these triggers automatic artifact-chain resolution: matching research and plan files load alongside the internal story artifact.

| Tool | Slash command | Natural language |
|------|---------------|------------------|
| Claude | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Copilot | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Cursor | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Kiro | Not supported | `Use story-refiner: <input>` |

---

## 5. Resumability

AI tools lose context between sessions. The playbook handles this with **file-based artifacts**: plain markdown that any AI tool can read.

| Directory | Contents | Created by | Used by |
|-----------|----------|------------|---------|
| `stories/` | Internal story artifacts normalized from ideas, tracker work items, bugs, chores, or spikes | story-refiner | all agents |
| `research/` | Codebase findings, design options | story-refiner | slice-planner, xp-pair-programmer |
| `plans/` | Task breakdowns with TDD steps and `## Progress` markers | slice-planner | xp-pair-programmer |
| `audits/` | Codebase audit reports | code-inspector | xp-pair-programmer (to address findings) |
| `reviews/` | Optional local review reports | diff-reviewer | humans, release-captain handoff |
| `incidents/` | Triage notes and postmortems | incident-responder | release-captain, follow-up stories |
| `knowledge-base/` | Team standards, decisions, vocabulary | you (human) | all agents |

These files live in the repo: not in `~/.claude/` or any tool-specific location: so any AI tool can resume from them. Whether they are committed or kept local is a team policy choice.

Find the right file with `ai-playbook artifacts` or search by path/content with `ai-playbook artifacts --query <text>`.

Full reference: [How To Resume a Session](how-to/resume-session.md).

---

## 6. Works With Your Stack

| Surface | Supported |
|---------|-----------|
| **Languages** | Python is the maintained reference implementation. Agents and the starter harness detect other stacks from project config; team conventions come from `templates/language-conventions-template.md`. |
| **Methodology** | Scrum, Kanban, Shape Up, or no formal process: methodology-agnostic. For Kanban, skip story points or use T-shirt sizing (S/M/L). |
| **AI tool** | Claude (full), Copilot (full), Cursor (full), Kiro (agents, KB, skills, templates, rules: slash commands not supported). |
| **Slash commands** | Claude, Copilot (VS Code), Cursor. Kiro uses natural language only (`Use story-refiner: ...`). |
| **Project-management tool / issue tracker** | Jira, GitHub Issues/Projects, GitLab Issues, Bitbucket Cloud Issues, Linear, or manual paste: see § 7. |
| **Feature flags** | Tool-agnostic. Update `knowledge-base/feature-flags.md` when you change providers. |

---

## 7. Project Management Tool Setup

The playbook supports Jira, GitHub Issues/Projects, GitLab Issues, Bitbucket Cloud Issues, Linear, or no tracker (manual paste). It treats each external object as a provider-neutral work item, then writes a playbook story artifact (`STORY`, `BUG`, `SPIKE`, or `CHORE`) for implementation.

Full setup: [How To Set Up Your Project Management Tool](how-to/setup-issue-tracker.md).

**At a glance:** `ai-playbook deploy` auto-configures the Atlassian (Jira) MCP only when `.ai-playbook.toml` sets `[issue-tracker] provider = "jira"`; with no declared provider it deploys no MCP. GitHub Issues and GitHub Projects work through the issue reference plus `gh` CLI/MCP context. GitLab uses `glab` or GitLab MCP. Bitbucket Cloud uses `BITBUCKET_TOKEN`. Linear uses `LINEAR_API_KEY` or Linear's MCP. Without a tracker, paste work item content when an agent asks.

The playbook is **methodology-agnostic** and **project-management-tool agnostic**. External tools can call the unit of work an issue, ticket, task, story, epic item, or project item. Inside the playbook, the durable implementation artifact is a story file with `type: story | bug | spike | chore` and `issue-ref:` preserving the original tracker identity.

---

## 8. Quality Enforcement

The playbook enforces rules mechanically, not solely through documentation.

Full setup: [How To Enforce Quality Gates](how-to/enforce-quality.md).

**Summary:** keep `make quality` green, optionally install local hooks (`pre-commit install`, lefthook, or husky), set the quality tier in `CLAUDE.md`, configure `knowledge-base/quality-gates.md`, and use the teach-back gate before committing non-trivial code.

For high-throughput teams, see also: lint-messages-as-teaching, doc gardening, and garbage-collection sweeps in `knowledge-base/working-agreement.md` § Reference: Agent-First Automation.

---

## 9. Common Tasks

### Reduce the number of questions an agent asks

```text
Minimize prompts. Use recommended defaults for reversible decisions. Ask me only when the choice changes scope, architecture, data, security, irreversible behavior, or user-visible behavior.
```

Approval gates still apply for artifacts, staging, commits, destructive operations, and external side effects.

### Run xp-pair-programmer without pausing at every RED test

By default xp-pair-programmer pauses on each failing test so you can redirect before code is written. To skip the pauses on a mechanical slice:

```text
low-prompt mode: don't pause at RED, just go.
```

Review at the commit boundary instead of at each step. Keep the interactive default for design-heavy slices where the test shape itself matters.

### Lower token usage

```text
Use the KB efficiency rule. Load only the smallest KB section needed for this decision, then continue.
```

```text
Use concise communication. Keep updates compact, avoid restating context, and expand only for risks, decisions, failures, or approvals.
```

These change communication style and KB loading only: not research depth, validation, artifact quality, model tier, or safety checks.

### Update the playbook after a new release

```bash
# From PyPI
uv tool install --force ai-playbook

# From a local clone
uv tool install --force --editable /path/to/ai-playbook

ai-playbook upgrade-check --tool claude   # CI-friendly drift check (exit 0/1/2)
ai-playbook doctor --tool claude          # full health report
ai-playbook deploy --agent all --tool claude
```

`upgrade-check` is the smallest command for drift detection: it exits non-zero when source has changed since the last deploy, which is suitable for CI. `doctor` is the full health report.

### Check deployment health

```bash
ai-playbook doctor --tool claude
```

Reports stale files, missing agents, disabled agents, fingerprint drift, and missing runtime directories in one pass.

### Check telemetry wiring (Claude only)

```bash
ai-playbook telemetry status
```

Shows whether the Claude Stop hook is configured, where `.claude/settings.json` lives, and whether `harness/telemetry.sh` is deployed. Use `telemetry enable` / `telemetry disable` to manage the hook outside the deploy flow.

### Correct an agent that got something wrong

Push back in the conversation. If the same issue recurs across sessions, update the relevant knowledge-base file: that fixes it for every future run.

---

## See Also

- [Getting Started](getting-started.md): quick start and first feature walkthrough
- [Architecture](architecture.md): design decisions, repo structure, and how agents work
- [CLI Reference](cli-reference.md): full command and flag reference
- [Known Limitations](limitations.md): what the system does not do or assumes
- [Methodology & References](references.md): full attribution
- [Contributing](../CONTRIBUTING.md): how to update the playbook

### How-to Guides

- [Invoke Agents](how-to/invoke-agents.md): start any agent with the right input
- [Resume a Session](how-to/resume-session.md): pick up where you left off
- [Choose Workflow Path](how-to/choose-workflow-path.md): pick the right workflow path
- [Set Up Project Management Tool](how-to/setup-issue-tracker.md): Jira, GitHub Issues/Projects, GitLab, Bitbucket, Linear, or manual paste
- [Enforce Quality Gates](how-to/enforce-quality.md): pre-commit hooks and gates
- [Set Up Multi-Repo Teams](how-to/setup-multi-repo.md): shared vocabulary across repos
