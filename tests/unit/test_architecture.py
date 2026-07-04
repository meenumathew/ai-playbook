"""Architecture enforcement tests — mechanical guardrails.

These tests enforce the dependency direction documented in CLAUDE.md:
    paths/targets (foundation) → fs/discovery/mcp (middle) → backup/doctor (service) → cli (top)

Lower layers must never import from higher layers. This test fails the build
if someone (human or AI agent) introduces a backwards dependency.
"""

import ast
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).parent.parent.parent / "src" / "deploy_ai_playbook"

# Allowed imports for each module (what it MAY import from within the package).
# Anything not listed here is forbidden.
#
# Layers (bottom to top):
#   foundation: paths, config, safety, console
#   middle:     targets, discovery, fs, mcp, telemetry
#   service:    backup, upgrade, services, doctor
#   top:        cli, deploy_render (Typer registration + presentation)
ALLOWED_INTERNAL_IMPORTS: dict[str, set[str]] = {
    "paths": set(),
    # `errors` is the foundation-layer exception base — every layer can import it.
    "errors": set(),
    # Shared Rich console instances — foundation, imports nothing internal.
    "console": set(),
    "targets": {"paths", "errors"},
    "config": {"errors"},
    "safety": {"errors"},
    "fs": {"paths", "safety", "targets"},
    "discovery": {"paths", "config", "errors", "targets"},
    "mcp": {"paths", "safety", "targets"},
    "telemetry": {"paths", "safety", "targets"},
    "backup": {"paths", "config", "discovery", "fs", "targets"},
    "upgrade": {"paths", "config", "fs", "discovery"},
    # services/* depends only on foundation + middle, plus its own siblings
    # (services → services is fine; the layer is one logical package and
    # intra-package helper reuse — e.g. diff.py importing deploy.path_rewrite —
    # is the alternative to duplicate code). Never on cli, doctor, or upgrade.
    "services": {"paths", "config", "discovery", "fs", "targets", "services"},
    "doctor": {
        "paths",
        "config",
        "errors",
        "fs",
        "discovery",
        "services",
        "targets",
        "telemetry",
        "upgrade",
    },
    # Deploy presentation extracted from cli — same layer as cli,
    # but deliberately NOT allowed to import cli (no cycles, no doctor).
    # `config` added for provider-driven MCP deploy (issue-tracker provider
    # decides whether the Atlassian MCP is configured) — foundation import,
    # direction unchanged.
    "deploy_render": {
        "paths",
        "config",
        "errors",
        "safety",
        "console",
        "fs",
        "discovery",
        "mcp",
        "telemetry",
        "backup",
        "upgrade",
        "services",
        "targets",
    },
    "cli": {
        "paths",
        "config",
        "errors",
        "console",
        "deploy_render",
        "fs",
        "discovery",
        "mcp",
        "safety",
        "backup",
        "doctor",
        "services",
        "targets",
        "telemetry",
        "upgrade",
    },
    "__init__": {"cli", "errors", "paths", "config", "fs", "discovery", "mcp", "backup"},
}

PACKAGE_NAME = "deploy_ai_playbook"


def _extract_internal_imports(filepath: Path) -> set[str]:
    """Parse a Python file and return set of internal module names it imports."""
    tree = ast.parse(filepath.read_text())
    imports: set[str] = set()
    for node in ast.walk(tree):
        imports.update(_internal_modules_from_node(node))
    return imports


def _internal_modules_from_node(node: ast.AST) -> set[str]:
    if isinstance(node, ast.Import):
        return {
            _first_module_segment(alias.name.removeprefix(f"{PACKAGE_NAME}."))
            for alias in node.names
            if alias.name.startswith(f"{PACKAGE_NAME}.")
        }
    if isinstance(node, ast.ImportFrom):
        return _internal_modules_from_import_from(node)
    return set()


def _internal_modules_from_import_from(node: ast.ImportFrom) -> set[str]:
    if node.level:
        package_modules = {name for name, _ in _get_source_modules()}
        if node.module:
            return {_first_module_segment(node.module)}
        return {
            _first_module_segment(alias.name)
            for alias in node.names
            if _first_module_segment(alias.name) in package_modules
        }
    if node.module == PACKAGE_NAME:
        # `from deploy_ai_playbook import x` resolves to `__init__.py`;
        # we filter to module-shaped names so plain symbol imports
        # (`__version__`, `AIPlaybookError`) don't get mis-attributed
        # to a sibling module that happens to share the symbol name.
        package_modules = {name for name, _ in _get_source_modules()}
        return {
            _first_module_segment(alias.name)
            for alias in node.names
            if _first_module_segment(alias.name) in package_modules
        }
    if node.module.startswith(f"{PACKAGE_NAME}."):
        return {_first_module_segment(node.module.removeprefix(f"{PACKAGE_NAME}."))}
    return set()


def _first_module_segment(module_name: str) -> str:
    return module_name.split(".")[0]


def _get_source_modules() -> list[tuple[str, Path]]:
    """Return (module_group, path) for each Python file in the package.

    Top-level files map to their stem (paths.py -> 'paths'). Subpackage
    files map to their package name (services/diff.py -> 'services'), so
    every service module is judged against the same layer rule. The
    subpackage __init__ itself is included as the package representative
    for the 'no rule defined' check.
    """
    modules: list[tuple[str, Path]] = [
        (path.stem, path) for path in sorted(SRC_DIR.glob("*.py")) if path.stem != "__pycache__"
    ]
    for subdir in sorted(p for p in SRC_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"):
        modules.extend(
            (subdir.name, path)
            for path in sorted(subdir.rglob("*.py"))
            if path.stem != "__pycache__"
        )
    return modules


@pytest.mark.parametrize(
    "module_name,filepath",
    _get_source_modules(),
    ids=[name for name, _ in _get_source_modules()],
)
def test_dependency_direction(module_name: str, filepath: Path) -> None:
    """Each module only imports from its allowed dependencies."""
    if module_name not in ALLOWED_INTERNAL_IMPORTS:
        pytest.skip(f"No rule defined for {module_name}")

    actual_imports = _extract_internal_imports(filepath)
    allowed = ALLOWED_INTERNAL_IMPORTS[module_name]
    forbidden = actual_imports - allowed

    assert not forbidden, (
        f"Module '{module_name}' imports {forbidden} but is only allowed to import {allowed}. "
        f"This violates the dependency direction: lower layers must not import from higher layers."
    )


def test_no_circular_dependencies() -> None:
    """No modules may form a circular dependency.

    Intra-package self-loops (e.g. ``services/diff.py`` importing
    ``services/deploy.py``) collapse to a `services → services` self-edge
    once subpackage files are rolled up by package name. Those are not
    real cycles — they are sibling-helper reuse within one logical layer.
    `ALLOWED_INTERNAL_IMPORTS` permits them explicitly; the cycle check
    here filters self-edges so this allowance is consistent.
    """
    all_imports: dict[str, set[str]] = {}
    for module_name, filepath in _get_source_modules():
        imports = _extract_internal_imports(filepath)
        # Drop self-edges introduced by subpackage roll-up.
        all_imports.setdefault(module_name, set()).update(imports - {module_name})

    cycle = _find_dependency_cycle(all_imports)
    assert cycle is None, (
        f"Circular dependency: {' -> '.join(cycle or [])}. "
        f"Extract shared code into a lower-level module."
    )


def test_all_source_modules_have_rules() -> None:
    """Every source module must be listed in ALLOWED_INTERNAL_IMPORTS."""
    modules = {name for name, _ in _get_source_modules()}
    missing = modules - set(ALLOWED_INTERNAL_IMPORTS.keys())
    assert not missing, (
        f"New module(s) {missing} have no architecture rule. "
        f"Add them to ALLOWED_INTERNAL_IMPORTS in test_architecture.py."
    )


def _find_dependency_cycle(graph: dict[str, set[str]]) -> list[str] | None:
    internal_graph = {
        module_name: dependencies & set(graph) for module_name, dependencies in graph.items()
    }
    try:
        tuple(TopologicalSorter(internal_graph).static_order())
    except CycleError as error:
        return _closed_cycle([str(module_name) for module_name in error.args[1]])
    return None


def test_relative_imports_are_counted_as_internal_dependencies() -> None:
    tree = ast.parse("from .cli import app\nfrom . import backup\n")

    imports = set()
    for node in ast.walk(tree):
        imports.update(_internal_modules_from_node(node))

    assert imports == {"backup", "cli"}


def _closed_cycle(cycle: list[str]) -> list[str]:
    if cycle and cycle[0] != cycle[-1]:
        return [*cycle, cycle[0]]
    return cycle


def test_extract_internal_imports_catches_import_statement_forms(tmp_path: Path) -> None:
    module = tmp_path / "sample.py"
    module.write_text(
        "import deploy_ai_playbook.cli\n"
        "import deploy_ai_playbook.fs as fs\n"
        "from deploy_ai_playbook import doctor\n"
        "from deploy_ai_playbook.telemetry import telemetry_status\n"
    )

    assert _extract_internal_imports(module) == {"cli", "fs", "doctor", "telemetry"}


def test_find_dependency_cycle_catches_long_cycles() -> None:
    graph = {
        "a": {"b"},
        "b": {"c"},
        "c": {"a"},
        "d": set(),
    }

    cycle = _find_dependency_cycle(graph)

    assert cycle is not None
    assert cycle[0] == cycle[-1]
    assert set(cycle[:-1]) == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# Cross-platform safety: text I/O must declare its encoding
# ---------------------------------------------------------------------------
#
# Python's `Path.read_text` / `Path.write_text` / `open(...)` default to
# locale-dependent encoding on Linux/macOS and UTF-8 on Windows-3.15+.
# Mixing those silently corrupts files when adopters run on a system whose
# locale is not UTF-8 (LANG=C, POSIX, some CI images). The fix is simple:
# every text I/O call must pass `encoding="utf-8"` explicitly.
#
# Ruff's `PLW1514` rule covers this but is preview-only at the time of
# writing and pulls in unrelated rules. This contract test is the stable
# enforcement layer — AST-walks the package and fails on any text I/O
# call missing the keyword. Test code is excluded; pytest's tmp_path
# fixtures are platform-agnostic and adding `encoding=` everywhere there
# is noise.

_TEXT_IO_METHODS = frozenset({"read_text", "write_text"})


def _text_io_calls_missing_encoding(filepath: Path) -> list[tuple[int, str]]:
    """Return (line_number, call_summary) for each unsafe text I/O call."""
    tree = ast.parse(filepath.read_text(encoding="utf-8"))
    findings: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        method = _called_method_name(node)
        if method not in _TEXT_IO_METHODS:
            continue
        if any(kw.arg == "encoding" for kw in node.keywords):
            continue
        findings.append((node.lineno, f".{method}(...)"))
    return findings


def _called_method_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def test_every_custom_exception_inherits_from_ai_playbook_error() -> None:
    """Every public Error class in `src/` must subclass `AIPlaybookError`.

    The base class is the contract for `except AIPlaybookError` to actually
    catch every error the package raises. Skipping it (e.g. plain
    `class FooError(Exception)`) silently breaks programmatic adopters.
    """
    import importlib
    import inspect

    from deploy_ai_playbook.errors import AIPlaybookError

    failures: list[str] = []
    for module_name, _filepath in _get_source_modules():
        if module_name in {"errors", "__init__"}:
            continue
        try:
            module = importlib.import_module(f"deploy_ai_playbook.{module_name}")
        except ImportError:
            # Subpackage init or empty module — nothing to introspect.
            continue
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if not name.endswith("Error"):
                continue
            if obj is AIPlaybookError:
                continue
            if obj.__module__ != f"deploy_ai_playbook.{module_name}":
                # Re-exported / imported error from another module — checked there.
                continue
            if not issubclass(obj, AIPlaybookError):
                failures.append(f"{module_name}.{name}: does not subclass AIPlaybookError")
    assert not failures, "Custom exceptions outside AIPlaybookError hierarchy:\n  " + "\n  ".join(
        failures
    )


def test_package_text_io_passes_explicit_encoding() -> None:
    """Every Path.read_text/write_text in src/ and tools/ must pass encoding=.

    This is enforcement of cross-platform safety. If a new helper genuinely
    needs locale-default behaviour (very rare — usually only when the file
    is owned by some external system that picks the encoding), refactor it
    into a thin wrapper module and add that module to `_ENCODING_EXEMPT`.
    """
    _ENCODING_EXEMPT: frozenset[str] = frozenset()  # noqa: N806 — lint-style constant

    repo_root = SRC_DIR.parent.parent.parent
    audit_roots = [SRC_DIR, repo_root / "tools"]
    failures: list[str] = []
    for audit_root in audit_roots:
        if not audit_root.exists():
            continue
        for path in sorted(audit_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            if path.name in _ENCODING_EXEMPT:
                continue
            for line_number, call in _text_io_calls_missing_encoding(path):
                failures.append(
                    f'{path.relative_to(repo_root)}:{line_number} {call} missing encoding="utf-8"'
                )
    assert not failures, (
        "Text I/O without explicit encoding (cross-platform hazard):\n  " + "\n  ".join(failures)
    )


def _artifact_id_mentions(path: Path) -> list[tuple[int, str]]:
    """Line numbers and text of comments/docstrings citing workflow artifact IDs.

    Only commentary is scanned: string literals used as data (test fixtures
    that create `stories/STORY-001-*.md` files, glob patterns) are legitimate
    and ignored.
    """
    import io
    import re
    import tokenize

    pattern = re.compile(r"\b(?:STORY|PLAN|AUDIT|CHORE|RESEARCH|BUG|SPIKE)-(?:\d+|[A-Z]+-\d+)")
    source = path.read_text(encoding="utf-8")
    mentions: list[tuple[int, str]] = [
        (token.start[0], token.string.strip())
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type == tokenize.COMMENT and pattern.search(token.string)
    ]

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            docstring = ast.get_docstring(node)
            if docstring and pattern.search(docstring):
                mentions.append((node.body[0].lineno, docstring.splitlines()[0]))
    return mentions


def test_workflow_artifact_scanner_catches_rubric_shaped_ids(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text(
        '"""Do not ship references to STORY-NOT-007."""\n'
        "def example():\n"
        "    # PLAN-001 belongs in the commit, not the code.\n"
        "    return 1\n",
        encoding="utf-8",
    )

    assert _artifact_id_mentions(sample) == [
        (3, "# PLAN-001 belongs in the commit, not the code."),
        (1, "Do not ship references to STORY-NOT-007."),
    ]


def test_no_workflow_artifact_ids_in_comments_or_docstrings() -> None:
    """Ticket context belongs in commits, not code.

    Enforces `knowledge-base/style-guide.md` § Ticket Context Belongs in
    Commits, Not Code: story/plan/audit/chore IDs are temporary workflow
    artifacts — citing them in comments or docstrings rots the moment the
    artifact is archived. Traceability lives in commit messages.
    """
    repo_root = SRC_DIR.parent.parent.parent
    failures: list[str] = []
    for audit_root in (SRC_DIR, repo_root / "tools", repo_root / "evals", repo_root / "tests"):
        if not audit_root.exists():
            continue
        for path in sorted(audit_root.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            for line_number, text in _artifact_id_mentions(path):
                failures.append(f"{path.relative_to(repo_root)}:{line_number} {text[:80]}")
    assert not failures, (
        "Workflow artifact IDs in comments/docstrings (see style-guide.md § "
        "Ticket Context Belongs in Commits, Not Code):\n  " + "\n  ".join(failures)
    )
