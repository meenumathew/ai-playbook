---
id: testing-techniques
size: large
tldr: Optional testing techniques loaded only on trigger; extends testing.md, never relaxes its rules.
load_when: property-based, mutation, hypothesis, fast-check, contract test, pact, async test, queue, stream, eventual consistency
audience: all
canonical_for: property-based testing, mutation testing, contract testing, async event-driven test patterns
cross_refs: testing.md, languages/testing-python.md
verified: 2026-07-17
---

# Testing Techniques

## Agent Use

- **Read first:** the section matching the trigger.
- **Quality rule:** this file extends `knowledge-base/testing.md`; it never relaxes TDD, AC coverage, or test quality rules.

---

## Property-Based Testing

Let the framework generate inputs to break invariants: strong on edge discovery (boundaries, empty, unicode, ordering) without hand-picking cases. Complements example-based tests; doesn't replace them. Tools: `hypothesis` (Python), `fast-check` (TypeScript). Use on pure domain rules; assert invariants, not specific outputs.

---

## Async and Event-Driven Test Patterns

The playbook does not prescribe event sourcing, CQRS, or saga architecture. It does prescribe how to test async behaviour when a project already uses queues, streams, consumers, or streaming responses.

### Message consumer acceptance tests

Test the **handler boundary**, not the broker. A story AC like "invoice is generated when payment succeeds" should drive a test that passes a representative message to the consumer handler and asserts the observable outcome.

| Do | Avoid |
|----|-------|
| Call the consumer handler directly with a decoded message object | Starting Kafka/Rabbit/SQS for every AT |
| Fake downstream ports: repo, email, payment, publisher | Sleeping for fixed time and hoping the consumer ran |
| Assert emitted events, state changes, or returned ack/nack decision | Asserting only that a mock was called |
| Include idempotency and duplicate-message cases | Testing only the happy path |

Minimum scenarios for a consumer:

- Valid message is processed once
- Duplicate message is ignored or handled idempotently
- Invalid message is rejected or dead-lettered with a safe reason
- Downstream failure retries, nacks, or dead-letters according to policy

### Eventual consistency assertions

When production behaviour is eventually consistent, tests should poll for an observable condition with a tight timeout and useful failure message.

```text
eventually(
  timeout=2s,
  interval=50ms,
  assertion="order projection contains status=paid"
)
```

Rules:

| Rule | Agent action |
|------|-------------|
| Poll for a business condition | Never `sleep(5)`: fixed sleeps create slow, flaky tests |
| Keep timeout short in ATs | Long async waits belong in integration or E2E suites |
| Fail with context | Include last observed state, event id, and correlation id |
| Correlate messages | Every async test message needs a unique id/correlation id |

### Streaming response assertions

For Server-Sent Events, websockets, chunked HTTP, or token streams, assert the stream contract:

| Behaviour | Assertion |
|-----------|-----------|
| Starts correctly | First frame/chunk has expected event type or metadata |
| Emits meaningful data | At least one domain-relevant event appears |
| Preserves order when order matters | Events appear in the expected sequence |
| Terminates or stays open by contract | End marker, close frame, heartbeat, or timeout behaviour is explicit |
| Handles cancellation | Client disconnect cancels upstream work without leaking tasks |

Do not assert every chunk of a non-deterministic stream. Assert invariants, ordering constraints, and final observable result.

### Broker integration tests

Use real broker infrastructure only in integration tests. Verify serialization, topic/queue names, partition/routing keys, ack/nack behaviour, and consumer group configuration. Business rules remain covered by unit/service/AT tests around the handler.

---

## Mutation Testing

Coverage proves tests *ran*. Mutation testing proves they *asserted*. Mechanical defence against TDD-theatre.

### Mental model (always)

After writing a test, mentally flip a condition in the production code it covers: `>` → `>=`, `True` → `False`, remove a guard, return `None`. If no test catches the change, strengthen the assertion or add a scenario before moving on.

### Tools

| Language | Tool |
|---|---|
| Python | `mutmut` (configured in `pyproject.toml § [tool.mutmut]`) |
| Go | `gremlins` (`go-mutesting` is unmaintained) |
| Rust | `cargo-mutants` |
| JS/TS | `stryker` |

The critical-path registry, run triggers, and the CI gate are policy: `quality-gates.md` § Mutation Testing Policy. Technique rule: fail only on regression against a stored baseline, never on absolute score; never run on pre-commit (too slow).

### Running locally

```bash
# mutmut 3.x reads paths_to_mutate from pyproject.toml § [tool.mutmut]
# (the 2.x --paths-to-mutate CLI flag was removed)
uv run mutmut run
uv run mutmut results
uv run mutmut show <id>     # inspect a surviving mutant
```

### Interpreting surviving mutants

| Cause | Fix |
|-------|-----|
| Missing test: behaviour change not exercised | Add a test |
| Weak assertion: test ran but didn't check the right thing | Strengthen the assertion |
| Equivalent mutant: identical behaviour (common: literature reports 10–40% of survivors, in live code too, e.g. `<` vs `<=` on an unreachable boundary) | Confirm no test can distinguish it, then document and suppress |

Never suppress by adding an assertion that just exercises the mutated line without testing behaviour: that re-introduces the very problem mutation testing exists to catch.

---

## Contract Testing

| Aspect | Detail |
|--------|--------|
| **What** | Test the agreed contract (request/response shape and semantics) between services: not the implementation |
| **Tools** | Pact (Python/TypeScript) |
| **Consumer tests** | Run against a mock (fast) |
| **Provider verification** | Run against a real instance (seconds) |
| **When to use** | You own the consumer, provider is a separate service, breaking changes have occurred before |

---

## Language-Specific Techniques

Language-specific applications of these techniques (Python: async pytest, frozen time, HTTP mocking, testcontainers, xdist) live in `languages/testing-<lang>.md`; for Python see `languages/testing-python.md` § Python pytest Techniques.
