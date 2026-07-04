---
id: languages-testing-python
size: large
tldr: pytest + pytest-mock + pytest-cov; fixtures in conftest.py; mock at service boundary; extends testing.md.
load_when: pytest, python test, fixture, conftest, pytest-mock, parametrize, pytest-cov, pytest-asyncio, pytest-randomly, frozen time, time-machine, httpx, respx, testcontainers, pytest-xdist
audience: all
canonical_for: pytest test runner, pytest fixtures, pytest mocking, pytest parametrize, pytest exception testing
cross_refs: testing.md, testing-techniques.md, languages/python.md
verified: 2026-07-17
---

# Testing: Python (pytest)

> **Reference implementation.** This is the active testing file for Python projects. It also serves as the reference for what a language testing file should contain: see `templates/testing-language-template.md` for the blank template.

## Agent Use

- **Read first:** Test Runner, Fixtures, Mocking, Parametrize, Exception Testing.
- **Load deeper only on trigger:** async tests, frozen time, HTTP client mocking, testcontainers, or parallel pytest execution: § Python pytest Techniques below.

---

## Test Runner

Adopter-side recommended setup. **Required**: pytest, pytest-cov, pytest-mock. **Recommended add-ons**: pytest-randomly (catches order-dependent tests), pytest-asyncio (for async code), pytest-xdist (parallel execution). Drop the add-ons if your project doesn't need them.

```toml
# pyproject.toml: adopter guidance, not this repo's exact config
[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-mock>=3.14.0",
    # Recommended add-ons: uncomment as needed:
    # "pytest-randomly>=3.15.0",      # randomises test order; catches hidden coupling
    # "pytest-asyncio>=0.24.0",       # async test support
    # "pytest-xdist>=3.5.0",          # parallel execution: pytest -n auto
    # "time-machine>=2.14.0",         # time travel for time-dependent tests (replaces freezegun)
    # "respx>=0.21.0",                # mock httpx clients
    # "testcontainers[postgres]>=4.0.0",  # real DB/service in Docker for integration tests
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
# addopts = "--randomly-seed=last"   # only if pytest-randomly is installed
# asyncio_mode = "auto"              # only if pytest-asyncio is installed

[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 80    # adopter-configurable: see knowledge-base/quality-gates.md
show_missing = true
```

```bash
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run pytest -n auto                          # parallel (requires pytest-xdist)
uv run pytest --randomly-seed=12345            # reproduce specific order
```

---

## Test File Structure

```text
tests/
  conftest.py            ← shared fixtures only, never test logic
  test_order.py          ← unit tests for Order
  test_order_service.py  ← unit tests for OrderService
  integration/
    test_order_repo.py   ← integration tests hitting real DB
```

---

## Fixtures

Use fixtures (in `conftest.py` when shared) for reusable setup instead of copy-pasted arrange blocks; use `yield` for teardown:

```python
@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.rollback()
    session.close()
```

**Scope rules:**

| Scope | When | Agent action |
|-------|------|-------------|
| `function` (default) | Most fixtures | Recreated per test: safest |
| `module` | Expensive setup shared within one file | e.g. HTTP client |
| `session` | Expensive setup shared across all tests | e.g. DB engine. **Never for mutable state.** |

Use the narrowest scope that keeps tests independent.

---

## Mocking

**Do not use `unittest.mock`.** Never import any `unittest.mock` symbol. Always use the `pytest-mock` `mocker` fixture: same API (`mocker.Mock()`, `mocker.MagicMock()`, `mocker.patch()`, `mocker.AsyncMock()` replace the imports; `mocker.patch(...)` inside the test replaces the `@patch` decorator), but every patch is undone automatically at teardown.

Where `mocker` seems unavailable, it isn't:

| Escape hatch | Correct approach |
|---|---|
| `AsyncMock(spec=SomePort)` inside a `@pytest.fixture` | Add `mocker` as a fixture parameter: pytest injects it like any other fixture |
| Module-level helper building mocks | Convert the helper to a fixture, or pass `mocker` in: `def _make_thing(mocker): return mocker.AsyncMock(...)` |

**Agent enforcement:**

- **xp-pair-programmer:** never write `unittest.mock` imports. If existing code uses them, migrate to `mocker` in a separate refactor commit.
- **diff-reviewer / code-inspector:** any `unittest.mock` import in the diff is a **Must Fix**.

---

## Parametrize

```python
@pytest.mark.parametrize("amount,expected", [
    (50.00, 50.00),    # below threshold
    (100.00, 90.00),   # at threshold
    (200.00, 180.00),  # above threshold
])
def test_discount_calculation(amount, expected):
    order = Order()
    order.add_item(Item("item", amount))
    assert order.total_with_discount() == expected
```

---

## Exception Testing

```python
def test_payment_raises_when_order_is_empty():
    with pytest.raises(InvalidOrderException, match="order has no items"):
        Order().process_payment()
```

---

## Python pytest Techniques

Load a subsection only when its trigger appears. Language-agnostic technique rules (property-based, mutation, contract, async patterns): `testing-techniques.md`.

### Async Tests

`asyncio_mode = "auto"` removes the need for `@pytest.mark.asyncio`. Use `mocker.AsyncMock()` for async dependencies; plain `Mock()` does not support `await`.

```python
async def test_checkout_saves_confirmed_order(mocker):
    mock_repo = mocker.AsyncMock()
    service = OrderService(repository=mock_repo)

    result = await service.checkout(Order())

    # Assert behaviour, not only that the mock was touched (testing.md § TDD Fidelity)
    assert result.status == OrderStatus.CONFIRMED
    saved_order = mock_repo.save.await_args.args[0]
    assert saved_order.status == OrderStatus.CONFIRMED
```

### Time-Dependent Tests

Use `time-machine` rather than `freezegun` on Python 3.12+. Never call `datetime.now()` directly in domain objects: inject a clock or freeze time in tests, at the smallest needed scope (prefer context-manager scope).

### HTTP Client Mocking (respx + httpx)

Use `respx` to mock `httpx` clients without starting a real server. Assert the returned behaviour and the outbound request shape that is part of the external contract.

### Integration Tests with Real Services

Use `testcontainers` for real DB/service integration tests. Unit tests must never import `testcontainers`; if a test does, it belongs in `tests/integration/`.

### Parallel Execution (pytest-xdist)

Parallel-safe tests require no shared filesystem state, no shared mutable globals, and DB isolation per worker.
