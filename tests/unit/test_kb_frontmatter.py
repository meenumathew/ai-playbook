"""Tests for tools/check-kb-frontmatter.py.

The checker enforces the KB and skill frontmatter contract used by INDEX.md
load decisions and skill discovery. These tests cover:

- A clean repo passes (regression test for the live state).
- Missing required keys fail with a clear message.
- Empty required keys fail.
- cross_refs pointing at non-existent files fail.
- 'all KB files' sentinel in cross_refs is permitted.
- Skill files use the skill contract, not the KB contract.
- Files outside the canonical dirs are ignored.
- The CLAUDE_SKIP_KB_FRONTMATTER escape hatch works.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "tools" / "check-kb-frontmatter.py"


def run_check(
    *paths: Path, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    args = [sys.executable, str(SCRIPT), *(str(p) for p in paths)]
    return subprocess.run(  # noqa: S603 — args are constructed from trusted constants
        args,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        env=env,
        check=False,
    )


def write_kb(tmp_path: Path, body: str, name: str = "demo.md") -> Path:
    path = tmp_path / "knowledge-base" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


def make_kb_body(**overrides: str) -> str:
    keys = {
        "id": "demo",
        "size": "small",
        "tldr": "demo",
        "load_when": "demo",
        "audience": "all",
        "canonical_for": "demo",
        "cross_refs": "design-patterns.md",
        "verified": "2026-05-27",
    }
    keys.update(overrides)
    front = "\n".join(f"{k}: {v}" for k, v in keys.items())
    return f"---\n{front}\n---\n\n# Demo\n\nbody.\n"


def test_kb_frontmatter_clean_repo_passes() -> None:
    """Live KB and skill files must conform — regression guard."""
    result = run_check()
    assert result.returncode == 0, result.stderr


def test_kb_frontmatter_default_scan_includes_languages() -> None:
    """The no-args scan must cover shipped languages/*.md (they carry real
    frontmatter) while keeping seeded workspaces/ content excluded."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("check_kb_frontmatter", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    kb_files, _skills = module.discover_targets([])
    relative = {p.relative_to(REPO_ROOT).as_posix() for p in kb_files}

    assert "knowledge-base/languages/python.md" in relative
    assert "knowledge-base/languages/testing-python.md" in relative
    assert not any(rel.startswith("knowledge-base/workspaces/") for rel in relative)


def test_kb_frontmatter_missing_required_keys_fails(tmp_path: Path) -> None:
    body = "---\nid: demo\nsize: small\n---\n\n# Demo\n"
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 1
    assert "missing required keys" in result.stderr


def test_kb_frontmatter_empty_required_key_fails(tmp_path: Path) -> None:
    body = make_kb_body(tldr='""')
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 1
    assert "is empty" in result.stderr


def test_kb_frontmatter_unresolvable_cross_ref_fails(tmp_path: Path) -> None:
    body = make_kb_body(cross_refs="totally-nonexistent.md")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 1
    assert "totally-nonexistent.md" in result.stderr
    assert "does not resolve" in result.stderr


def test_kb_frontmatter_all_sentinel_in_cross_refs_passes(tmp_path: Path) -> None:
    body = make_kb_body(cross_refs="all KB files")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 0, result.stderr


def test_kb_frontmatter_section_anchor_in_cross_ref_passes(tmp_path: Path) -> None:
    body = make_kb_body(cross_refs="design-patterns.md § Module Depth")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 0, result.stderr


def test_kb_frontmatter_unresolvable_section_anchor_fails(tmp_path: Path) -> None:
    body = make_kb_body(cross_refs="design-patterns.md § Totally Missing Heading")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 1
    assert "Totally Missing Heading" in result.stderr
    assert "does not contain heading" in result.stderr


def test_kb_frontmatter_checks_language_and_workspace_kb_files(tmp_path: Path) -> None:
    language_path = write_kb(
        tmp_path,
        "---\nid: python\nsize: small\n---\n\n# Python\n",
        name="languages/python.md",
    )
    workspace_path = write_kb(
        tmp_path,
        "---\nid: workspace\nsize: small\n---\n\n# Workspace\n",
        name="workspaces/README.md",
    )

    result = run_check(language_path, workspace_path)

    assert result.returncode == 1
    assert "languages/python.md" in result.stderr
    assert "workspaces/README.md" in result.stderr
    assert "missing required keys" in result.stderr


def test_kb_frontmatter_missing_block_fails(tmp_path: Path) -> None:
    path = write_kb(tmp_path, "# No frontmatter here\n")
    result = run_check(path)
    assert result.returncode == 1
    assert "missing frontmatter" in result.stderr


def test_kb_frontmatter_skill_contract(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills" / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "---\n"
        "name: demo\n"
        "description: 'demo skill'\n"
        "user-invocable: false\n"
        "license: MIT\n"
        "---\n\n# Demo\n"
    )
    skill_path.write_text(body, encoding="utf-8")
    result = run_check(skill_path)
    assert result.returncode == 0, result.stderr


def test_kb_frontmatter_skill_missing_key_fails(tmp_path: Path) -> None:
    skill_path = tmp_path / "skills" / "demo" / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    body = "---\nname: demo\ndescription: 'demo'\n---\n\n# Demo\n"
    skill_path.write_text(body, encoding="utf-8")
    result = run_check(skill_path)
    assert result.returncode == 1
    assert "missing required keys" in result.stderr


def test_kb_frontmatter_skip_flag_bypasses_check(tmp_path: Path) -> None:
    body = make_kb_body(cross_refs="totally-nonexistent.md")
    path = write_kb(tmp_path, body)
    result = run_check(path, env_overrides={"CLAUDE_SKIP_KB_FRONTMATTER": "1"})
    assert result.returncode == 0


def test_kb_frontmatter_stale_verified_warns_without_failing(tmp_path: Path) -> None:
    """A long-past `verified` date warns on stderr but does not fail the run.

    A hard gate on age would make CI go red purely because time passed; the
    check is intentionally non-blocking.
    """
    body = make_kb_body(verified="2020-01-01")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 0, result.stderr
    assert "days old" in result.stderr
    assert "staleness" in result.stderr.lower()


def test_kb_frontmatter_recent_verified_does_not_warn(tmp_path: Path) -> None:
    """A recent `verified` date produces no staleness warning."""
    body = make_kb_body(verified="2099-01-01")
    path = write_kb(tmp_path, body)
    result = run_check(path)
    assert result.returncode == 0, result.stderr
    assert "days old" not in result.stderr


def test_kb_frontmatter_ignores_unrelated_paths(tmp_path: Path) -> None:
    """Files outside knowledge-base/ and skills/ should be ignored when passed."""
    other = tmp_path / "docs" / "thing.md"
    other.parent.mkdir(parents=True, exist_ok=True)
    other.write_text("# unrelated\n", encoding="utf-8")
    result = run_check(other)
    assert result.returncode == 0
