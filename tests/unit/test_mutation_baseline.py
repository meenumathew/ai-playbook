"""Unit tests for the mutation baseline checker."""

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def _stats(**overrides: int) -> dict[str, int]:
    data = {
        "killed": 100,
        "survived": 0,
        "total": 113,
        "no_tests": 13,
        "skipped": 0,
        "suspicious": 0,
        "timeout": 0,
        "check_was_interrupted_by_user": 0,
        "segfault": 0,
    }
    data.update(overrides)
    return data


def _baseline(**overrides: int) -> dict:
    thresholds = {
        "max_survived": 0,
        "max_no_tests": 13,
        "max_suspicious": 0,
        "max_timeout": 0,
        "max_check_was_interrupted_by_user": 0,
        "max_segfault": 0,
    }
    thresholds.update(overrides)
    return {"version": 1, "thresholds": thresholds}


def _run_checker(stats_path: Path, baseline_path: Path) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[2] / "tools" / "check-mutation-baseline.py"
    return subprocess.run(  # noqa: S603 - args are trusted test paths and repo script
        [sys.executable, str(script), str(stats_path), str(baseline_path)],
        text=True,
        capture_output=True,
        check=False,
    )


def test_accepts_stats_within_baseline(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats())
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 0
    assert "within the committed baseline" in result.stdout


def test_rejects_surviving_mutant_regression(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(survived=1))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "survived: observed 1, baseline allows 0" in result.stderr


def test_rejects_infrastructure_statuses(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(segfault=2))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "segfault: observed 2, baseline allows 0" in result.stderr
