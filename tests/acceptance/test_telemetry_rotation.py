"""Acceptance tests for harness/telemetry.sh state handling.

Rotation must never destroy history on malformed configuration, and agent
attribution must come from assistant messages, not from tool results (file
contents in the transcript would otherwise flip it).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from deploy_ai_playbook.discovery import get_source_root


def run_telemetry(
    project: Path,
    payload: dict[str, object],
    env_overrides: dict[str, str] | None = None,
    tool: str = "claude",
) -> subprocess.CompletedProcess[str]:
    script = get_source_root() / "harness" / "telemetry.sh"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(  # noqa: S603 - test executes a repo-owned shell script.
        ["/bin/sh", str(script), tool],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_rotation_skipped_when_max_bytes_is_not_numeric(tmp_path: Path) -> None:
    """A garbage CLAUDE_USAGE_MAX_BYTES must disable rotation, not rotate
    unconditionally: rotate-on-every-Stop plus the keep-N prune destroys
    real history within N sessions."""
    usage = tmp_path / ".claude" / "usage.jsonl"
    usage.parent.mkdir(parents=True)
    usage.write_text('{"timestamp":"t","session_id":"old"}\n', encoding="utf-8")

    result = run_telemetry(
        tmp_path, {"session_id": "s1"}, env_overrides={"CLAUDE_USAGE_MAX_BYTES": "not-a-number"}
    )

    assert result.returncode == 0, result.stderr
    archives = list(usage.parent.glob("usage-*.jsonl*"))
    assert archives == [], "malformed max-bytes must not trigger rotation"
    assert '"session_id":"old"' in usage.read_text(encoding="utf-8")


def test_rotation_still_works_with_numeric_threshold(tmp_path: Path) -> None:
    usage = tmp_path / ".claude" / "usage.jsonl"
    usage.parent.mkdir(parents=True)
    usage.write_text('{"timestamp":"t","session_id":"old"}\n' * 100, encoding="utf-8")

    result = run_telemetry(
        tmp_path, {"session_id": "s1"}, env_overrides={"CLAUDE_USAGE_MAX_BYTES": "64"}
    )

    assert result.returncode == 0, result.stderr
    archives = list(usage.parent.glob("usage-*.jsonl*"))
    assert len(archives) == 1, "an over-threshold log must rotate to an archive"


@pytest.mark.skipif(shutil.which("jq") is None, reason="assistant-only extraction requires jq")
def test_marker_inside_non_assistant_message_does_not_flip_attribution(tmp_path: Path) -> None:
    """Tool results (read file contents) live in the transcript as user-type
    entries. A file containing the literal marker must not re-attribute the
    session."""
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"type": "assistant", "message": "Active agent: story-refiner"}),
                json.dumps(
                    {
                        "type": "user",
                        "message": "tool result with file text: Active agent: diff-reviewer",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_telemetry(tmp_path, {"session_id": "s1", "transcript_path": str(transcript)})

    assert result.returncode == 0, result.stderr
    event = json.loads((tmp_path / ".claude" / "usage.jsonl").read_text(encoding="utf-8").strip())
    assert event["active_agent"] == "story-refiner"


def test_codex_session_end_payload_writes_codex_operational_log(tmp_path: Path) -> None:
    transcript = tmp_path / "codex-transcript.jsonl"
    transcript.write_text(
        '{"message":"Active agent: xp-pair-programmer"}\n{"message":"done"}\n',
        encoding="utf-8",
    )

    result = run_telemetry(
        tmp_path,
        {
            "hook_event_name": "SessionEnd",
            "model": "gpt-5.6-terra",
            "session_id": "codex-session",
            "transcript_path": str(transcript),
        },
        tool="codex",
    )

    assert result.returncode == 0, result.stderr
    usage_path = tmp_path / ".codex" / "usage.jsonl"
    event = json.loads(usage_path.read_text(encoding="utf-8").strip())
    assert event == {
        "active_agent": "xp-pair-programmer",
        "source": "codex",
        "timestamp": event["timestamp"],
        "turns": 2,
    }
    assert not (tmp_path / ".claude" / "usage.jsonl").exists()


def test_telemetry_log_omits_sensitive_session_and_usage_fields(tmp_path: Path) -> None:
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        '{"type":"assistant","message":"Active agent: diff-reviewer",'
        '"usage":{"input_tokens":100,"output_tokens":20}}\n',
        encoding="utf-8",
    )

    result = run_telemetry(
        tmp_path,
        {
            "model": "private-model",
            "session_id": "sensitive-session-id",
            "transcript_path": str(transcript),
        },
    )

    assert result.returncode == 0, result.stderr
    event = json.loads((tmp_path / ".claude" / "usage.jsonl").read_text(encoding="utf-8"))
    assert event.keys() == {"active_agent", "source", "timestamp", "turns"}
    serialized = json.dumps(event)
    for sensitive in (
        "session",
        "token",
        "model",
        str(transcript),
        "sensitive-session-id",
        "private-model",
    ):
        assert sensitive not in serialized
