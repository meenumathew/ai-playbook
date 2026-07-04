---
id: languages-<lang>
size: <small|medium|large>
tldr: '<one-sentence: e.g. "Go 1.22+; stdlib slog; golangci-lint; envconfig; extends style-guide.md and testing.md">'
load_when: <lang>, <stdlib keywords>, <tooling keywords>, <framework keywords>
audience: all
canonical_for: <Lang> language version, <Lang> application structure, <Lang> tooling, <Lang> error handling
cross_refs: style-guide.md, testing.md, languages/testing-<lang>.md
verified: <YYYY-MM-DD>
---

<!-- When seeding to knowledge-base/languages/<lang>.md, fill in the frontmatter above and delete this comment. -->

# <Language> Conventions

> Copy to `knowledge-base/languages/<lang>.md`, replace all `<…>` placeholders, and delete non-applicable sections. See `knowledge-base/languages/python.md` for a full example.

---

## Language Version

<Minimum supported version and any runtime/compiler notes: e.g. "Go 1.22+", "Java 21 LTS", "Rust stable">

---

## Application Structure

```text
<project-root>/
  <source-dir>/         ← production code
    <package>/
      <entry-point>     ← thin, delegates to domain
      domain/
      services/
  tests/
  <build-config>        ← e.g. go.mod, pom.xml, Cargo.toml
```

- <Note on src layout or module conventions>
- <Note on CLI / entry-point discipline>

---

## Code Style

| Rule | Agent action |
|------|-------------|
| <Naming convention> | <Enforcement: linter, review flag> |
| <Type annotation / generics rule> | <When required, what form> |
| <Composition / inheritance guideline> | <What to favour> |
| <Error style: exceptions vs result types vs error values> | <Flag deviations in review> |
| No debug output in production | Use the logger |

---

## Documentation Comments

Required on public functions/methods/types. Optional on private helpers with self-explanatory signatures and on test functions.

```<lang>
// Example of a well-documented public function
// showing parameters, return value, and error/exception contract
```

---

## Imports / Modules

| Rule | Agent action |
|------|-------------|
| <Import ordering convention> | <Blank-line groups or tool-enforced> |
| <Preferred import form: module vs symbol> | <Exception cases> |
| <Circular import / dependency rule> | <How to detect and resolve> |

---

## Environment Variables / Configuration

```<lang>
// Fail-fast pattern for required config
// Explicit-default pattern for optional config
```

---

## Formatting

| Setting | Value |
|---------|-------|
| Line length | <value and config location> |
| Indentation | <spaces / tabs, count> |
| Formatter | `<tool>`: run after every GREEN and REFACTOR step |

---

## Tooling

| Tool | Purpose | Config |
|------|---------|--------|
| `<formatter>` | Formatting | `<config file>` |
| `<linter>` | Linting | `<config file>` |
| `<type-checker>` | Static type checking | `<config file>` |
| `<test-runner>` | Tests: see `testing-<lang>.md` | `<config file>` |

Pre-commit / pre-push command:

```bash
<lint-command> && <typecheck-command> && <test-command>
```

---

## Logging

<Logging idiom for this language: logger initialisation, lazy vs eager evaluation, structured fields>

Use `<logger.exception equivalent>` for caught errors. See `observability.md` for structured logging rules.

---

## Type System

| Rule | Agent action |
|------|-------------|
| <Strictness setting> | <Enforced by tool> |
| <Null / option handling> | <Pattern to use> |
| <Generics / parametric types> | <When to use> |
| <Structural vs nominal typing> | <Preference and rationale> |

---

## Error Handling

<How errors propagate in this language: exceptions, result types, or error return values>

| Rule | Agent action |
|------|-------------|
| <Error propagation rule> | <Domain exceptions / typed errors> |
| <Error wrapping / chaining rule> | <Preserve root cause> |
| <Logging rule> | <Never expose internals to callers> |

---

## Input Validation

| Rule | Agent action |
|------|-------------|
| <Validation library / approach> | <Where validation runs: boundary only> |
| <Unknown-field handling> | <Reject or ignore> |
| <Constraint annotations> | <min/max, patterns, required> |

---

## Async Patterns

| Rule | Agent action |
|------|-------------|
| <Async model: coroutines / goroutines / futures / green threads> | <When to use> |
| <Concurrent execution idiom> | <Avoid sequential await in a loop> |
| <Timeout requirement> | <All external calls must have a timeout> |
| <Sync/async mixing rule> | <How to enforce layer boundaries> |
