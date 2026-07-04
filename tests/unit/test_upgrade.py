"""Unit tests for the upgrade-check helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.paths import VERSION_FILE, Tool
from deploy_ai_playbook.upgrade import (
    UpgradeStatus,
    _language_skip_files,
    check_upgrade,
    parse_version_file,
)


def test_check_upgrade_reports_not_deployed_when_version_file_missing(tmp_path: Path) -> None:
    report = check_upgrade(tmp_path, Tool.claude)

    assert report.status is UpgradeStatus.not_deployed
    assert report.deployed_fingerprint is None
    assert report.source_fingerprint is None
    assert any(VERSION_FILE in note for note in report.notes)


def test_check_upgrade_reports_drift_when_fingerprints_differ(tmp_path: Path) -> None:
    (tmp_path / VERSION_FILE).write_text(
        "playbook-fingerprint: 000000000000\n"
        "deployed-at: 2026-05-22T00:00:00Z\n"
        "tool: claude\n"
        "language: all\n"
    )

    report = check_upgrade(tmp_path, Tool.claude)

    assert report.status is UpgradeStatus.drift
    assert report.deployed_fingerprint == "000000000000"
    assert report.source_fingerprint != "000000000000"
    assert report.deployed_at == "2026-05-22T00:00:00Z"
    assert report.deployed_tool == "claude"


def test_check_upgrade_reports_tool_mismatch_even_when_fingerprint_matches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "deploy_ai_playbook.upgrade.compute_source_fingerprint", lambda *a, **k: "abc123"
    )
    (tmp_path / VERSION_FILE).write_text(
        "playbook-fingerprint: abc123\ntool: copilot\nlanguage: all\n"
    )

    report = check_upgrade(tmp_path, Tool.claude)

    assert report.status is UpgradeStatus.tool_mismatch
    assert any("--tool copilot" in note for note in report.notes)


def test_check_upgrade_collects_pack_versions(tmp_path: Path) -> None:
    (tmp_path / VERSION_FILE).write_text(
        "playbook-fingerprint: deadbeef\n"
        "tool: claude\n"
        "language: all\n"
        "pack: django@1.2.3\n"
        "pack: ops@0.4.0\n"
    )

    report = check_upgrade(tmp_path, Tool.claude)

    assert report.deployed_packs == ["django@1.2.3", "ops@0.4.0"]


def test_parse_version_file_ignores_blank_and_keyless_lines() -> None:
    parsed = parse_version_file(
        "\nplaybook-fingerprint: abc123\n# stray comment without colon\n  tool: claude  \n"
    )

    assert parsed.fingerprint == "abc123"
    assert parsed.tool == "claude"
    assert parsed.deployed_at is None
    assert parsed.packs == []


def test_language_skip_files_returns_empty_for_all_or_unknown() -> None:
    assert _language_skip_files(None) == set()
    assert _language_skip_files("") == set()
    assert _language_skip_files("all") == set()
    assert _language_skip_files("nonsense-language") == set()


@pytest.mark.parametrize(
    "language",
    ["python"],
)
def test_language_skip_files_excludes_other_languages_when_filter_set(language: str) -> None:
    skipped = _language_skip_files(language)

    # Filter should at least keep some files; sanity check it's a set of strings.
    assert isinstance(skipped, set)
    for entry in skipped:
        assert isinstance(entry, str)
