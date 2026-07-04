---
id: languages-testing-python
size: large
tldr: pytest + pytest-mock + pytest-cov; fixtures in conftest.py; mock at service boundary; extends testing.md.
load_when: pytest, python test, fixture, conftest, pytest-mock, parametrize, pytest-cov, pytest-asyncio, pytest-randomly
audience: all
canonical_for: pytest test runner, pytest fixtures, pytest mocking, pytest parametrize, pytest exception testing
cross_refs: testing.md, testing-techniques.md, languages/python.md
verified: 2026-06-10
---

# Testing: Python (pytest)

> **Reference implementation.** This is the active testing file for Python projects. It also serves as the reference for what a language testing file should contain: see `templates/testing-language-template.md` for the blank template.

## Agent Use

- **Read first:** Test Runner, Fixtures, Mocking, Parametrize, Exception Testing.
- **Load deeper only on trigger:** async tests, frozen time, HTTP client mocking, testcontainers, or parallel pytest execution: use `testing-techniques.md` § Python pytest Techniques.

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

Use fixtures for reusable setup: avoid copy-pasting arrange blocks:

```python
# conftest.py
@pytest.fixture
def empty_order():
    return Order()

@pytest.fixture
def order_with_items():
    order = Order()
    order.add_item(Item("book", 10.00))
    return order
```

Use `yield` for teardown:

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

**Do not use `unittest.mock`.** Never import `from unittest.mock import Mock, patch, MagicMock` or any other `unittest.mock` symbol. Always use the `pytest-mock` `mocker` fixture: a thin wrapper over `unittest.mock` that exposes the same API but undoes every patch automatically at test teardown and integrates with pytest's fixture lifecycle.

| Banned | Use instead |
|--------|-------------|
| `from unittest.mock import Mock` | `mocker.Mock()` |
| `from unittest.mock import MagicMock` | `mocker.MagicMock()` |
| `from unittest.mock import patch` | `mocker.patch()` |
| `from unittest.mock import AsyncMock` | `mocker.AsyncMock()` |
| `@patch(...)` decorator | `mocker.patch(...)` inside the test |

**Common escape hatches: and how to avoid them:**

The temptation to reach for `unittest.mock` appears in two places where `mocker` seems unavailable. Both have clean pytest solutions:

| Escape hatch | Why it seems needed | Correct approach |
|---|---|---|
| **Fixtures**: `AsyncMock(spec=SomePort)` in a `@pytest.fixture` | "`mocker` isn't a parameter of my fixture" | Add `mocker` as a fixture parameter: pytest injects it like any other fixture |
| **Module-level helpers**: `def _make_thing(): return AsyncMock(...)` | "`mocker` isn't in scope at module level" | Convert the helper to a fixture, or pass `mocker` as an argument: `def _make_thing(mocker): return mocker.AsyncMock(...)` |

```python
# ✗ Wrong: reaches for unittest.mock because mocker seems unavailable
from unittest.mock import AsyncMock

@pytest.fixture()
def client():
    mock_repo = AsyncMock(spec=CaseRepositoryPort)
    ...

# ✓ Correct: mocker is just another fixture
@pytest.fixture()
def client(mocker):
    mock_repo = mocker.AsyncMock(spec=CaseRepositoryPort)
    ...
```

**Agent enforcement:**

- **xp-pair-programmer:** never write `unittest.mock` imports. If existing code uses them, migrate to `mocker` in a separate refactor commit.
- **diff-reviewer / code-inspector:** any `unittest.mock` import in the diff is a **Must Fix**.

Use `pytest-mock` at the service layer:

```python
def test_order_service_saves_order(mocker):
    mock_repo = mocker.Mock()
    service = OrderService(repository=mock_repo)

    service.place_order(Order())

    mock_repo.save.assert_called_once_with(mocker.ANY)
```

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

## Reference Notes

Advanced pytest techniques live outside the core Python testing rules so agents do not load them for routine test work:

| Topic | Load when |
|-------|-----------|
| `testing-techniques.md` § Python pytest Techniques | Python async, frozen time, HTTP mocking, testcontainers, or xdist are in scope |
