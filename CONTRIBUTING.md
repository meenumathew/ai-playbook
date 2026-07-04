# Contributing

Thank you for your interest in contributing to AI Playbook. This guide covers how to set up for development, make changes, and submit them.

Before you start, decide which venue your change belongs in:

- **PR**: bug fix, doc fix, refactor, additive change with one obvious shape. Read on.
- **RFC**: new agent, new CLI command, KB restructure, anything with multiple plausible designs. See [`docs/rfcs/README.md`](docs/rfcs/README.md).
- **ADR**: durable architectural decision. See [`docs/adr/README.md`](docs/adr/README.md).

The compatibility promise that constrains all three venues lives in [`docs/deprecation-policy.md`](docs/deprecation-policy.md). Decision authority lives in [`GOVERNANCE.md`](GOVERNANCE.md).

---

## Table of Contents

- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [What to Update and Where](#what-to-update-and-where)
- [Testing](#testing)
- [Git History](#git-history)
- [Commit Conventions](#commit-conventions)
- [Pull Requests](#pull-requests)
- [Adding a New Language](#adding-a-new-language)
- [Adding a New Agent](#adding-a-new-agent)
- [Changing a Tool or Service](#changing-a-tool-or-service)
- [File Guidelines](#file-guidelines)
- [Maintenance](#maintenance)

---

## Getting Started

1. Fork the repository
2. Clone your fork
3. Create a branch for your change

```bash
git clone https://github.com/<your-username>/ai-playbook.git
cd ai-playbook
git checkout -b feat/your-feature
```

---

## Development Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
# Install dependencies (including dev tools)
uv sync --dev

# Install pre-commit hooks
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg

# Verify everything works
make quality
uv run pytest tests/ -v
uv run ruff check src/ tests/ evals/
uv run ruff format --check src/ tests/ evals/
uv run pyright

# Optional before pushing: run CI's security gates locally
# (secret scan + pip-audit + bandit; needs network, so not part of `make quality`)
make security
```

---

## Making Changes

### Repo Structure

See **[Architecture](docs/architecture.md#repo-structure)** for the full annotated directory tree.

### Workflow

1. Read the relevant existing files before making changes
2. Make your change: prefer editing existing files over creating new ones
3. Add or update tests if you changed `src/`, agents, or evals
4. Run the full validation suite (see [Testing](#testing))
5. Commit with a Conventional Commit message (see [Commit Conventions](#commit-conventions))
6. Open a pull request

---

## What to Update and Where

### Knowledge base (`knowledge-base/`)

Update when you:

- Discover new team preferences: "the team always does X this way now"
- Establish new patterns from the codebase
- Learn from mistakes: update to prevent repeats
- Change practices: remove or replace outdated guidance

**Should it go in the knowledge base (KB)?** Ask:

- Is it unique to how the team works? → Probably yes
- Will the team reference it repeatedly? → Probably yes
- Is it obvious or universal? → Probably no

### Agents (`agents/`)

Update when you:

- Find an agent giving wrong or inconsistent output
- Want to add a new step or enforce a new rule
- Fix outdated knowledge base references

### Evals (`evals/`)

Update when you:

- Change an agent's behavior, steps, or output format
- Add a new agent (create both `<agent>-input.md` and `<agent>-expected.md`)
- Add or refresh `evals/samples/<agent>.md` when a standard agent's expected output changes materially
- Fix an agent that produces incorrect output: update the expected file too

### CLI (`src/`)

Update when you:

- Add new commands or flags
- Fix deployment bugs
- Need to deploy to a new tool target

Always add or update tests alongside CLI changes.

### Renaming: blast-radius checklist

Renaming a file or symbol always touches more places than the obvious one.
Before opening a PR that renames an agent, KB file, skill, or tool target,
walk this list. Missing one entry will fail a contract test on push, but
catching it locally is cheaper.

**Rename an agent (`agents/<name>.agent.md`):**

1. `agents/<old>.agent.md` → `agents/<new>.agent.md`, including frontmatter `id:`.
2. `commands/<old>.md` → `commands/<new>.md` (the slash-command shim).
3. `evals/<old>-input.md` and `evals/<old>-expected.md` (and the adversarial pair).
4. `evals/samples/<old>.md` if it exists.
5. `evals/rubrics/<old>.json` if it exists.
6. `tests/acceptance/contract_data.py`: `AGENT_CONTRACTS`, `AGENTS_WITH_READ_BUDGET`, `AGENT_FORBIDDEN_PHRASES`.
7. Every `agents/*.agent.md` that lists `<old>` in `handoff:` (grep first).
8. `README.md` agent list, `CHANGELOG.md` skills/agents lines, `CLAUDE.md` Workflow table.
9. `knowledge-base/INDEX.md` § Agent Use rows.

Find them all up front: `grep -rn "<old>" agents/ commands/ evals/ tests/ knowledge-base/ README.md CHANGELOG.md CLAUDE.md`.

**Rename a KB file (`knowledge-base/<name>.md`):**

1. `knowledge-base/<old>.md` → `knowledge-base/<new>.md`.
2. `knowledge-base/INDEX.md` rows that point at it.
3. `knowledge-base/CHEATSHEET.md` if cited there.
4. Every `agents/*.agent.md` and `skills/*/SKILL.md` that cites `knowledge-base/<old>.md` (grep).
5. `CLAUDE.md` if cited there.
6. Every `evals/*-expected.md` and `evals/rubrics/*.json` that names the file.

Find them all up front: `grep -rn "<old>.md" agents/ skills/ knowledge-base/ evals/ CLAUDE.md`.

**Rename a skill (`skills/<name>/SKILL.md`):**

1. `skills/<old>/` → `skills/<new>/` (the whole directory).
2. Every `agents/*.agent.md` that cites `skills/<old>/SKILL.md` (grep).
3. `knowledge-base/INDEX.md` § Skills rows.
4. `CHANGELOG.md` skills line.
5. `tests/acceptance/contract_data.py` if the skill is in a contract.

After any rename: run `make quality` locally: `test_pointer_contracts.py` is the
catch-net for missed citations.

---

## Testing

Run the full validation suite before submitting:

```bash
# All tests with coverage
uv run pytest tests/ -v --cov=src --cov-fail-under=95

# Lint
uv run ruff check src/ tests/ evals/

# Format check
uv run ruff format --check src/ tests/ evals/

# Type check
uv run pyright

# Eval structure validation
uv run python evals/run_eval.py check-structure

# Eval structural calibration
uv run python evals/run_eval.py calibrate

# Smoke test CLI
uv run ai-playbook list

# Full local gate, including docs lint
make quality
```

**Test suite layers:**

| Layer | What it tests | Location |
|-------|--------------|----------|
| Unit | CLI commands, argument parsing, edge cases | `tests/unit/` |
| Acceptance | End-to-end deploy, agent contracts, eval structure | `tests/acceptance/` |
| Agent contracts | Agents reference KB files that exist, use correct format | `tests/acceptance/test_agent_contracts.py`, `tests/acceptance/test_kb_skill_contracts.py`, `tests/acceptance/test_story_workflow_contracts.py`, `tests/acceptance/test_harness_release_contracts.py` |
| Eval harness | Rubrics parse, structural validator is calibrated, and agent output can be judged semantically | `evals/run_eval.py` |

**Rules:**

- Write the test first: this is a Test-Driven Development (TDD) project
- All tests must pass before committing
- Minimum 95% total coverage on `src/`, with branch coverage enabled
- Use `tmp_path` (pytest fixture) for filesystem tests
- Markdown-content assertions must carry a phrase-pin classification label: `# CONTRACT-PHRASE:`, `# STRUCTURE-MARKER:`, or `# ACCIDENTAL-PIN:`. The classification convention lives in `tests/acceptance/__init__.py`. CLI-output assertions (on `result.output`) are exempt.
- Quality gates enforce: whitespace/file checks, secret scanning, docs lint, format/lint, type checks, and tests through the project Makefile/CI contract
- CI runs a dedicated docs-quality job through `make docs-lint`. Local pre-commit runs Vale as an error gate and offline link checks when those tools are installed.

---

## Git History

The public repository was re-initialized at the open-source release boundary, so `git log` on `main` starts from a single squashed commit. Pre-release development used Conventional Commits and the `Teach-back:` trailer; that history is not exposed publicly. Going forward, every commit on `main` follows the conventions in the next section, and `harness/check-teachback.sh` enforces the trailer for non-trivial commit types via the `commit-msg` hook (type lists: `skills/git/SKILL.md` § Teach-back Trailer).

If you are evaluating the project against the commit conventions, look at PR commit history and the CI `commit-hygiene` job: which runs the same `harness/check-teachback.sh` on every non-merge commit a PR adds: rather than the squashed `main` log.

---

## Commit Conventions

Use [Conventional Commits](https://www.conventionalcommits.org/):

```text
<type>(scope): <description>
```

**Types:**

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `test` | Test additions or fixes |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Build, CI, tooling changes |

**Examples:**

```text
docs: update security conventions for personally identifiable information logging
feat(agents): add architecture detection to slice-planner
fix(cli): handle missing target directory gracefully
test(cli): add coverage for --disable all edge case
feat(languages): add Go language guide
```

---

## Pull Requests

1. Keep PRs focused: one logical change per PR
2. Write a clear title (under 70 characters) and description
3. Reference related issues if applicable
4. Ensure CI passes before requesting review
5. If the PR removes, renames, or repurposes a covered surface (CLI flag, agent ID, config key, KB path, deployed file), follow [`docs/deprecation-policy.md`](docs/deprecation-policy.md) § Deprecation Cycle: do not skip the cycle without an ADR justifying the skip
6. If the PR implements an accepted RFC, link the RFC number in the PR body (`Implements RFC-NNNN`)

**PR description template:**

```markdown
## Summary
- What changed and why

## Test plan
- How to verify the change works
```

---

## Adding a New Language

1. Create `knowledge-base/languages/<language>.md`: conventions, tooling, formatting
2. Create `knowledge-base/languages/testing-<language>.md`: test runner, fixtures, examples
3. Add a row to `knowledge-base/INDEX.md` for both new files
4. Add the maintained language files to `LANGUAGE_FILES` in `src/deploy_ai_playbook/paths.py` if `ai-playbook deploy --language <language>` should include them
5. Update agent language detection tables where applicable (`xp-pair-programmer`, `slice-planner`)
6. Run tests to verify agent contracts and CLI language filtering still pass

---

## Adding a New Agent

1. Create `agents/<name>.agent.md`: include a `Tier-aware ceremony` table
2. Use a professional frontmatter `name:` and `description:`; keep the stable `id:` aligned with the filename and command name
3. Avoid casual contractions and vague phrases in maintained prose. Vale enforces the shared Playbook rules in `.vale/styles/Playbook/`.
4. Create `commands/<name>.md` as a slash command entry point
5. Create eval input: `evals/<name>-input.md`
6. Create a schema-backed rubric at `evals/rubrics/<name>.json` and a matching human-readable contract at `evals/<name>-expected.md`
7. Add an eval baseline sample under `evals/samples/<name>.md` if it is a standard shipped agent
8. Add the agent to the pipeline diagram in `README.md`
9. Add a row to `CLAUDE.md § Workflow` routing table
10. Run `uv run ai-playbook list` and `uv run python evals/run_eval.py list-agents` to confirm CLI and eval discovery
11. Run `vale agents/<name>.agent.md`, `uv run pytest tests/ -v`, `uv run python evals/run_eval.py check-structure`, and `uv run python evals/run_eval.py calibrate`: Vale, contract, and eval tests will catch drift

The standard agent registry is derived from `agents/*.agent.md` through `standard_agent_names()`. Do not add a second manual agent list for tests or workflows.

---

## Changing a Tool or Service

The playbook keeps tool changes isolated: **only one file needs updating** when you switch a tool:

| You change | Update this file |
|---|---|
| Feature flag provider (e.g. LaunchDarkly → Datadog) | `knowledge-base/feature-flags.md` |
| Logging / observability platform | `knowledge-base/observability.md` |
<!-- vale Google.WordList = NO -->
| Cloud provider or infrastructure approach | New Architectural Decision Record (ADR) under `docs/adr/` |
<!-- vale Google.WordList = YES -->
| Language or test framework | `knowledge-base/languages/<lang>.md` |

After updating, redeploy to all projects:

```bash
ai-playbook deploy --agent all --tool claude
```

---

## File Guidelines

**Each file should:**

- Focus on one topic: one file, one concern
- Be skimmable: headers, lists, tables
- Cross-reference related files (never duplicate content)
- Include concrete examples, not abstract principles

**Universal files (`knowledge-base/*.md`):**

- Language-agnostic: no Python/TypeScript/Go specific syntax
- Link to `languages/` for anything language-specific

**Avoid:**

- Duplicating content across files: link instead
- Implementation details that change frequently
- Overly general advice that applies to all software everywhere
- Template notes and motivational text: agents need instructions, not persuasion

**Token budget:**
The full playbook deploys ~23,000 words (~30,000 tokens) per session. Every word costs context window space. When adding content, identify what to trim or consolidate. Run `wc -w` on your changes.

---

## Maintenance

**Monthly:**

- Review all knowledge base files for accuracy
- Remove outdated guidance
- Add learnings from recent work

**When onboarding new contributors:**

- Read the entire knowledge base: questions reveal gaps
- After the first week, propose at least one KB improvement

**When changing direction:**

- Mark superseded ADRs in `docs/adr/` (update status, link to new ADR)
- Update affected files
- Add an ADR explaining the change

---

## Questions?

Open an [issue](https://github.com/meenumathew/ai-playbook/issues) or start a [discussion](https://github.com/meenumathew/ai-playbook/discussions).
