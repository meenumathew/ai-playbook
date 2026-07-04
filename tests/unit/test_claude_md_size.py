"""Tests for tools/check-claude-md-size.py.

The check enforces a line-count budget on CLAUDE.md so always-loaded
context cannot grow without deliberate review against RFC-0001's
classification criteria. These tests cover:

- A clean repo passes (regression test for the live state).
- An over-threshold file fails with a clear message.
- The failure message cites RFC-0001 so contributors know why.
- The CLAUDE_SKIP_CLAUDE_MD_SIZE escape hatch works.
- The tool resolves the default CLAUDE.md path from its own location,
  so it works no matter where the user runs it from.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check-claude-md-size.py"


def _load_script_module():
    """Import the size-check script as a module so tests can read its constants."""
    spec = importlib.util.spec_from_file_location("check_claude_md_size", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_SCRIPT = _load_script_module()
MAX_LINES = int(_SCRIPT.MAX_LINES)
RFC_REF = str(_SCRIPT.RFC_REF)


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


def write_oversized_file(tmp_path: Path, lines: int) -> Path:
    """Write a file with `lines` newline-terminated lines."""
    path = tmp_path / "oversized.md"
    path.write_text("\n".join(f"line {i}" for i in range(lines)) + "\n", encoding="utf-8")
    return path


def test_claude_md_size_clean_repo_passes() -> None:
    """Live CLAUDE.md must be within budget — regression guard."""
    result = run_check()
    assert result.returncode == 0, result.stderr


def test_claude_md_size_over_threshold_fails(tmp_path: Path) -> None:
    """A file one line over MAX_LINES fails with count, threshold, and target path."""
    over = MAX_LINES + 1
    path = write_oversized_file(tmp_path, over)
    result = run_check(path)
    assert result.returncode == 1
    assert str(over) in result.stderr
    assert str(MAX_LINES) in result.stderr
    assert str(path) in result.stderr


def test_claude_md_size_failure_message_cites_rfc(tmp_path: Path) -> None:
    """Failure message points contributors at the canonical RFC reference.

    The script owns the citation string in `RFC_REF`; the test reuses it so
    rewording the citation in the script doesn't require a parallel test edit.
    """
    path = write_oversized_file(tmp_path, MAX_LINES + 1)
    result = run_check(path)
    assert result.returncode == 1
    assert RFC_REF in result.stderr


def test_claude_md_size_skip_flag_bypasses_check(tmp_path: Path) -> None:
    """CLAUDE_SKIP_CLAUDE_MD_SIZE=1 bypasses the gate with a stderr notice."""
    path = write_oversized_file(tmp_path, MAX_LINES + 1)
    result = run_check(path, env_overrides={"CLAUDE_SKIP_CLAUDE_MD_SIZE": "1"})
    assert result.returncode == 0
    assert "CLAUDE_SKIP_CLAUDE_MD_SIZE" in result.stderr


def test_claude_md_size_runs_from_any_cwd(tmp_path: Path) -> None:
    """Default path is anchored to the script, not the invocation cwd."""
    result = run_check(cwd=tmp_path)
    assert result.returncode == 0, result.stderr


def test_claude_md_size_missing_file_fails_cleanly(tmp_path: Path) -> None:
    """A missing target reports a clean error, not a raw traceback."""
    result = run_check(tmp_path / "does-not-exist.md")
    assert result.returncode == 1
    assert "ERROR: cannot read" in result.stderr
    assert "Traceback" not in result.stderr


def test_claude_md_size_over_word_budget_fails(tmp_path: Path) -> None:
    """A dense file within the line cap but over MAX_WORDS fails.

    The word budget is the companion ratchet: without it, packing words onto
    fewer lines defeats the line cap invisibly.
    """
    max_words = int(_SCRIPT.MAX_WORDS)
    words_per_line = (max_words // 10) + 1
    path = tmp_path / "dense.md"
    path.write_text(
        "\n".join(" ".join(f"w{i}" for i in range(words_per_line)) for _ in range(10)) + "\n",
        encoding="utf-8",
    )
    result = run_check(path)
    assert result.returncode == 1
    assert str(max_words) in result.stderr
