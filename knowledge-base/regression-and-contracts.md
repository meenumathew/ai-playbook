---
id: regression-and-contracts
size: medium
tldr: Validate existing behavior and contracts before and after changes. Validate code generation for completeness. Scope changes trigger regression checks.
load_when: plan changes, scope changes, code generation, OpenAPI, protobuf, GraphQL, migrations, API breaking change, contract change, behavior regression
audience: xp-pair-programmer, diff-reviewer
canonical_for: regression testing, contract preservation, code generation validation, UFX-2140 pattern
cross_refs: testing.md, testing-techniques.md, debugging.md, quality-gates.md, CLAUDE.md § Shared Rules
verified: 2026-06-10
---

# Regression & Contract Validation

Prevent plan-driven execution from masking quality debt. This file covers three critical gates:

1. **Existing behavior validation**: before implementation starts
2. **Regression detection**: during implementation
3. **Contract preservation**: for generated outputs and exported interfaces

---

## Agent Use

- **Read first:** Validate Existing Behavior, Regression Detection, Code Generation Validation.
- **Load deeper only on trigger:** Contract Preservation, The UFX-2140 Failure Pattern.

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
| 2 | **For code generators:** run the generator on current code. Validate output completeness: |
| |: OpenAPI: all endpoints documented? All real response statuses present (not just happy-path)? |
| |: Protobuf / GraphQL: all message types / fields present? No aliases or experimental fields missing? |
| |: DB migrations: schema matches current models? Foreign keys and constraints present? |
| |: If gaps found, log them in plan's `## Discovered` section with priority. Do not proceed until you understand the gaps. |
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
# Baseline (before first slice)
make test PYTEST_ARGS="--junitxml=baseline.xml" || true

# After slice completion
make test PYTEST_ARGS="--junitxml=slice.xml" || true
# Diff per-test outcomes (name + status), not the summary line
for f in baseline slice; do
  python -c "import xml.etree.ElementTree as ET;\
[print(tc.get('classname'), tc.get('name'), 'FAIL' if tc.find('failure') is not None else 'PASS')\
 for tc in ET.parse('$f.xml').iter('testcase')]" | sort > "$f.txt"
done
diff baseline.txt slice.txt && echo OK || { echo "REGRESSION: per-test outcomes changed"; exit 1; }
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

**Incomplete generator = Must Fix.** Log the gap in commit message and plan the fix as a separate story.

```text
// Example commit message
feat(openapi): add payment webhook endpoints

Generated OpenAPI spec now includes POST /payments/webhook.
Known limitations: error responses (4xx, 5xx) not yet included in spec.
See [PLAN-123] for OpenAPI completeness task.

Co-authored-by: Copilot <...>
```

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

## The UFX-2140 Failure Pattern

**What went wrong:**

1. OpenAPI generation added; spec had gaps (missing error responses)
2. Spec gaps not validated at impl time: assumed "plan says add these AC, so add them"
3. Implementation followed plan, added new response types
4. But OpenAPI spec still incomplete: new response types missing from spec
5. Quality degraded: contract is now inaccurate

**How to prevent it:**

- At pre-flight (xp-pair-programmer § 8): *"Validate OpenAPI completeness on main. Gaps found? Document in Discovered."*
- In diff-reviewer (step 2 regression check): *"OpenAPI spec changed? Verify all real status codes present."*
- At merge (release-captain): check Definition of Done § Contracts: "All exported contracts validated for completeness"

---

## See Also

- `testing-techniques.md` § Contract Testing: consumer-driven contracts (Pact) as the automated form of § Contract Preservation
- `testing.md` § Test Quality Rules: ensure regression tests are isolation-clean
- `debugging.md` § Iron Law: root cause before fixing
- `quality-gates.md`: gate definitions; add "no regression" and "contract preservation" to your DoD
- `CLAUDE.md` § Shared Rules: verification discipline
