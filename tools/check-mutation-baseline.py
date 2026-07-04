#!/usr/bin/env python3
"""Compare mutmut CI stats against the committed regression baseline.

`mutmut run` is useful only when the exported stats are treated as a contract.
This checker fails on new surviving/no-test mutants and on infrastructure-like
statuses such as suspicious, timeout, interrupted, or segfault.

Usage:
    python tools/check-mutation-baseline.py [STATS_JSON] [BASELINE_JSON]

Defaults:
    STATS_JSON    mutants/mutmut-cicd-stats.json
    BASELINE_JSON mutation-baseline.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATS_PATH = REPO_ROOT / "mutants" / "mutmut-cicd-stats.json"
DEFAULT_BASELINE_PATH = REPO_ROOT / "mutation-baseline.json"

STAT_FIELDS = (
    "killed",
    "survived",
    "total",
    "no_tests",
    "skipped",
    "suspicious",
    "timeout",
    "check_was_interrupted_by_user",
    "segfault",
)

THRESHOLD_TO_FIELD = {
    "max_survived": "survived",
    "max_no_tests": "no_tests",
    "max_suspicious": "suspicious",
    "max_timeout": "timeout",
    "max_check_was_interrupted_by_user": "check_was_interrupted_by_user",
    "max_segfault": "segfault",
}


class CheckError(Exception):
    """Mutation baseline contract violation."""


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CheckError(f"{path}: file does not exist") from exc
    except json.JSONDecodeError as exc:
        raise CheckError(f"{path}: invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise CheckError(f"{path}: expected a JSON object")
    return data


def _required_int(data: dict[str, Any], key: str, path: Path) -> int:
    value = data.get(key)
    if not isinstance(value, int) or value < 0:
        raise CheckError(f"{path}: `{key}` must be a non-negative integer")
    return value


def check_baseline(stats_path: Path, baseline_path: Path) -> list[str]:
    stats = _load_json_object(stats_path)
    baseline = _load_json_object(baseline_path)
    thresholds = baseline.get("thresholds")
    if not isinstance(thresholds, dict):
        raise CheckError(f"{baseline_path}: missing `thresholds` object")

    observed = {field: _required_int(stats, field, stats_path) for field in STAT_FIELDS}
    if observed["total"] <= 0:
        raise CheckError(f"{stats_path}: `total` must be greater than zero")

    failures: list[str] = []
    for threshold_key, stat_field in THRESHOLD_TO_FIELD.items():
        allowed = thresholds.get(threshold_key)
        if not isinstance(allowed, int) or allowed < 0:
            raise CheckError(
                f"{baseline_path}: `thresholds.{threshold_key}` must be a non-negative integer"
            )
        actual = observed[stat_field]
        if actual > allowed:
            failures.append(f"{stat_field}: observed {actual}, baseline allows {allowed}")

    return failures


def main(argv: list[str]) -> int:
    stats_path = Path(argv[1]) if len(argv) > 1 else DEFAULT_STATS_PATH
    baseline_path = Path(argv[2]) if len(argv) > 2 else DEFAULT_BASELINE_PATH

    try:
        failures = check_baseline(stats_path, baseline_path)
    except CheckError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("ERROR: mutation baseline regression:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        print(
            "\nReview surviving/no-test mutants before raising mutation-baseline.json.",
            file=sys.stderr,
        )
        return 1

    print("Mutation stats are within the committed baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
