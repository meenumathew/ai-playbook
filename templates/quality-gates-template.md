---
id: quality-gates
size: medium
tldr: '<one-sentence: e.g. "Project gates: format/lint/typecheck/test/coverage/security; critical paths in src/auth and src/payment">'
load_when: quality gate, coverage threshold, critical path, mutation score, make quality, make test, CI gate
audience: all
canonical_for: project-specific gate commands, coverage policy, critical path registry, mutation testing policy
cross_refs: testing.md, testing-techniques.md, security.md, style-guide.md
verified: <YYYY-MM-DD>
---

<!-- When seeding to knowledge-base/quality-gates.md, fill in the frontmatter above and delete this comment. -->

# Quality Gates

Project-specific verification gates. Keep commands executable and review-only rules explicit.

---

## Gate Summary

| # | Gate | Command / Check | Pass condition | Required when |
|---|------|-----------------|----------------|---------------|
| 1 | Format | `[format command]` | Exit 0, no changed files | Every code change |
| 2 | Lint | `[lint command]` | Exit 0, zero blocking issues | Every code change |
| 3 | Type check | `[type-check command]` | Exit 0, zero type errors | Typed code changes |
| 4 | Tests | `[test command]` | All relevant tests pass | Every behaviour change |
| 5 | Coverage | `[coverage command]` | Meets project threshold | Code changes |
| 6 | Security scan | `[security command]` | No new critical/high findings | Dependency, auth, input, or release changes |

---

## Coverage Policy

<!-- Record only project-specific thresholds here. -->

| Scope | Target |
|-------|--------|
| New/modified code | `[e.g. 80%+ branch coverage]` |
| Critical paths | `[e.g. 100% branch coverage]` |
| Whole repository | `[project-specific threshold]` |

---

## Critical Paths

<!-- Keep narrow: only high-risk paths. -->

| Area | File paths | Why critical | Required evidence |
|------|------------|--------------|-------------------|
| `[auth]` | `[src/auth/**]` | `[authorisation decisions]` | `100% branch coverage; mutation score must not regress` |
| `[payments]` | `[src/payment/**]` | `[money movement]` | `100% branch coverage; mutation score must not regress` |

---

## Mutation Testing Policy

| Trigger | Command / Check | Pass condition | Required when |
|---------|-----------------|----------------|---------------|
| PR touches critical-path files | `[scoped mutation command, e.g. uv run mutmut run --paths-to-mutate src/auth]` | Score does not regress from baseline | Critical-path file changes |
| Scheduled run | `[full mutation command]` | Report produced and reviewed | Weekly or per sprint |
| Local/on-demand | `[developer command]` | Surviving mutants reviewed | Before marking risky work Done |

Baseline scores:

| Area | Baseline mutation score | Last reviewed |
|------|-------------------------|---------------|
| `[auth]` | `[e.g. 82%]` | `[YYYY-MM-DD]` |

---

## Behaviour Coverage Checklist

Before claiming done, verify the changed behaviour covers all five behaviour classes in `testing.md` § Test Ordering and Completeness (happy, unhappy, edge, boundary, error handling): positive coverage for every AC, negative coverage for user-visible failure paths.

---

## Review-Only Gates

Some gates are non-command checks and must be reviewed manually.

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

Bypass and suppression rules (`--no-verify`, blanket suppressions, skips): `CLAUDE.md` § Quality Gates and `style-guide.md` § No Suppression Without Justification.
