"""Acceptance tests for harness/read-budget.sh.

The PreToolUse hook mechanizes the CLAUDE.md read-budget protocol: count
Read calls per session, warn at 80% of the active agent's declared cap,
block (exit 2) over cap, fail open whenever attribution is impossible.

Each test builds a synthetic project dir (deployed agent file + transcript)
and pipes a PreToolUse-shaped payload to the hook, exactly as Claude Code
would.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "harness" / "read-budget.sh"


def make_project(
    tmp_path: Path,
    agent: str = "story-refiner",
    budget: str = "20",
    marker: str | None = None,
) -> tuple[Path, Path]:
    """Create a fake deployed project and transcript; returns (project, transcript)."""
    project = tmp_path / "project"
    agents_dir = project / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / f"{agent}.agent.md").write_text(
        f"---\nid: {agent}\nread-budget: {budget}\n---\n# {agent}\n", encoding="utf-8"
    )
    transcript = tmp_path / "transcript.jsonl"
    lines = ['{"type":"user","message":"please Use story-refiner for this"}']
    if marker is not None:
        lines.append(json.dumps({"type": "assistant", "message": marker}))
    transcript.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return project, transcript


def run_hook(
    project: Path,
    transcript: Path,
    session_id: str = "sess-1",
    env_overrides: dict[str, str] | None = None,
    file_path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    payload = json.dumps(
        {
            "session_id": session_id,
            "transcript_path": str(transcript),
            "tool_name": "Read",
            "tool_input": {"file_path": file_path or "/some/file.py"},
        }
    )
    env = os.environ.copy()
    env["CLAUDE_PROJECT_DIR"] = str(project)
    env.pop("CLAUDE_SKIP_READ_BUDGET", None)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(  # noqa: S603 — repo-owned hook under test
        ["/bin/sh", str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def read_count(project: Path, session_id: str = "sess-1") -> int:
    count_file = project / ".claude" / "read-budget" / f"{session_id}.count"
    return int(count_file.read_text()) if count_file.exists() else 0


def test_read_within_budget_allows_and_counts(tmp_path: Path) -> None:
    project, transcript = make_project(tmp_path, marker="Active agent: story-refiner")

    first = run_hook(project, transcript)
    second = run_hook(project, transcript)

    assert first.returncode == 0 and second.returncode == 0
    assert read_count(project) == 2


def test_read_over_cap_blocks_with_stop_and_ask_message(tmp_path: Path) -> None:
    """The 21st read for a cap-20 agent exits 2 naming the cap."""
    project, transcript = make_project(tmp_path, budget="20", marker="Active agent: story-refiner")
    (project / ".claude" / "read-budget").mkdir(parents=True)
    (project / ".claude" / "read-budget" / "sess-1.count").write_text("20\n")

    result = run_hook(project, transcript)

    assert result.returncode == 2
    assert "20" in result.stderr and "story-refiner" in result.stderr
    assert "STOP and ask" in result.stderr
    assert read_count(project) == 20, "blocked reads must not consume budget"


def test_read_at_80_percent_warns_but_allows(tmp_path: Path) -> None:
    """Read 16 of 20 (80%) is allowed with a count/cap warning."""
    project, transcript = make_project(tmp_path, budget="20", marker="Active agent: story-refiner")
    (project / ".claude" / "read-budget").mkdir(parents=True)
    (project / ".claude" / "read-budget" / "sess-1.count").write_text("15\n")

    result = run_hook(project, transcript)

    assert result.returncode == 0
    assert "16/20" in result.stderr


def test_no_marker_fails_open_silently(tmp_path: Path) -> None:
    """A transcript without an Active agent marker allows silently."""
    project, transcript = make_project(tmp_path, marker=None)

    result = run_hook(project, transcript)

    assert result.returncode == 0
    assert result.stderr == ""


def test_self_tracked_agent_fails_open_silently(tmp_path: Path) -> None:
    """xp-pair-programmer declares self-tracked — no enforcement."""
    project, transcript = make_project(
        tmp_path,
        agent="xp-pair-programmer",
        budget="self-tracked",
        marker="Active agent: xp-pair-programmer",
    )

    result = run_hook(project, transcript)

    assert result.returncode == 0
    assert result.stderr == ""


def test_skip_flag_allows_over_cap_with_notice(tmp_path: Path) -> None:
    """CLAUDE_SKIP_READ_BUDGET=1 bypasses the block with a notice."""
    project, transcript = make_project(tmp_path, budget="20", marker="Active agent: story-refiner")
    (project / ".claude" / "read-budget").mkdir(parents=True)
    (project / ".claude" / "read-budget" / "sess-1.count").write_text("25\n")

    result = run_hook(project, transcript, env_overrides={"CLAUDE_SKIP_READ_BUDGET": "1"})

    assert result.returncode == 0
    assert "CLAUDE_SKIP_READ_BUDGET" in result.stderr


def test_last_marker_wins_on_agent_switch(tmp_path: Path) -> None:
    """A mid-session role switch re-attributes enforcement to the new agent."""
    project, transcript = make_project(
        tmp_path, agent="diff-reviewer", budget="20", marker="Active agent: story-refiner"
    )
    with transcript.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"type": "assistant", "message": "Active agent: diff-reviewer"}) + "\n")

    (project / ".claude" / "read-budget").mkdir(parents=True)
    (project / ".claude" / "read-budget" / "sess-1.count").write_text("20\n")

    result = run_hook(project, transcript)

    assert result.returncode == 2
    assert "diff-reviewer" in result.stderr


def test_sessions_count_independently(tmp_path: Path) -> None:
    project, transcript = make_project(tmp_path, marker="Active agent: story-refiner")

    run_hook(project, transcript, session_id="sess-a")
    run_hook(project, transcript, session_id="sess-b")

    assert read_count(project, "sess-a") == 1
    assert read_count(project, "sess-b") == 1


def test_missing_transcript_fails_open(tmp_path: Path) -> None:
    project, _transcript = make_project(tmp_path, marker="Active agent: story-refiner")

    result = run_hook(project, tmp_path / "missing.jsonl")

    assert result.returncode == 0
    assert read_count(project) == 0


def test_duplicate_read_of_same_path_warns(tmp_path: Path) -> None:
    """Re-reading a file already read this session is pure budget waste — warn."""
    project, transcript = make_project(tmp_path, marker="Active agent: story-refiner")

    first = run_hook(project, transcript, file_path="/repo/src/app.py")
    second = run_hook(project, transcript, file_path="/repo/src/app.py")

    assert first.returncode == 0 and second.returncode == 0
    assert "already read" not in first.stderr
    assert "already read" in second.stderr
    assert "/repo/src/app.py" in second.stderr


def test_distinct_paths_do_not_warn(tmp_path: Path) -> None:
    project, transcript = make_project(tmp_path, marker="Active agent: story-refiner")

    run_hook(project, transcript, file_path="/repo/src/a.py")
    second = run_hook(project, transcript, file_path="/repo/src/b.py")

    assert second.returncode == 0
    assert "already read" not in second.stderr
