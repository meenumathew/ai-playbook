---
id: languages-python
size: medium
tldr: Python 3.12+; pydantic-settings; ruff + pyright; structured logging; extends style-guide.md and testing.md.
load_when: python, pydantic, ruff, pyright, mypy, uv, pyproject, fastapi, pydantic-settings
audience: all
canonical_for: Python language version, Python application structure, Python tooling, Python error handling
cross_refs: style-guide.md, testing.md, languages/testing-python.md
verified: 2026-06-10
---

# Python Conventions

> **Reference implementation.** This is the active language file for Python projects. It also serves as the reference for what a language conventions file should contain: see `templates/language-conventions-template.md` for the blank template.

## Agent Use

- **Read first:** Language Version, Application Structure, Code Style, Tooling, Logging, Error Handling, Input Validation.
- **Load deeper only on trigger:** use the relevant section below; do not load extra Python files.

---

## Language Version

Python 3.12+

---

## Application Structure

```text
my-project/
  src/
    my_package/
      __init__.py
      cli.py          ← thin, delegates to domain
      domain/
      services/
  tests/
  pyproject.toml
```

- Apps should have a CLI interface: enables end-to-end testing
- Keep CLI thin: delegate to domain model and services
- Use `src/` layout to avoid import path issues

---

## Code Style

| Rule | Agent action |
|------|-------------|
| PEP 8 conventions | Enforced by ruff |
| Type hints on all function signatures | Use built-in generics (`list`, `dict`, `set`) not `typing.List` (3.9+) |
| Descriptive names: never abbreviate | Flag abbreviations in review |
| Composition over inheritance | Favour composing objects over deep class hierarchies |
| EAFP over LBYL | `try/except` over pre-checks when race conditions or clarity matter |
| `pathlib.Path` for all filesystem operations | Never `os.path`: `Path` is composable, typed, and cross-platform |
| `typing.Final` for module-level constants | `MAX_RETRIES: Final = 3`: signals immutability to both humans and type checkers |
| `match` for structural branching | Prefer `match`/`case` over `if/elif` chains on type or shape (3.10+) |
| No `print()` in production | Use the logger |

---

## Docstrings: Google Style

Required on all public functions, methods, and classes. Not required on private methods with self-explanatory signatures, or test functions.

```python
def calculate_discount(order: Order, rate: float) -> float:
    """Apply a percentage discount to the order total.

    Args:
        order: The order to discount.
        rate: Discount rate as a decimal (e.g. 0.10 for 10%).

    Returns:
        The discounted total rounded to 2 decimal places.

    Raises:
        ValueError: If rate is not between 0 and 1.
    """
```

---

## Imports

| Rule | Agent action |
|------|-------------|
| Order: stdlib → third-party → local | Blank line between groups |
| Import modules, not individual functions | Exception: `typing` |
| Alphabetise within each group | Enforced by ruff |
| Declare public API with `__all__` | Any module intended for import by others: prevents accidental re-export |

---

## Environment Variables

For simple scripts, read directly from `os.environ`:

```python
TABLE_NAME = os.environ["TABLE_NAME"]           # Fail fast: KeyError if missing
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")  # Explicit default for optional
```

For applications, use **pydantic-settings**: validated, typed config loaded from environment or `.env`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str                    # required: startup fails if missing
    log_level: str = "INFO"              # optional with default
    max_retries: int = 3
    feature_new_checkout: bool = False   # feature flags as typed booleans

settings = Settings()
```

| Rule | Agent action |
|------|-------------|
| One `Settings` class per application | Import `settings` as a singleton: never call `Settings()` in multiple places |
| Never read `os.environ` directly in services | Inject `settings` through the constructor |
| `.env` file in `.gitignore` | `env.example` committed with placeholder values |

---

## Formatting

| Setting | Value |
|---------|-------|
| Line length | Per project config (typically 100; `pyproject.toml [tool.ruff]`) |
| Indentation | 4 spaces (PEP 8) |
| Formatter | `ruff format`: run after every GREEN and REFACTOR step |

---

## Tooling

| Tool | Purpose |
|------|---------|
| `uv` | Package manager + virtualenv (replaces pip, virtualenv, poetry): `uv sync`, `uv add`, `uv run` |
| `ruff` | Formatter + linter + import sorter (replaces black, flake8, isort) |
| `pyright` | Static type checker (`typeCheckingMode = "standard"` in `pyproject.toml`: strict for greenfield, standard for projects mixing typed and untyped third-party code): preferred over mypy: faster, better inference, same engine as Pylance in VS Code |
| `pytest` | Test runner: see `testing-python.md` |

For detailed `pyproject.toml` examples, use the project's existing config first; otherwise seed from this file and project needs.

---

## Logging

Use `logging.getLogger(__name__)`. Lazy evaluation (`logger.info("user %s", user_id)`): not f-strings. Use `logger.exception()` for caught errors. See `observability.md` for structured logging patterns.

---

## Reference Notes

Use only when the trigger appears:

| Topic | Load when |
|-------|-----------|
| `Protocol` | Ports/interfaces need Python-specific typing guidance |
| `TypedDict` | Dict-shaped boundary data needs typing |
| `TYPE_CHECKING` | Circular imports or heavy runtime type imports are in scope |
| `assert_never` | `match`/union exhaustiveness is in scope |
| Async layering | Python async services/adapters or timeout rules are in scope |

---

## Error Handling

Service layer raises domain exceptions. Presentation layer catches and converts to responses. See `philosophy.md` § Error Handling for principles.

| Rule | Agent action |
|------|-------------|
| Chain exceptions with `from exc` | Preserve traceback and root cause: `raise DomainError("safe message") from exc` |
| No mutable default arguments | `def f(items=[])` shares state across calls: use `None` and create the collection inside |

---

## Input Validation (Pydantic v2)

| Rule | Agent action |
|------|-------------|
| `extra="forbid"` on request models | Reject unknown fields |
| `extra="ignore"` on response models | Handle external data gracefully |
| `Field()` for constraints | `min_length`, `max_length`, `ge`, `le`, `pattern` |
| v2 APIs only | `field_validator` and `ConfigDict`: not v1 `validator` |
