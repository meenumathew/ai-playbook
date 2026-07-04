"""Tests for tools/check-agent-size.py.

The check enforces per-file line budgets on frequently-loaded surfaces
(agents/*.agent.md, CHEATSHEET, INDEX, skills/*/SKILL.md) so per-invocation
context cannot grow without deliberate review. Mirrors the CLAUDE.md
size-gate tests:

- A clean repo passes (regression test for the live state).
- An over-budget agent or surface file fails with a clear message naming it.
- Unlisted agents/skills get the default cap.
- The CLAUDE_SKIP_AGENT_SIZE escape hatch works.
- The tool resolves the default repo root from its own location.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check-agent-size.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("check_agent_size", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = _load_script_module()
AGENT_MAX_LINES = dict(_SCRIPT.AGENT_MAX_LINES)
DEFAULT_AGENT_MAX_LINES = int(_SCRIPT.DEFAULT_AGENT_MAX_LINES)
SURFACE_MAX_LINES = dict(_SCRIPT.SURFACE_MAX_LINES)
DEFAULT_SKILL_MAX_LINES = int(_SCRIPT.DEFAULT_SKILL_MAX_LINES)


def run_check(
    *paths: Path,
    env_overrides: dict[str, str] | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    args = [sys.executable, str(SCRIPT), *(str(p) for p in paths)]
    return subprocess.run(  # noqa: S603 — args are constructed from trusted constants
        args,
        capture_output=True,
        text=True,
        cwd=cwd or REPO_ROOT,
        env=env,
        check=False,
    )


def write_lines(path: Path, lines: int) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"line {i}" for i in range(lines)) + "\n", encoding="utf-8")
    return path


def make_root(tmp_path: Path) -> Path:
    root = tmp_path / "root"
    (root / "agents").mkdir(parents=True)
    (root / "skills").mkdir()
    return root


def test_size_gate_clean_repo_passes() -> None:
    """Every live loaded-surface file must be within its budget — regression guard."""
    result = run_check()
    assert result.returncode == 0, result.stderr


def test_every_live_agent_has_an_explicit_cap() -> None:
    """New agents must get a deliberate cap, not silently inherit the default."""
    live = {p.name for p in (REPO_ROOT / "agents").glob("*.agent.md")}
    assert live == set(AGENT_MAX_LINES), (
        "agents/ and tools/check-agent-size.py AGENT_MAX_LINES are out of sync; "
        "add or remove cap entries to match"
    )


def test_every_live_skill_has_an_explicit_cap() -> None:
    """New skills must get a deliberate cap, not silently inherit the default."""
    live = {str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "skills").glob("*/SKILL.md")}
    listed = {rel for rel in SURFACE_MAX_LINES if rel.startswith("skills/")}
    assert live == listed, (
        "skills/ and tools/check-agent-size.py SURFACE_MAX_LINES are out of sync; "
        "add or remove cap entries to match"
    )


def test_over_budget_agent_fails_naming_the_file(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_lines(root / "agents" / "custom.agent.md", DEFAULT_AGENT_MAX_LINES + 1)

    result = run_check(root)

    assert result.returncode == 1
    assert "custom.agent.md" in result.stderr
    assert str(DEFAULT_AGENT_MAX_LINES + 1) in result.stderr


def test_over_budget_surface_fails_naming_the_file(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    cap = SURFACE_MAX_LINES["knowledge-base/CHEATSHEET.md"]
    write_lines(root / "knowledge-base" / "CHEATSHEET.md", cap + 1)

    result = run_check(root)

    assert result.returncode == 1
    assert "CHEATSHEET.md" in result.stderr
    assert str(cap) in result.stderr


def test_unlisted_skill_gets_default_cap(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_lines(root / "skills" / "new-skill" / "SKILL.md", DEFAULT_SKILL_MAX_LINES + 1)

    result = run_check(root)

    assert result.returncode == 1
    assert "skills/new-skill/SKILL.md" in result.stderr


def test_within_budget_passes(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_lines(root / "agents" / "small.agent.md", 5)
    write_lines(root / "skills" / "tiny" / "SKILL.md", 5)

    result = run_check(root)

    assert result.returncode == 0


def test_skip_flag_bypasses_check(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    write_lines(root / "agents" / "custom.agent.md", DEFAULT_AGENT_MAX_LINES + 1)

    result = run_check(root, env_overrides={"CLAUDE_SKIP_AGENT_SIZE": "1"})

    assert result.returncode == 0
    assert "CLAUDE_SKIP_AGENT_SIZE" in result.stderr


def test_runs_from_any_cwd(tmp_path: Path) -> None:
    result = run_check(cwd=tmp_path)
    assert result.returncode == 0, result.stderr
