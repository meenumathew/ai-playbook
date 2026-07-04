# How To Enforce Quality Gates

## Goal

Set up mechanical enforcement so the system checks quality rules automatically on every commit: not just documents them.

## Prerequisites

- AI Playbook deployed in your project.
- Starter harness deployed (`Makefile`, `.pre-commit-config.yaml`, CI workflow, security-scan workflow `.github/workflows/security.yml` with weekly secret and dependency scans, teach-back hook, and telemetry files are copied by `ai-playbook deploy` unless `--no-harness` is passed; Claude deploys also merge the telemetry Stop hook into `.claude/settings.json`).
- Project toolchain installed (for example: uv for Python, the Go toolchain, Cargo, npm, Maven, or Gradle).

## Steps

### 1. Configure the Makefile Contract

Agents and CI invoke a stable set of Make targets so the playbook stays language-neutral:

```bash
make format
make format-check
make lint
make typecheck
make test
make quality
```

The starter `Makefile` auto-detects common stacks. If your project already has a `Makefile`, `ai-playbook deploy` will not overwrite it: add these targets yourself, pointing them at your existing scripts.

`docs-lint` is this repository's documentation gate, not part of the language-neutral starter `Makefile`. Add it to adopter projects when maintained documentation needs its own lint target.

| Stack | Target internals can call |
|-------|---------------------------|
| Python | `uv run ruff`, `uv run pyright`, `uv run pytest` |
| Go | `gofmt`, `go vet`, `golangci-lint`, `go test ./...` |
| Rust | `cargo fmt`, `cargo clippy`, `cargo test` |
| JavaScript / TypeScript | `npm run format`, `npm run lint`, `npm run typecheck`, `npm test` |
| Java / Kotlin | Maven or Gradle tasks |

### 2. Install Local Hooks

```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

The second command is required for the teach-back trailer hook (`harness/check-teachback.sh`), which runs at the `commit-msg` stage. Without it, the hook is silently skipped on every commit. `ai-playbook doctor` warns when the config is present but the `commit-msg` stage is not installed.

The deployed `.pre-commit-config.yaml` is intentionally fast and language-neutral:

| Hook | Catches |
|------|---------|
| `detect-private-key` | SSH keys and PEM files staged accidentally |
| `gitleaks` | API keys, tokens, passwords |
| YAML / TOML checks | Broken config files |
| Whitespace and EOF checks | Noisy diffs |

Teams that prefer lefthook or husky can use them instead. Keep the same Make targets underneath so agents and CI share one contract.

`pre-commit` itself runs on Python. Non-Python teams can install it for these universal checks alone, or replace the local hook layer with lefthook or husky and keep the Make targets and CI unchanged.

### 3. Set the Quality Tier

In your project's `CLAUDE.md`:

```markdown
quality-tier: production
```

- **production**: full TDD, complete Definition of Done, mandatory security checks
- **prototype**: lighter ceremony, save-and-continue instead of approval gates

### 4. Configure Project-Specific Gates

Edit `knowledge-base/quality-gates.md` (seeded from `templates/quality-gates-template.md` on first use):

- Set the test command (`pytest`, `npm test`, `go test ./...`, ...).
- Set coverage thresholds intentionally: branch coverage above line coverage.
- List required checks for your stack.

### 5. Use the Teach-Back Gate

Before committing non-trivial code, confirm you can explain:

1. **What** the code does
2. **Where** to debug it if something breaks
3. **How** it would change if requirements shifted

If you cannot pass the teach-back, do not commit. Ask the agent to explain or simplify.

Useful prompt:

```text
Before shipping, give me a context briefing: explain what changed, why, where to debug it, and how we know it works.
```

### 6. Write Commit Rationale

Every commit body must explain *why* you chose this approach: not just *what* changed. For non-trivial code commits, end the body with the enforced `Teach-back:` trailer.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Make target missing | Existing project `Makefile` was not overwritten | Add `format`, `lint`, `typecheck`, `test`, and `quality` targets |
| Docs lint missing | Repository docs are not covered by the local gate | Add `docs-lint` and include it in `quality` |
| Pre-commit not running | Hooks not installed | `pre-commit install` |
| Hook fails but the code is correct | Stale hook config after a playbook update | `ai-playbook deploy --agent all --tool claude` to refresh |
| Agent skips quality checks | Quality tier set to `prototype` | Change to `production` in `CLAUDE.md` |
| Language tool missing | Toolchain not installed locally | Install the project toolchain, or run the same Make target in CI |

## Related

- [Architecture § Harness Engineering](../architecture.md#harness-engineering): the three-layer enforcement model
- [CLI Reference § Deploy](../cli-reference.md#deploy-agents): `--no-harness` flag
- [Doc Linting](../../knowledge-base/doc-linting.md): Vale rules, markdownlint config, adding custom rules
