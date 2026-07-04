---
id: testing
size: medium
tldr: TDD vertical (RED→GREEN→REFACTOR); AC coverage; test_<what>_<condition> naming; mock at service boundary.
load_when: test, TDD, AC coverage, retrofit tests, weak test, test quality, characterization test, test doubles
audience: all
canonical_for: TDD discipline, test naming convention, AC standards, test quality rules, retrofitting tests
cross_refs: testing-techniques.md, languages/testing-python.md, debugging.md, feature-flags.md
verified: 2026-05-19
---

# Testing Rules

Language-specific testing: `languages/testing-<lang>.md`.
Optional techniques: `testing-techniques.md`.

## Agent Use

- **Read first:** TDD Discipline, Choose The Testing Mode, Acceptance Test (AT) Standards, Test Quality Rules.
- **Load deeper only on trigger:** mutation, property-based, contract, async/event-driven, Python async/time/http/testcontainers/xdist techniques: use `testing-techniques.md`.

---

## TDD Discipline: Vertical, Not Horizontal

One test at a time: **RED -> GREEN -> REFACTOR**.

- No production code without a failing test.
- No more test code than is sufficient to fail.
- No more production code than is sufficient to pass.
- A test that cannot fail is not a test; confirm RED before GREEN.
- Do not write all tests first. Bulk test writing creates imagined tests and weak assertions.

---

## Choose The Testing Mode

Use the lightest test strategy that protects the change.

| Work type | Test strategy |
|---|---|
| Story/plan behaviour with AC | One failing AT per AC, then inner unit/service TDD until the AT passes |
| Bug fix | Regression test first at the smallest useful boundary |
| Refactor | Run baseline tests, refactor, rerun same tests; add characterization tests only when coverage is missing |
| Existing untested code | Characterization tests may pass immediately; capture current behaviour before changing it |
| Docs/prompt/format-only | No invented tests; validate with docs/lint/search/evals as relevant |

---

## Acceptance Test (AT) Standards

- One AT per acceptance criterion.
- Name: `test_ac_<what>_<condition>`.
- Location: `tests/acceptance/`, organized by business capability.
- Runs against the real public entry point: HTTP route, CLI command, message handler, component render.
- Use fakes/in-memory adapters at external boundaries to keep ATs fast.
- New-behaviour ATs should fail before coding starts. If one passes immediately, verify whether behaviour already exists or the test is too weak.

---

## Test Quality Rules

Non-negotiable. Every test xp-pair-programmer writes and diff-reviewer checks must pass these:

1. **Test behaviour, not implementation**: assert return values, raised exceptions, state changes, emitted events, or user-visible output. Never assert private state or internal call order.
2. **One behaviour per test**: if the name needs "and", split it.
3. **Named `test_<what>_<condition>`**: e.g. `test_token_expires_after_15_minutes`.
4. **Arrange-Act-Assert**: setup, execute, verify. Add AAA comments only when structure is not obvious.
5. **Unit tests have no I/O**: no DB, filesystem, network, or clock.
6. **Test independence**: no shared mutable state; tests pass in any order.
7. **Keep tests simple**: no `if`, `for`, or `while` in the test body; use parametrized tests for input matrices.

The classic **FIRST** mnemonic maps here: Fast (rule 5), Independent (rule 6), Repeatable/Self-validating/Timely (rules 1-7).

---

## TDD Fidelity: Anti-Patterns to Flag

Tests must assert on *behaviour*, not *shape*. Coverage and green tests are not evidence that tests are meaningful. xp-pair-programmer rewrites; diff-reviewer flags as **Must Fix**:

| Anti-pattern | What it looks like | Why it fails |
|---|---|---|
| Shape test | `assert isinstance(result, dict)`, `assert result is not None`, `assert x >= 0` with no upper bound | Any correct-shaped return passes: behaviour changes go undetected |
| Error class without message | `pytest.raises(ValueError)` with no `match=` | Wrong error for right reason / right error for wrong reason both pass |
| Behavioural change with no test | `src/` diff adds branch, guard, or logic but no matching assertion added | Logic is unverified |
| Mock asserting only that call occurred | `mock.assert_called()` without `assert_called_with(...)` | Doesn't verify the right inputs were passed |
| Test name asserts X, body asserts Y | `test_rejects_empty_name` with no `ValueError` / no `name` in assertion | Test drifted from intent; coverage is theatre |

Cite the specific assertion line and propose the behaviour-level replacement. Tests must assert on the computed value, observable effect, or error message. For mechanical critical-path verification: `testing-techniques.md` § Mutation Testing.

---

## What Not to Test

- Framework or library code.
- Trivial pass-through code.

Decision line: if swapping implementation without changing behaviour breaks the test, the test is coupled to implementation.

---

## Test Ordering and Completeness

Cover behaviours in this order:

1. Happy path
2. Unhappy paths
3. Edge cases
4. Boundary values
5. Error handling

Every AC needs positive coverage. User-visible failure paths need negative coverage.

---

## Test Doubles

| Type | Use |
|------|-----|
| Stub | Return canned data |
| Mock | Verify side effects at external seams |
| Spy | Wrap real behaviour and record calls |
| Fake | In-memory implementation |

Heuristic: stub queries, mock commands. Domain objects do not need mocks.

### Python-specific: ban on `unittest.mock`

Applies only to Python projects. Never import from `unittest.mock`; use the pytest `mocker` fixture from `pytest-mock`. Details: `languages/testing-python.md` § Mocking.

### Mock at boundaries only

Mock at seams between your code and something you do not control: external APIs, clock, randomness, sometimes filesystem/DB. Do not mock your own classes. If you need to, the module seam is wrong.

---

## Coverage Targets

| Scope | Target |
|-------|--------|
| New and modified code | 80%+ branch coverage |
| Critical paths in `knowledge-base/quality-gates.md` | 100% branch coverage |

Coverage is a floor, not a goal. Branch coverage plus scenario coverage matters more than line coverage.

---

## When Tests Are Hard to Write

Testability is a property of the code. Fix the code, not the test.

| Symptom | Agent action |
|---------|--------------|
| Hard to set up | Extract smaller units |
| Needs DB/API for business logic | Add ports/fakes; move I/O to edges |
| Hidden inputs like env/clock/config | Inject or abstract the dependency |
| Shared globals/singletons | Remove or scope to the test |
| Test longer than production code | Move business rules into pure domain code |

Business logic should be testable with zero I/O.

---

## Test Types Quick Guide

Use this as a balance check, not a doc to memorize:

| Type | Purpose | Default |
|------|---------|---------|
| Unit | Single function/class, no I/O | ~70% of dev pyramid |
| AT | Story AC at public boundary with fakes | ~20% |
| Integration | Real external-service boundary | ~10% |
| E2E / Smoke / Sanity | Deployed system checks | Post-deploy only |

Details and special cases live in `testing-techniques.md`.

---

## Post-Deploy Tests

E2E, smoke, and sanity tests run against a deployed system, not the dev pyramid. Include them in a plan only when the story explicitly creates or modifies post-deploy checks (e.g. release-captain smoke checklist, new health endpoint, new sanity probe). Otherwise classify story tests as `Unit | AT | Integration` and let post-deploy concerns live in `release.md` § Post-Deploy Smoke and `observability.md`.

---

## Retrofitting Tests onto Existing Untested Code

For existing untested code, write characterization tests first. They may pass immediately because they document current behaviour. If they expose a bug, mark it (`# BUG:` / `# UNEXPECTED:`) and handle it as discovered work.

---

## Test-Story Cycle: When the Deliverable Is Tests

For test-stories, coverage is the AC; new behaviour still uses normal TDD.

---

## Test Folder Structure

Default:

```text
tests/
|-- unit/
|-- acceptance/
|-- integration/
|-- fixtures/
`-- helpers/
```
