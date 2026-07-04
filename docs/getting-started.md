# Getting Started

In this tutorial we will install AI Playbook, deploy it into a small demo project, and run a first change. By the end you will have agents working in a repository and a passing test to prove it.

**Time:** about 5 minutes. **Result:** working agent instructions in your project.

## Prerequisites

- Python 3.12 or newer.
- `uv` on PATH. If needed, install it from <https://docs.astral.sh/uv/getting-started/installation/>.
- Git and `make` on PATH.
- Claude Code, GitHub Copilot, Cursor, or Kiro ready when you reach the agent prompt. The shell commands below use `--tool claude`; replace it with your tool if needed.

## 1. Install the CLI

We will install from PyPI using `uv`:

```bash
uv tool install ai-playbook
ai-playbook list
```

`ai-playbook list` prints the eight shipped agents: `story-refiner`, `slice-planner`, `xp-pair-programmer`, `diff-reviewer`, `release-captain`, `incident-responder`, `code-inspector`, and `docs-maintainer`.

## 2. Create a Demo Project

Create a tiny Python project so the rest of the tutorial has real code and tests to change:

```bash
mkdir ai-playbook-demo
cd ai-playbook-demo
git init

cat > pyproject.toml <<'TOML'
[project]
name = "ai-playbook-demo"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[dependency-groups]
dev = [
    "pytest>=9.0.0,<10.0",
    "ruff>=0.15.0,<1.0",
    "pyright>=1.1.350,<2.0",
]

[tool.pytest.ini_options]
pythonpath = ["src"]

[tool.pyright]
include = ["src"]
pythonVersion = "3.12"
TOML

mkdir -p src tests
touch src/__init__.py

cat > src/greet.py <<'PY'
def greet(name: str) -> str:
    return f"Hello, {name}"
PY

cat > tests/test_greet.py <<'PY'
from greet import greet


def test_greet_returns_name():
    assert greet("Ada") == "Hello, Ada"
PY

uv run pytest -q
```

## 3. Deploy Into the Demo Project

Run `init` once, then deploy the playbook:

```bash
ai-playbook init
ai-playbook deploy --agent all --tool claude
```

`init` scaffolds the six artifact directories and a starter `.ai-playbook.toml`; it is idempotent and never overwrites existing files.

Deploy copies agents, the knowledge base, skills, templates, the rules file (`CLAUDE.md`), the starter harness, and the issue-tracker MCP configuration into your project. Claude deploys also wire the harness telemetry Stop hook so completed sessions append to `.claude/usage.jsonl`.

Decide as a team whether generated artifacts (`stories/`, `plans/`, `research/`, `audits/`, `reviews/`, and `incidents/`) should be committed. Run `ai-playbook artifact-policy local` to add a managed `.gitignore` block for local-only artifacts, or `ai-playbook artifact-policy shared` to remove that managed block when artifacts should be committed or governed manually.

## 4. Set the Quality Tier and Model Tiers

The deployed `CLAUDE.md` defaults to production. Confirm the tier line at the top:

```bash
grep '^quality-tier:' CLAUDE.md
```

`production` enables full TDD and complete gates: the right default for code we plan to keep.

Then add the model-tier mapping so `doctor` can verify the deployment without warnings. Because this demo deploys to Claude, use values Claude Code recognizes (`opus` / `sonnet` / `haiku` / `inherit` or a `claude-*` ID): `deploy` materializes them into each deployed agent's `model:` frontmatter, so advisor agents run on the stronger model and executor agents on the cheaper one automatically. Replace them with your own choices for team use:

```bash
cat >> .ai-playbook.toml <<'TOML'

[model_tiers]
advisor = "opus"
executor = "sonnet"
TOML
```

For non-Claude tools, or values Claude Code does not recognize (for example Ollama identifiers), the mapping is left as the tier name and you map it in your tool's own config.

## 5. Install the Local Hooks

Wire the deployed hooks once per clone:

```bash
uvx pre-commit==4.3.0 install
uvx pre-commit==4.3.0 install --hook-type commit-msg
```

## 6. Make a First Small Change

Open your AI tool in the demo project, then ask `xp-pair-programmer` to add input validation:

```text
Use xp-pair-programmer: Add input validation to greet(name) in src/greet.py.
Reject empty names with ValueError.
```

xp-pair-programmer writes a failing test first:

```python
def test_greet_rejects_empty_name():
    with pytest.raises(ValueError):
        greet("")
```

Then it writes the smallest code that makes the test pass:

```python
def greet(name: str) -> str:
    if not name:
        raise ValueError("name must not be empty")
    return f"Hello, {name}"
```

When the test passes, xp-pair-programmer stages the change and asks for confirmation:

```text
Changes staged. Say 'commit' to proceed.
```

Reply `commit`. The change is now in the project history.

## 7. Confirm the Quality Gate

Run the quality contract that ships with the harness:

```bash
make quality
```

A green run confirms format, lint, type check, and tests all pass.

## 8. Confirm Deployment Health

Run the doctor command:

```bash
ai-playbook doctor --tool claude
```

A healthy deployment prints `✓ All healthy: deployment is up to date`.

For CI checks that need an exit code rather than a report, use:

```bash
ai-playbook upgrade-check --tool claude
```

Exit `0` = up to date, `1` = drift detected, `2` = never deployed.

---

## What You Have Achieved

At this point you have:

- [x] CLI installed and working
- [x] A tiny demo project under Git
- [x] Agents deployed into the project
- [x] Quality tier set to `production`
- [x] Model tiers configured
- [x] Local hooks installed
- [x] One test-driven change committed by xp-pair-programmer
- [x] Quality gates passing through `make quality`
- [x] Deployment confirmed healthy

You are ready to use the full workflow path on real work.

## If something went wrong

The five-minute path assumes a normal Unix-ish environment. If a step fails, the symptom usually points at one of these:

| Symptom | Most likely cause | Fix |
|---|---|---|
| `uv: command not found` | `uv` is not installed or not on PATH | Install `uv`, then open a new shell |
| `ai-playbook: command not found` after `uv tool install` | The user-tool bin directory isn't on PATH | Run `uv tool dir --bin` and add the printed path to your shell's PATH |
| `Error: Cannot write to <path>: Permission denied` during deploy | Target dir is read-only or owned by another user | Choose a writable target with `--target-dir <path>` or `chown` the existing one |
| `Error: Unsafe destination ...: refuses to write through symlink` | A symlinked file inside the target tree | Replace the symlink with the real file or pick a different target |
| Deploy completes but `ai-playbook list` still says no agents | You're running from a venv that was left over from a previous install | `uv tool uninstall ai-playbook && uv tool install ai-playbook` |
| `make quality` fails with `ruff`, `pyright`, or `pytest` missing | The target project has no Python tool dependencies | Add the tools to your project dependencies, or override commands in `Makefile.local` |
| `pre-commit install` complains "no .git directory" | The command ran in a non-repo directory | `git init`, then re-run the two `uvx pre-commit==4.3.0 install` commands |
| `ai-playbook doctor` reports missing model tiers | The `[model_tiers]` table was skipped | Add the table from step 4 to `.ai-playbook.toml` |
| `ai-playbook doctor` reports a missing commit-msg hook | The hook install step was skipped | Run `uvx pre-commit==4.3.0 install --hook-type commit-msg` |
| `ai-playbook doctor` reports stale agents immediately after deploy | Two CLI versions on PATH disagree on bundled data | Confirm with `which -a ai-playbook` and uninstall the older one |
| Deploy interrupted partway (Ctrl-C, network blip) | Half-written state | Re-run the same `ai-playbook deploy` command: it's idempotent and will reconcile; or `ai-playbook rollback --tool <tool> --yes` to revert to the last good backup |

If none of these match, run `ai-playbook doctor --tool <tool> --json` and read the output: it lists every issue with a one-line fix command. If that doesn't help, [open an issue](https://github.com/meenumathew/ai-playbook/issues) with the doctor JSON attached.

## Next Steps

| To... | Read |
|-------|------|
| Learn the day-to-day workflow | [User Guide](user-guide.md) |
| Invoke a specific agent | [How To Invoke Agents](how-to/invoke-agents.md) |
| See every command and flag | [CLI Reference](cli-reference.md) |
| Understand the design | [Architecture](architecture.md) |
| Check known limitations | [Known Limitations](limitations.md) |
