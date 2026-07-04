---
id: testing-techniques
size: large
tldr: Optional testing techniques loaded only on trigger; extends testing.md, never relaxes its rules.
load_when: property-based, mutation, hypothesis, fast-check, contract test, pact, async test, queue, stream, eventual consistency, frozen time, httpx, respx, testcontainers, pytest-xdist
audience: all
canonical_for: property-based testing, mutation testing, contract testing, async event-driven test patterns
cross_refs: testing.md, languages/testing-python.md
verified: 2026-05-19
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

Define critical paths in `knowledge-base/quality-gates.md`. Starting points (teams shrink or expand): auth/authorisation, payment/billing, security-sensitive parsing, PII access control. Focus on *decision logic* around irreversible or security-sensitive operations: not every DB write.

### When it runs

| Trigger | Behaviour | Blocks PR? |
|---------|-----------|-----------|
| PR touches a critical-path file | Parallel CI job scoped to changed paths; report-only, regression check decides | Only if score regresses below baseline |
| Weekly scheduled CI run | Full scan, report as artifact | No: advisory |
| Manual / on-demand | Developer runs locally before marking a critical-path story Done | No |

Never on pre-commit (too slow). Never a blocking gate on every PR: teams quietly disable gates they can't meet.

### CI wiring

Run `mutmut` (or equivalent) in a separate workflow triggered by `paths:` matching your critical paths plus a weekly `schedule:`. Fail only on regression against a stored baseline: not on absolute score. Cache the tool's generated workspace only when it is stable on your CI runner; never commit `mutants/`.

### Timing

| Codebase | Full run | Changed-files only |
|---|---|---|
| < 5k LOC | 2–5 min | < 1 min |
| 5k–20k LOC | 5–20 min | 2–5 min |
| > 20k LOC | 20–60 min | 5–15 min |

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

## Python pytest Techniques

Load this section only for Python projects that need the named technique. Core pytest rules stay in `languages/testing-python.md`.

### Async Tests

`asyncio_mode = "auto"` removes the need for `@pytest.mark.asyncio`.

```python
async def test_checkout_saves_confirmed_order(mocker):
    mock_repo = mocker.AsyncMock()
    service = OrderService(repository=mock_repo)

    result = await service.checkout(Order())

    # Assert behaviour (the returned state), not just that the mock was
    # touched — a save-call-only assertion is the mock-only anti-pattern
    # testing.md bans.
    assert result.status == OrderStatus.CONFIRMED
    saved_order = mock_repo.save.await_args.args[0]
    assert saved_order.status == OrderStatus.CONFIRMED
```

Use `mocker.AsyncMock()` for async dependencies; plain `Mock()` does not support `await`.

### Time-Dependent Tests

Use `time-machine` rather than `freezegun` on Python 3.12+.

| Rule | Agent action |
|------|-------------|
| Never call `datetime.now()` directly in domain objects | Inject a clock or freeze time in tests |
| Freeze only the smallest needed scope | Prefer context-manager scope when possible |

### HTTP Client Mocking (respx + httpx)

Use `respx` to mock `httpx` clients without starting a real server. Assert the returned behaviour and the outbound request shape that is part of the external contract.

### Integration Tests with Real Services

Use `testcontainers` for real DB/service integration tests. Unit tests must never import `testcontainers`; if a test does, it belongs in `tests/integration/`.

### Parallel Execution (pytest-xdist)

Parallel-safe tests require no shared filesystem state, no shared mutable globals, and DB isolation per worker.
