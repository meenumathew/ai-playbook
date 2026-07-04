---
id: quality-gates
size: medium
tldr: "Project-specific gates: commands, coverage thresholds, critical paths, mutation policy. Seed file; fill in placeholders before relying on it."
load_when: quality gate, coverage threshold, critical path, mutation score, make quality, make test, CI gate
audience: all
canonical_for: project-specific gate commands, coverage policy, critical path registry, mutation testing policy
cross_refs: testing.md, testing-techniques.md, security.md, style-guide.md
verified: 2026-06-10
---

# Quality Gates

This repo has filled the project-specific commands below. Adopter projects seeded from `templates/quality-gates-template.md` must replace the bracketed placeholders in their own copy before relying on gates.

Project-specific verification gates. Stricter or more specific than the playbook defaults; executable where possible; record review-only rules too.

## Agent Use

- **Read first:** Gate Summary, Coverage Policy, Critical Paths, When a Gate Fails.
- **Load deeper only on trigger:** Mutation Testing Policy when critical-path work is in progress; Review-Only Gates during review.

---

## Per-Language Formatter & Lint Defaults

Use these when Make targets are absent and the project config makes the language unambiguous. Project scripts (`npm run lint`, `make lint`) take precedence when present.

| Language | Formatter + linter |
|---|---|
| Python | `ruff format` + `ruff check --fix` |
| JS/TS | `eslint --fix` + `prettier` |
| Go | `gofmt` + `go vet` |
| Rust | `cargo fmt` + `cargo clippy` |
| Java | project formatter (`spotless`, `google-java-format`) |
| C/C++ | `clang-format` |
| C# | `dotnet format` |

Detection rule: read project config (`pyproject.toml`, `package.json`, `go.mod`, `Cargo.toml`, `pom.xml`, `*.csproj`) before applying any of these: never assume a language. Run formatter and lint immediately after GREEN and after REFACTOR per `CLAUDE.md` § Code Quality. See also `knowledge-base/style-guide.md` for naming, formatting, and suppression rules.

---

## Gate Summary

| # | Gate | Command / Check | Pass condition | Required when |
|---|------|-----------------|----------------|---------------|
| 1 | Format | `make format-check` | Exit 0, no changed files | Every code change |
| 2 | Lint | `make lint` | Exit 0, zero blocking issues | Every code/docs-tooling change |
| 3 | Type check | `make typecheck` | Exit 0, zero type errors | Python source changes |
| 4 | Tests | `make test` or focused `uv run pytest <paths> -q` while iterating | All relevant tests pass | Every behaviour change |
| 5 | Coverage | `make test` (`--cov=src --cov-fail-under=95`) | >=95% branch coverage for `src/` | Source changes |
| 6 | Security scan | CI secret scan + `pip-audit` + Bandit in `.github/workflows/ci.yml`; run the same commands locally for security-sensitive changes | No new critical/high findings | Dependency, auth, input, workflow, or release changes |

---

## Coverage Policy

Coverage is a safety signal, not a goal by itself. Prefer branch coverage and behaviour scenarios over raw line coverage.

| Scope | Target | Rationale |
|-------|--------|-----------|
| New/modified code | Behaviour tests for changed branches and error paths | Branch coverage catches untested else/error paths better than line coverage |
| Critical paths | Focused tests for positive, negative, edge, rollback, and unsafe-input paths; mutation baseline must not regress | Deploy, release, security, and instruction-contract defects are high impact in this repo |
| Whole repository | >=95% branch coverage for `src/` via `make test` | 95% fits *this* repo: deploy/rollback safety, instruction-contract validity, and supply-chain integrity are high-impact. Keep it realistic: improve tests, don't game the metric |

If this project chooses **100% line coverage**, state why here and pair it with behaviour review. 100% line coverage does not prove correctness; tests must still cover positive, negative, edge, and boundary behaviours.

**Adopter projects:** 95% is this repo's target, not a universal law. Set your own threshold from risk: a safety-critical service may justify higher, an early prototype lower: and state the reasoning here the way this file does.

**Legacy codebases:** when the repo-wide number is unreachable, gate on changed lines instead (`diff-cover` over the PR diff, e.g. >=90%). New code stays fully tested without forcing a retrofit of the whole baseline; ratchet the repo-wide threshold up as coverage grows.

---

## Critical Paths

Paths where defects create high user, security, financial, or compliance risk. Keep narrow enough that stronger gates are realistic.

| Area | File paths | Why critical | Required evidence |
|------|------------|--------------|-------------------|
| Deploy and rollback safety | `src/deploy_ai_playbook/cli.py`, `fs.py`, `safety.py`, `backup.py`, `mcp.py`, `telemetry.py` | Writes into adopter repos; defects can overwrite instructions, leak data, or block rollback | Focused deploy/backup/doctor tests; no raw tracebacks; rollback path verified |
| Instruction contracts | `CLAUDE.md`, `agents/`, `skills/`, `knowledge-base/`, `templates/`, `evals/` | These files are the product surface agents execute | Contract tests, pointer tests, eval structure/calibration/sample validation, docs lint |
| Supply chain and release automation | `.github/workflows/`, `harness/`, `pyproject.toml`, `uv.lock`, `mutation-baseline.json` | Release artifacts and CI define adopter trust boundaries | SHA-pinned Actions, secret/dependency/static scans, mutation baseline check |

Do **not** mark every write path as critical. Prefer decision-heavy code around authentication, authorisation, payment, PII, security-sensitive parsing, and irreversible operations.

---

## Mutation Testing Policy

Mutation testing is a quality signal, not a universal PR blocker. Detail in `testing-techniques.md` § Mutation Testing.

| Trigger | Command / Check | Pass condition | Required when |
|---------|-----------------|----------------|---------------|
| PR touches `src/`, `tests/`, or mutation config | `.github/workflows/mutation.yml` (`uv run mutmut run --max-children 4` → export stats → `tools/check-mutation-baseline.py`) | Counts do not exceed `mutation-baseline.json` | Critical-path file changes |
| Scheduled run | Same workflow on weekly schedule | Report produced; baseline check passes | Weekly |
| Local/on-demand | `uv run mutmut run --max-children 4 && uv run mutmut export-cicd-stats && uv run python tools/check-mutation-baseline.py` | Surviving/no-test mutants do not exceed baseline; infrastructure statuses are zero | Before marking risky source changes Done |

Record baseline scores here:

| Area | Baseline mutation score | Last reviewed |
|------|-------------------------|---------------|
| `src/deploy_ai_playbook/` | See `mutation-baseline.json` (`survived <= 0`, `no_tests <= 13`, infrastructure statuses `0`) | 2026-05-28 |

---

## Behaviour Coverage Checklist

Before claiming done, verify the changed behaviour has:

- [ ] Positive path tests for expected success
- [ ] Negative path tests for rejected/failed inputs
- [ ] Edge cases such as empty, null, zero, max, whitespace, or unicode where relevant
- [ ] Boundary cases such as threshold transitions and off-by-one risks
- [ ] Error handling tests for exception type, safe message, and layer translation

---

## Review-Only Gates

Cannot be expressed as a single command: reviewers verify:

| Rule | Verified by |
|------|-------------|
| No hardcoded secrets or credentials | Diff review and secret scanning |
| No raw internal error details in client responses | Security review |
| Structured logging includes useful context and excludes sensitive data | Observability review |
| Architecture dependency direction is preserved | Design review |
| Known limitations and ADRs updated when needed | Documentation review |

---

## When a Gate Fails

| Gate | Agent action |
|------|-------------|
| Format/lint/type/test failure | Fix the underlying issue; do not suppress without justification |
| Coverage below threshold | Add meaningful behaviour tests or delete dead code; do not lower the threshold silently |
| Security scan failure | Treat exploitable findings as Must Fix before approval |
| Tool unavailable | Name the blocker and run the closest smaller verification; do not claim the gate passed |

Never bypass gates with `--no-verify`, blanket `# noqa`, bare `# type: ignore`, or skipped tests without an explicit reason.
