---
id: regression-and-contracts
size: medium
tldr: Validate existing behavior and contracts before and after changes. Validate code generation for completeness. Scope changes trigger regression checks.
load_when: plan changes, scope changes, code generation, OpenAPI, protobuf, GraphQL, migrations, API breaking change, contract change, behavior regression
audience: xp-pair-programmer, diff-reviewer, slice-planner, release-captain
canonical_for: regression testing, contract preservation, code generation validation, migration safety, UFX-2140 pattern
cross_refs: testing.md, testing-techniques.md, debugging.md, quality-gates.md, CLAUDE.md § Shared Rules
verified: 2026-07-17
---

# Regression & Contract Validation

Prevent plan-driven execution from masking quality debt. This file covers three critical gates:

1. **Existing behavior validation**: before implementation starts
2. **Regression detection**: during implementation
3. **Contract preservation**: for generated outputs and exported interfaces

---

## Agent Use

- **Read first:** Validate Existing Behavior, Regression Detection, Code Generation Validation.
- **Load deeper only on trigger:** Contract Preservation, Migration Safety.

| Agent | Usage |
|-------|-------|
| **xp-pair-programmer** | Run § Validate Existing Behavior **before starting any task that touches code generation or modifies a contract**. On each slice, re-run § Regression Detection. Log findings in plan's `## Discovered`. |
| **diff-reviewer** | Run § Regression Detection if scope changed from original AC. Run § Code Generation Validation if PR includes generators/formatters. Log as **Must Fix** if gaps found. |

---

## Validate Existing Behavior

**Triggered when:** plan includes code generation, external contracts, or scope changes mid-story.

**Goal:** establish baseline before writing code.

| Step | Action |
|------|--------|
| 1 | On `main` branch, run the full test suite. Record: pass/fail, execution time, test count. |
| 2 | **For code generators:** run the generator on current code and validate output completeness per § Code Generation Validation. Log gaps in plan's `## Discovered` with priority; do not proceed until you understand them. |
| 3 | **For API or contract changes:** read the current contract definition (OpenAPI spec, protobuf schema, type definitions). Document exported fields and client dependencies. Identify backward-compatibility constraints. |

**Example.** UFX-2140 failure mode: should have caught at this step:

```text
## Discovered

- OpenAPI generator on main branch: 42 endpoints documented.
  Incomplete: error responses missing. PaymentError (400, 402) not in spec.
  Impact: implementation of new AC will run against incomplete spec.
  Action: [Add validation test for error responses to OpenAPI test suite before implementing AC]
```

---

## Regression Detection

**Triggered when:** plan changes scope, or after each TDD slice in xp-pair-programmer.

**Goal:** catch behavior changes before they accumulate.

| Trigger | Action |
|---------|--------|
| **Scope change mid-story** | Baseline test suite on `main`. Run full suite on branch. Diff: any tests changed from pass → fail, skip → pass, or skip → fail? If yes: investigate until you understand the regression before continuing. |
| **Each TDD slice completion** (xp-pair-programmer only) | After GREEN + REFACTOR, run the affected tests (module + direct dependents); run the full suite before each commit, or lean on CI when the suite is slow (>2–3 min). Compare against baseline. Any new failures? Fix in this slice before moving on. Never carry forward test regressions. |
| **Code generation changes** | After modifying a generator, re-run all generators. Diff the output artifacts. Validate completeness (see § Code Generation Validation) before committing. |

**Bash workflow (xp-pair-programmer use).** Prefer structured results over scraping runner output: emit machine-readable reports (`pytest --junitxml=...`, `go test -json`, `jest --json`) and diff the per-test outcomes: a summary line can stay identical while one test starts failing and another starts passing.

```bash
make test PYTEST_ARGS="--junitxml=baseline.xml" || true   # before first slice
make test PYTEST_ARGS="--junitxml=slice.xml"    || true   # after each slice
# Extract (test name, status) from each report and diff those lines:
# pass→fail and fail→pass can cancel out in the summary counts.
```

---

## Code Generation Validation

**Trigger.** PR includes any generator or formatter (OpenAPI, Protobuf, GraphQL, DB migration, config codegen, WASM bindings).

**Verify before merging:**

| Generated Artifact | Validation | Example |
|---|---|---|
| **OpenAPI spec** | All endpoints present? All real status codes? Error responses included? Authorization headers documented? | UFX-2140: spec had 42 endpoints but no 400/402 error responses. Run a semantic diff (`oasdiff` / `openapi-diff`) of `main` vs. branch: removed operations, responses, or fields indicate incompleteness. |
| **Protobuf / GraphQL schema** | All message types? All fields? Experimental or deprecated? Annotations preserved? Removed protobuf fields `reserved`? | Run a semantic schema diff: `buf breaking` (protobuf), `graphql-inspector diff` (GraphQL). If a field disappeared, investigate: was it deliberately removed (and reserved) or is the generator incomplete? |
| **Database migrations** | Schema matches domain models? Foreign keys present? Indexes on query paths? | Run migration on empty DB, then `\d+ <table>` (psql) or schema inspection: does it match the model? |
| **Type definitions** (TS `.d.ts`, Python stubs, Go interfaces) | All public methods? Correct types? Generic parameters preserved? | Diff against source: any public signature missing from generated types = incorrect generator. Fix before merge. |

**Red flags (Must Fix in review):**

- Generator output is smaller/simpler than previous version without a documented reason
- Generator output omits fields/methods that exist in source code
- Generator output includes experimental/deprecated items marked as stable
- Documentation/comments reference generated artifacts that are incomplete, for example "See OpenAPI spec for all endpoints" when spec is incomplete

**Incomplete generator = Must Fix.** Log the gap in the commit body ("Known limitations: error responses (4xx, 5xx) not yet in spec; completeness task in [PLAN-123]") and plan the fix as a separate story.

---

## Contract Preservation

**Trigger.** PR modifies something other code depends on (API response, message format, schema, exported type, library interface, feature flag behavior).

For service-to-service contracts, the standard mechanism for catching these breaks automatically is consumer-driven contract testing: see `testing-techniques.md` § Contract Testing. The table below is the manual review checklist when no contract suite exists yet.

| Contract Type | Preservation Rule | Validation |
|---|---|---|
| **API response shape** | Removing fields = breaking. Adding optional fields = backward-compat. | Before-after test: old client can consume new response. If breaking, bump major version and document migration. |
| **Message format** (Protobuf, JSON RPC, async events) | Removing fields = breaking. JSON: renaming keys = breaking. Protobuf: field *numbers* carry the wire contract: renaming a field is wire-compatible (it still breaks JSON mapping and generated code); removing one requires `reserved` for its number and name, and numbers are never reused. | Run a semantic schema diff (`buf breaking` for protobuf) before and after. If breaking, test both old and new clients in before-after suite. |
| **Database schema** | New columns must be nullable or have defaults. Removing columns breaks queries. | Run migration on populated DB (if possible, use test fixtures). Query still works after? If breaking, include backfill in migration. |
| **Library interface** | New params must be optional or have defaults. Removing functions = breaking. | Type-check imports: `import { deletedFunc } from lib` should fail on new version. If not, you missed a deprecation cycle. |
| **Feature flag behavior** (flip default, remove flag) | Removing a flag = must wait for deprecation cycle. | Both states tested? Code path for flag=true AND flag=false still executable? |

**If claiming backward-compatible.**

```text
BEFORE: GET /orders returns { id, total }
AFTER:  GET /orders returns { id, total, tax, shipping }

Claim: Backward-compatible (added optional fields).
Validation: Test "old client can consume new response" passes.
```

**If breaking:**

```text
BREAKING: GET /orders no longer returns 'total' field. Use 'tax + shipping' instead.
Bump: major version
Migration: See [URL] for client upgrade guide.
```

---

## Migration Safety

A data or schema migration is the highest-blast-radius change a slice can carry: it runs once, against live data, and a bad one is not a simple rollback. Plan it as reversible steps, not one destructive edit.

**Expand → migrate → contract (never rename in place).** Split every schema change into phases that each keep old and new readers/writers working:

1. **Expand:** add the new column/table/field; deploy code that writes both old and new but still reads old. Nothing breaks because old shape is untouched.
2. **Migrate:** backfill existing rows into the new shape in batches; switch reads to the new shape once backfill is verified.
3. **Contract:** after a bake period with no old readers, drop the old column/field in a *later* deploy.

Each phase is independently deployable and reversible; a single "rename column + change code" deploy is not.

**Backfill in batches, idempotently.** Never one giant `UPDATE` that locks the table. Batch by key range, make each batch re-runnable (so a mid-backfill failure resumes, not corrupts), and throttle to protect live traffic.

**Reversibility is the plan, not an afterthought.** Every migration step states how to undo it. The expand/contract split exists precisely so that until the contract phase, rollback is a code deploy, not a data restore. Once the contract phase drops data, forward-fix is the only path, so gate it behind a bake period and an explicit go/no-go.

**Decouple migration from deploy.** Run migrations as their own step with their own runbook, not implicitly inside app startup: an app that migrates on boot cannot roll back cleanly (`release.md` § Rollback: do not auto-rollback migrations).

**Verify against real-shaped data.** Test the migration on a production-shaped dataset (volume and edge cases), not a toy fixture: row counts before/after, no silent drops, constraints hold. Pair with a characterization test of the behaviour that reads the migrated data.

**Where it fits.** slice-planner plans the expand/migrate/contract slices when the migration-safety gate fires; release-captain runs the migration on its own step and holds the contract phase behind the bake period.
