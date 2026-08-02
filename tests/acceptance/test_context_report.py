"""Acceptance tests for static context-efficiency reporting."""

import json

from deploy_ai_playbook.cli import app
from tests.acceptance._dsl import runner


def test_context_report_json_explains_and_totals_agent_surface(tmp_path):
    result = runner.invoke(
        app,
        [
            "context-report",
            "--agent",
            "xp-pair-programmer",
            "--target-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["estimate"] == {
        "billable_usage": False,
        "method": "ceil(characters / 4)",
        "scope": "static playbook files only",
    }
    assert {surface["path"] for surface in payload["fixed"]} == {
        "CLAUDE.md",
        "knowledge-base/CHEATSHEET.md",
    }
    assert len(payload["agents"]) == 1
    agent = payload["agents"][0]
    assert agent["agent"] == "xp-pair-programmer"
    assert agent["agent_surface"]["path"] == "agents/xp-pair-programmer.agent.md"
    assert {surface["path"] for surface in agent["preloads"]} == {
        "knowledge-base/debugging.md",
        "knowledge-base/testing.md",
    }
    component_characters = sum(surface["characters"] for surface in payload["fixed"])
    component_characters += agent["agent_surface"]["characters"]
    component_characters += sum(surface["characters"] for surface in agent["preloads"])
    assert agent["total_characters"] == component_characters
    assert agent["estimated_tokens"] > 0


def test_context_report_includes_configured_pack_agent_and_kb_override(tmp_path):
    pack = tmp_path / ".ai-playbook" / "packs" / "python"
    (pack / "agents").mkdir(parents=True)
    (pack / "knowledge-base").mkdir()
    (pack / "agents" / "python-reviewer.agent.md").write_text(
        "---\n"
        "name: Python Reviewer\n"
        "description: Reviews Python changes\n"
        "id: python-reviewer\n"
        "preload: python-review.md\n"
        "---\n"
        "# Python Reviewer\n",
        encoding="utf-8",
    )
    (pack / "knowledge-base" / "python-review.md").write_text(
        "# Python Review\n",
        encoding="utf-8",
    )
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/python"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "context-report",
            "--agent",
            "python-reviewer",
            "--target-dir",
            str(tmp_path),
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["agents"][0]["origin"] == "pack:python"
    assert payload["agents"][0]["preloads"][0]["path"] == "knowledge-base/python-review.md"


def test_context_report_human_output_disclaims_runtime_usage(tmp_path):
    result = runner.invoke(
        app,
        [
            "context-report",
            "--agent",
            "docs-maintainer",
            "--target-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Static context estimate" in result.output
    assert "docs-maintainer" in result.output
    assert "not billable usage" in result.output
    assert "conversation, tool schemas, and files read later are excluded" in result.output


def test_context_report_reports_an_unmeasurable_surface_instead_of_crashing(tmp_path):
    """A pack agent that preloads a file it does not ship fails with an error, not a traceback.

    The measurement is only as good as the declaration: if the preload cannot
    be found, the totals would be silently short, so the command refuses.
    """
    pack = tmp_path / ".ai-playbook" / "packs" / "python"
    (pack / "agents").mkdir(parents=True)
    (pack / "agents" / "python-reviewer.agent.md").write_text(
        "---\nid: python-reviewer\npreload: never-shipped.md\n---\n# Python Reviewer\n",
        encoding="utf-8",
    )
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/python"]\n',
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "context-report",
            "--agent",
            "python-reviewer",
            "--target-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Context report failed" in result.output
    assert "never-shipped.md" in result.output


def test_context_report_unknown_agent_returns_actionable_error(tmp_path):
    result = runner.invoke(
        app,
        [
            "context-report",
            "--agent",
            "missing-agent",
            "--target-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "Unknown agent" in result.output
    assert "xp-pair-programmer" in result.output
