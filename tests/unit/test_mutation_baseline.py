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
        "max_unresolved_basis_points": 0,
        "max_no_tests": 13,
        "max_skipped": 0,
        "max_suspicious": 0,
        "max_timeout": 0,
        "max_check_was_interrupted_by_user": 0,
        "max_segfault": 0,
        "min_total": 101,
    }
    thresholds.update(overrides)
    return {"version": 3, "thresholds": thresholds}


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


def test_rejects_unresolved_mutant_regression(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(survived=1))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "unresolved rate (survived + timeout)" in result.stderr
    assert "baseline allows 0.00%" in result.stderr


def test_accepts_timeout_to_survivor_reclassification(tmp_path: Path):
    """Runner speed may turn old timeouts into survivors without weakening tests."""
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(survived=70, timeout=30))
    _write_json(
        baseline_path,
        _baseline(max_unresolved_basis_points=8900, max_timeout=100),
    )

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 0


def test_rejects_combined_survivor_and_timeout_regression(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(survived=70, timeout=31))
    _write_json(
        baseline_path,
        _baseline(max_unresolved_basis_points=8900, max_timeout=100),
    )

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "unresolved rate (survived + timeout)" in result.stderr
    assert "observed 89.38%" in result.stderr


def test_unresolved_rate_scales_with_larger_mutant_population(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(total=200, survived=20))
    _write_json(
        baseline_path,
        _baseline(max_unresolved_basis_points=1000),
    )

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 0


def test_rejects_infrastructure_statuses(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(segfault=2))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "segfault: observed 2, baseline allows 0" in result.stderr


def test_rejects_skipped_mutant_regression(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(skipped=3))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "skipped: observed 3, baseline allows 0" in result.stderr


def test_rejects_collapsed_mutant_population(tmp_path: Path):
    """A total below min_total means most of src/ stopped being mutated."""
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(total=40, killed=27))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "total: observed 40, baseline requires at least 101" in result.stderr


def test_rejects_baseline_missing_min_total(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats())
    baseline = _baseline()
    del baseline["thresholds"]["min_total"]
    _write_json(baseline_path, baseline)

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 1
    assert "min_total" in result.stderr


def test_accepts_total_at_exact_floor(tmp_path: Path):
    stats_path = tmp_path / "stats.json"
    baseline_path = tmp_path / "baseline.json"
    _write_json(stats_path, _stats(total=101, killed=88))
    _write_json(baseline_path, _baseline())

    result = _run_checker(stats_path, baseline_path)

    assert result.returncode == 0
