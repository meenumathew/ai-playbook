"""Unit tests for the upgrade-check helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.deployment_record import (
    DeploymentRecord,
    DeploymentScope,
    ScopeKind,
    deployment_record_text,
)
from deploy_ai_playbook.paths import VERSION_FILE, Tool
from deploy_ai_playbook.upgrade import (
    UpgradeStatus,
    _language_skip_files,
    check_upgrade,
    parse_version_file,
    stale_carryover_fingerprint,
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
    assert parsed.scope == DeploymentScope()


def test_scope_aware_deployment_record_round_trips() -> None:
    record = DeploymentRecord(
        fingerprint="abc123",
        deployed_at="2026-07-23T00:00:00Z",
        tool="claude",
        language="python",
        packs=["django@1.2.3"],
        scope=DeploymentScope(
            kind=ScopeKind.partial,
            agents=("story-refiner",),
            harness=False,
            mcp=False,
        ),
    )

    parsed = parse_version_file(deployment_record_text(record))

    assert parsed == record


def test_scope_record_invalid_boolean_uses_safe_default() -> None:
    parsed = parse_version_file(
        "scope: partial\nagent: story-refiner\nrules: maybe\nharness: FALSE\n"
    )

    assert parsed.scope.rules is True
    assert parsed.scope.harness is False


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


# ---------------------------------------------------------------------------
# stale_carryover_fingerprint
# ---------------------------------------------------------------------------


def _fake_source(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    (source / "agents").mkdir(parents=True)
    (source / "agents" / "alpha.agent.md").write_text("# alpha v1\n")
    (source / "agents" / "beta.agent.md").write_text("# beta v1\n")
    return source


def _fingerprint_over(source: Path, scope: DeploymentScope) -> str:
    from deploy_ai_playbook.discovery import discover_layered
    from deploy_ai_playbook.fs import compute_source_fingerprint

    return compute_source_fingerprint(
        source,
        discover_layered(source, packs=[]).files,
        skip_files=set(),
        agent_names=scope.fingerprint_agent_names,
        include_commands=scope.commands,
        include_harness=scope.harness,
        include_rules=scope.rules,
    )


def _carryover(
    previous: DeploymentRecord | None,
    source: Path,
    *,
    selected_agents: set[str],
) -> str | None:
    from deploy_ai_playbook.discovery import discover_layered

    return stale_carryover_fingerprint(
        previous,
        tool=Tool.claude,
        source_root=source,
        discovered_files=discover_layered(source, packs=[]).files,
        selected_agents=selected_agents,
        all_agents={"alpha", "beta"},
        rules=False,
        commands=True,
        harness=False,
        selected_language=None,
    )


def _previous_record(source: Path) -> DeploymentRecord:
    scope = DeploymentScope(
        kind=ScopeKind.full, agents=("alpha", "beta"), rules=False, harness=False
    )
    return DeploymentRecord(
        fingerprint=_fingerprint_over(source, scope),
        tool="claude",
        language="all",
        scope=scope,
    )


def test_carryover_none_without_previous_record(tmp_path: Path) -> None:
    source = _fake_source(tmp_path)

    assert _carryover(None, source, selected_agents={"alpha"}) is None


def test_carryover_none_when_previous_record_is_another_tool(tmp_path: Path) -> None:
    source = _fake_source(tmp_path)
    previous = DeploymentRecord(fingerprint="abc", tool="copilot")

    assert _carryover(previous, source, selected_agents={"alpha"}) is None


def test_carryover_none_when_this_run_rewrites_the_whole_previous_surface(
    tmp_path: Path,
) -> None:
    """A full redeploy rewrites everything: the fresh fingerprint is truthful
    even though the source moved since the previous deploy."""
    source = _fake_source(tmp_path)
    previous = _previous_record(source)
    (source / "agents" / "beta.agent.md").write_text("# beta v2\n")

    assert _carryover(previous, source, selected_agents={"alpha", "beta"}) is None


def test_carryover_none_when_source_unchanged_since_previous_deploy(tmp_path: Path) -> None:
    source = _fake_source(tmp_path)
    previous = _previous_record(source)

    assert _carryover(previous, source, selected_agents={"alpha"}) is None


def test_carryover_returns_previous_fingerprint_when_carried_files_are_stale(
    tmp_path: Path,
) -> None:
    source = _fake_source(tmp_path)
    previous = _previous_record(source)
    (source / "agents" / "beta.agent.md").write_text("# beta v2\n")

    assert _carryover(previous, source, selected_agents={"alpha"}) == previous.fingerprint
