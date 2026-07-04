---
id: languages-testing-<lang>
size: <small|medium|large>
tldr: '<one-sentence: e.g. "go test + testify + mockgen; fixtures via t.Run subtests; mock at service boundary; extends testing.md">'
load_when: <runner>, <test keywords>, <mock library>, <coverage tool>
audience: all
canonical_for: <runner> test runner, <runner> fixtures, <runner> mocking, <runner> parametrize, <runner> exception testing
cross_refs: testing.md, testing-techniques.md, languages/<lang>.md
verified: <YYYY-MM-DD>
---

<!-- When seeding to knowledge-base/languages/testing-<lang>.md, fill in the frontmatter above and delete this comment. -->

# Testing: <Language>

> Copy to `knowledge-base/languages/testing-<lang>.md`, replace all `<…>` placeholders, and delete non-applicable sections. See `knowledge-base/languages/testing-python.md` for a full example.

---

## Test Runner

**Required packages:**

```<lang>
// Minimal test config showing runner, coverage, and any async setup
```

```bash
<run-once command>
<run-with-coverage command>
```

---

## File Conventions

| File type | Convention | Example |
|-----------|-----------|---------|
| Unit test | `<pattern>` next to source | `<example>` |
| Integration test | `<pattern>` | `<example>` |
| Test factory / builder | `<pattern>` | `<example>` |

---

## Test Structure

<Describe/context grouping convention and the test naming pattern: `test_<what>_<condition>` or equivalent>

```<lang>
// Minimal test showing describe/group and single-behaviour test
```

---

## Mocking

<Preferred mocking approach: dependency injection over framework-level mocking where possible>

```<lang>
// Preferred: inject a mock/stub through the constructor or function parameter
// Avoid: module-level patching or global mock registries unless DI is impossible
```

| Banned / discouraged | Use instead | Reason |
|---|---|---|
| `<legacy or discouraged mock API>` | `<preferred API>` | `<rationale>` |

**Rules:** Never mock the type under test. Reset mocks before each test. Use patching only when DI is impossible.

---

## Test Factories / Fixtures

Avoid complex inline construction; use factory functions or fixture helpers with overrides:

```<lang>
// Factory function returning a valid test object with sensible defaults
// showing how to apply partial overrides
```

---

## Parametrised Tests

```<lang>
// Parametrised test showing the table-of-inputs pattern
```

---

## Exception Testing

```<lang>
// Assert that a specific exception type (and message, if important) is raised
```

---

## Async Tests

```<lang>
// Minimal async test showing the await / async setup pattern
// Async exception assertion pattern
```

**Rules:** Always await: unawaited coroutines fail silently. Use the async-aware mock type, not the sync mock, for async dependencies.

---

## Coverage

Coverage targets: `testing.md` § Coverage Targets. Run: `<coverage command>`.
