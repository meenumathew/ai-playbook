# AI Playbook

[![CI](https://github.com/meenumathew/ai-playbook/actions/workflows/ci.yml/badge.svg)](https://github.com/meenumathew/ai-playbook/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/meenumathew/ai-playbook/branch/main/graph/badge.svg)](https://codecov.io/gh/meenumathew/ai-playbook)
[![CodeQL](https://github.com/meenumathew/ai-playbook/actions/workflows/codeql.yml/badge.svg)](https://github.com/meenumathew/ai-playbook/actions/workflows/codeql.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/meenumathew/ai-playbook/badge)](https://scorecard.dev/viewer/?uri=github.com/meenumathew/ai-playbook)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A developer workflow framework for AI-assisted software development. Eight agents take a change from idea to deployed code: and through production incidents: using **Extreme Programming (XP)**, **Test-Driven Development (TDD)**, and **Domain-Driven Design (DDD)** practices. Planning, audit, and incident work is captured in markdown artifacts, so work is resumable across sessions and AI tools.

> **Audience.** Developers building production-minded software who are comfortable with TDD, refactoring, and code review.

## Prerequisites

The playbook is most useful when you are already comfortable with:

- **Test-Driven Development**: the red-green-refactor cycle, test doubles, the test pyramid.
- **Refactoring**: code smells; extract, inline, and move patterns; working in small steps.
- **Code review**: reading diffs, giving and receiving feedback.
- **Git**: branching, rebasing, conventional commits.
- **At least one backend language**: Python, TypeScript, Go, or Rust.

## When the Playbook Is a Good Fit

- You ship production code and want AI tools to follow your team's standards.
- AI tools have produced code that ignores your architecture, skips tests, or drifts from requirements.
- You work across multiple AI tools (Claude, Copilot, Cursor, Kiro) and want a consistent workflow.
- Your team uses any methodology (Scrum, Kanban, Shape Up, or no formal process) with any project-management tool or issue tracker (Jira, GitHub Issues/Projects, GitLab Issues, Bitbucket Issues, Linear, or none).

## When It Is Not

- You are learning to code for the first time: start with tutorials and courses.
- You want a plug-and-play AI copilot with no configuration: this is an opinionated workflow framework, not a chat wrapper.
- Your team does not write tests: the playbook enforces TDD, and without buy-in it will feel like friction.

---

## What the Playbook Does

AI coding tools are capable but unguided: they write code without grounding in requirements, skip tests, ignore existing patterns, and drift from intent. The playbook gives AI tools a structured workflow: refine the idea or tracker work item, research the codebase, plan in vertical slices, build test-first, review against standards. The workflow uses markdown story artifacts, research, plans, audits, reviews, and incidents where durable context matters, so context survives across sessions, project-management tools, and AI tool switches.

---

## Key Features

- **Eight specialised agents**: story-refiner, slice-planner, xp-pair-programmer, diff-reviewer, release-captain, incident-responder, code-inspector, docs-maintainer.
- **Two-layer testing (acceptance tests + unit TDD)**: acceptance tests written from story acceptance criteria verify *built the right thing*; unit TDD drives the implementation, verifying *built it right*. xp-pair-programmer enforces both layers.
- **Quality tiers**: set `prototype` or `production` globally, then override individual agents in `.ai-playbook.toml` when one needs different ceremony.
- **Language-agnostic workflow**: agents and the starter harness detect common project configs. Python is the maintained reference implementation; other stacks start from team-owned convention templates.
- **Tool-aware deployment** *(CLI)*: `ai-playbook deploy` writes the right files to the right places for Claude, GitHub Copilot, Cursor, and Kiro. Claude, Copilot, and Cursor get slash commands; Kiro uses natural-language invocation.
- **Adopter-local packs**: extend or override the playbook core with project-specific agents, knowledge-base files, skills, or templates via `.ai-playbook.toml`. Optional `pack.toml` metadata records pack versions and compatibility bounds. Core updates flow through `uv tool upgrade ai-playbook` (or `pip install -U ai-playbook`); pack content survives. Commands are core-only in v1. See [CLI Reference § Packs](docs/cli-reference.md#packs).
- **Model-agnostic tiers**: agents declare `advisor` or `executor` tier in frontmatter; map tiers to whatever models you use (Anthropic, OpenAI, Google, Ollama-backed local models, mixed). Source files never hard-code model IDs. Deploying to Claude materializes your `[model_tiers]` mapping into the deployed agent frontmatter, so per-agent model routing is automatic; other tools map tiers in their own config. See [`knowledge-base/model-tier.md`](knowledge-base/model-tier.md).
- **Resumable**: file-based artifacts (stories, research, plans, audits, reviews, incidents) let any AI tool pick up where another left off.
- **Project-management-tool agnostic** *(work item in, story artifact out)*: `skills/issue-fetch/SKILL.md` accepts a Jira issue key, GitHub issue or Project item, GitLab issue, Bitbucket Cloud issue, Linear issue ID, tracker URL, or pasted work item. The agent preserves the original reference in `issue-ref:`, resolves local story artifacts first, then fetches via the configured CLI, MCP server, or provider API. The CLI itself does not call any tracker.
- **Host-agnostic** *(skill contract)*: `skills/host-adapter/SKILL.md` defines stable operation IDs (`host.pr.create`, `host.pr.review`, `host.pr.merge`) for GitHub, GitLab, Bitbucket Cloud, and Gitea/Forgejo. Adopters satisfy the contract with their host CLI (`gh`, `glab`, `tea`) or REST. This is a markdown contract for agents, not a Python runtime adapter inside the CLI.
- **Eval-backed** *(harness)*: each agent ships input + expected pairs in `evals/` plus a structural validator in `evals/run_eval.py`. An optional, opt-in LLM-as-judge workflow (`.github/workflows/eval-drift.yml`) catches semantic drift; it is manual by default (run it from the Actions tab via `workflow_dispatch`, or re-enable the weekly cron in the workflow) because that step calls the Anthropic API and requires the `ANTHROPIC_API_KEY` repo secret (it fails closed without it). The structural pass is offline and vendor-neutral. The judge scores committed baselines in `evals/samples/`: one captured live-agent baseline (story-refiner, repo-grounded) plus hand-curated seeds for the rest: alongside adversarial baselines (must pass) and deliberately-flawed negative controls (must fail, catching judge leniency drift). A green eval run proves rubric-baseline-judge agreement, not full live agent behaviour (see `evals/samples/README.md` § Scope).
- **Self-improving**: the built-in retrospective skill turns session friction into knowledge-base updates.

---

## Quick Start

```bash
# 1. Install the CLI. Requires Python 3.12+ and uv on PATH.

# (a) From PyPI (recommended).
uv tool install ai-playbook
# or:  pipx install ai-playbook
# or:  pip install ai-playbook

# (b) From source (for contributors or pre-release evaluation).
git clone https://github.com/meenumathew/ai-playbook.git
cd ai-playbook
uv tool install --editable .           # tracks local edits
# or:  pipx install --editable .
# or:  uv tool install .                # immutable install from source

# 2. Deploy into your project.
cd /path/to/your-project
ai-playbook init
ai-playbook deploy --agent all --tool claude

# 3. Wire the deployed pre-commit hooks (one-time per clone).
# Required so the Teach-back commit-msg gate, gitleaks secret scan,
# and shellcheck/markdownlint hooks run locally: not just in CI.
uvx pre-commit==4.3.0 install
uvx pre-commit==4.3.0 install --hook-type commit-msg
```

Set the **quality tier** in the deployed `CLAUDE.md`: `prototype` or `production`. Every agent calibrates ceremony to that tier.

Then open your AI tool and run:

```text
Use story-refiner: here's the feature: <describe the outcome>
```

Recommended invocation sequence: **story-refiner** → **slice-planner** → **xp-pair-programmer** → **diff-reviewer** → **release-captain**. Invoke each step deliberately; the CLI does not auto-run an agent chain.

For trivial changes, skip story-refining:

```text
Use xp-pair-programmer: <describe the change>
```

---

## The Dev Loop

```text
story-refiner    →  Refine the idea, research the codebase, write a verified story
     ↓
slice-planner    →  Design approach, structure vertical slices, write tactical plan
     ↓
xp-pair-programmer          →  Acceptance tests from acceptance criteria (outer loop), then unit TDD (inner loop)
     ↓
diff-reviewer    →  Verify against acceptance criteria, knowledge base standards, and Definition of Done
     ↓
release-captain  →  Open PR/MR, watch CI, merge on approval, version bump, tag, post-deploy smoke
```

When production breaks, **incident-responder** triages, ranks hypotheses, writes the blameless postmortem, and proposes follow-up artifacts. It is read-only on production; humans, with release-captain, execute mitigations.

**code-inspector** runs health checks and **docs-maintainer** writes documentation and Architectural Decision Records. See the [User Guide](docs/user-guide.md) for all workflow paths: minimal, spike, solo, and team.

### Scope: what release-captain does and does not do

release-captain ships up to the tag, not into production. The playbook deliberately keeps deploy execution outside the agent surface so adopters wire their own CD pipeline.

| release-captain does | release-captain does NOT |
|---|---|
| Open PR/MR via the host-adapter (GitHub, GitLab, Bitbucket Cloud, Gitea) | Auto-merge: every merge requires explicit user approval |
| Watch CI and refuse to proceed on red | Run `kubectl`, `terraform`, `ansible`, `helm`, `docker push`, or any deploy command |
| Bump version, update `CHANGELOG`, create an annotated tag | Push a tag without explicit user approval for that push |
| Run the post-deploy smoke checklist after a deploy lands | Execute the deploy itself: your CI/CD picks up from the tag |
| Hand off to incident-responder if smoke fails | Roll back deploys, toggle feature flags, scale services, rotate secrets |

For auto-deploy on tag push, configure your CI/CD pipeline (GitHub Actions, GitLab CI, Bitbucket Pipelines, ArgoCD) to react to `v*` tags. Deploy is environment-specific, and the failure mode of an over-eager agent is high: the playbook stays out of that loop by design. See [`knowledge-base/release.md`](knowledge-base/release.md) for the full gate list.

---

## Your First Feature: Walkthrough

An end-to-end example for a small change. Time: about 5 minutes.

**Scenario.** Add input validation to an existing function.

**Step 1. Start xp-pair-programmer.**

```text
Use xp-pair-programmer: Add input validation to create_user in src/users.py.
Reject empty names and emails without an @ symbol.
```

**Step 2. xp-pair-programmer writes acceptance tests first (outer loop).**

Before any production code, xp-pair-programmer writes a failing acceptance test for each acceptance criterion at the system boundary:

```python
# tests/acceptance/test_ac_create_user.py
def test_ac_create_user_rejects_empty_name():
    with pytest.raises(ValueError, match="name"):
        create_user(name="", email="valid@example.com")

def test_ac_create_user_rejects_invalid_email():
    with pytest.raises(ValueError, match="email"):
        create_user(name="Alice", email="no-at-symbol")
```

Both fail, confirming the acceptance criteria are testable and the team is building the right thing.

**Step 3. xp-pair-programmer drives implementation with unit TDD (inner loop).**

One acceptance criterion at a time, with the simplest code that passes:

```python
if not name:
    raise ValueError("name must not be empty")
```

Run the first acceptance test: green. Move to the next criterion, write code, refactor.

**Step 4. All acceptance tests pass.**

```text
AC 1: rejects empty name ✅
AC 2: rejects invalid email ✅

Changes staged. Say 'commit' to proceed.
```

**Step 5. Reply `commit`.** Done. Optionally run diff-reviewer on the diff.

**Why two layers.** Acceptance tests verify *what*: built the right thing, from acceptance criteria. Unit tests verify *how*: built it right, from the implementation. The two-layer pattern is from [Acceptance Test-Driven Development (ATDD)](https://www.agilealliance.org/glossary/atdd/).

---

## Which Path?

```text
Is the change trivial? (typo, rename, one-liner, config)
  └─ YES → Minimal: xp-pair-programmer → diff-reviewer
  └─ NO → Is the requirement clear and the design obvious?
           ├─ YES, ≤ 5 ACs → xp-pair-programmer (from story) → diff-reviewer
           ├─ YES, 6–7 ACs → slice-planner → xp-pair-programmer → diff-reviewer
           ├─ YES, 8+ ACs → story-refiner to split/trim → slice-planner → xp-pair-programmer → diff-reviewer
           └─ NO → Do you understand the problem space?
                    ├─ YES → story-refiner → slice-planner → xp-pair-programmer → diff-reviewer
                    └─ NO  → Spike (timebox) → story-refiner → ...
```

---

## Project-Specific Knowledge Base

Some files are project-specific: adopters fill them in for their own codebase. Agents seed these from templates on first use and warn that the file is unedited. You must edit them by hand; agents only seed, they do not infer your domain.

| File | Purpose | Seeded from |
|------|---------|-------------|
| `knowledge-base/domain-language.md` | Project glossary: terms used in stories, plans, code, and tests | `templates/domain-language-template.md` |
| `knowledge-base/quality-gates.md` | Project quality contract: Make targets and underlying lint, format, type-check, and test commands | `templates/quality-gates-template.md` |
| `knowledge-base/languages/<lang>.md` | Per-language conventions (auto-detected from `pyproject.toml`, `package.json`, and similar config) | `templates/language-conventions-template.md` |
| `knowledge-base/languages/testing-<lang>.md` | Per-language testing conventions | `templates/testing-language-template.md` |
| `docs/limitations.md` | Known limitations: what the system does not do, does not support, or assumes | `templates/limitations-template.md` |
| `docs/adr/NNNN-*.md` | One ADR per architectural decision | `templates/adr-template.md` |

When an agent seeds a file, it reports: `Seeded knowledge-base/domain-language.md from template: review and edit.` Open the file and replace the placeholders with your actual terms. Until you do, plans and stories may drift toward generic language.

---

## Documentation

Docs follow the [Diataxis framework](https://diataxis.fr/). The canonical docs map is [Documentation Index](docs/README.md); this root README stays the project landing page.

| Need | Start here |
|------|------------|
| First successful walkthrough | [Getting Started](docs/getting-started.md) |
| Day-to-day tasks | [User Guide](docs/user-guide.md) and [How-to Guides](docs/how-to/) |
| Exact commands and contracts | [CLI Reference](docs/cli-reference.md) |
| Design context and rationale | [Architecture](docs/architecture.md) and [Methodology and References](docs/references.md) |
| Full Diataxis map | [Documentation Index](docs/README.md) |

---

## Quality Enforcement (Harness Engineering)

The playbook does not stop at documenting rules: it enforces them mechanically.

| Layer | Mechanism | How it blocks violations |
|-------|-----------|--------------------------|
| **Context** | `CLAUDE.md`, knowledge-base, stories, templates | Agents read the rules before acting |
| **Constraints** | Architecture tests (`test_architecture.py`) | Build fails if a module imports from a higher layer |
| **Linters** | Make targets, local hooks, and GitHub Actions CI | Commit or merge blocked when lint, types, tests, or secrets checks fail |
| **Mutation testing** | Dedicated PR/scheduled workflow with a committed regression baseline | New surviving/no-test mutants block until reviewed |

Quality gates use a language-neutral contract:

```text
make format    make format-check    make lint    make typecheck    make test    make quality
```

Local hooks can be pre-commit, lefthook, husky, or none. CI and agents share the same Make-target contract.

**Cognitive health gates** prevent AI-generated code from outrunning understanding:

- **Teach-back**: before committing non-trivial code, the developer explains what it does, where to debug it, and how it would change.
- **Commit rationale + Teach-back trailer**: non-trivial commits explain *why* in the body and carry a one-line `Teach-back:` trailer.

See [Architecture § Harness Engineering](docs/architecture.md#harness-engineering) for details.

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (package manager)
- An AI coding tool such as [Claude Code](https://claude.ai/code), [GitHub Copilot](https://github.com/features/copilot), [Cursor](https://cursor.com), [Kiro](https://kiro.dev), or another tool that can read deployed markdown instructions

---

## Scope and Limitations

This is an opinionated playbook, not a finished framework. It works well for the cases below and is explicit about its bounds elsewhere.

**Designed for:**

- Solo developers and small teams (roughly 2–10 engineers) using AI tools day-to-day.
- Production code with genuine test, review, and release discipline.
- Teams comfortable adapting markdown rules to their stack.

**Highlights from the limitations registry**: see [`docs/limitations.md`](docs/limitations.md) for the full list:

- **Single-maintainer project.** Designed and maintained by one person. Governance, the RFC process, and the compatibility promise are documented in [`GOVERNANCE.md`](GOVERNANCE.md), [`docs/rfcs/README.md`](docs/rfcs/README.md), and [`docs/deprecation-policy.md`](docs/deprecation-policy.md). Multi-maintainer transition criteria are explicit; until they are met, the maintainer has final say.
- **Not benchmarked against alternatives.** No published comparison versus Cursor rules, Aider conventions, Cline, Continue, or other agent frameworks. Quality claims rest on the playbook's own evals, not external baselines.
- **Eval suite is v1.** Adversarial pairs, committed baselines, structural calibration, generated standard-agent discovery, and schema-backed rubrics for all standard agents are in place. Multi-turn agent simulation, judge-ensemble scoring, and historical regression budgets are not yet implemented. The drift job is opt-in (manual `workflow_dispatch`, weekly cron off by default), makes a single-judge call against committed baselines, and fails closed if no baselines or judge secret are configured.
- **Python is the only fully supported language.** Other languages (Go, Rust, Java, TypeScript, and others) are auto-detected and work, but team-owned conventions in `knowledge-base/languages/<lang>.md` start from blank templates.
- **Bitbucket Server / Data Center is not supported.** Bitbucket Cloud only: see [ADR-0001](docs/adr/0001-bitbucket-server-not-supported.md).
- **No paging integration.** The notifier covers Slack, email, and generic webhooks only; PagerDuty and Opsgenie are intentionally out of scope.
- **release-captain stops at "tag pushed".** Adopters wire their own deploy pipeline triggered by tags; the playbook does not deploy.

**Not the right tool if** you need a polished commercial product with SLAs, a vendor support contract, or guaranteed backward compatibility across versions.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for development setup, testing, and how to submit changes.

---

## License

[MIT](LICENSE): Meenu Mathew
