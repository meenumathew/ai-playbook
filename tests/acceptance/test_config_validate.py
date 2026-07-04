"""Acceptance tests for `ai-playbook config validate`."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app

runner = CliRunner()


def test_config_validate_accepts_missing_config(tmp_path: Path) -> None:
    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "valid" in result.output
    assert "missing" in result.output


def test_config_validate_json_reports_packs_and_overrides(tmp_path: Path) -> None:
    pack_root = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_root.mkdir(parents=True)
    (pack_root / "pack.toml").write_text('name = "internal"\nversion = "1.2.3"\n')
    (pack_root / "agents").mkdir()
    (pack_root / "agents" / "internal-reviewer.agent.md").write_text(
        """---
name: Internal Reviewer
description: Pack test fixture agent
argument-hint: Describe the change
model: executor
id: internal-reviewer
load_when: pack fixture
inputs: a request
outputs: guidance
handoff: diff-reviewer
escalation: humans
verified: 2026-06-12
---

# Internal Reviewer
"""
    )
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/internal"]\n\n'
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n\n'
        '[quality_tiers.agents]\ninternal-reviewer = "production"\n'
    )

    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["valid"] is True
    assert payload["packs"][0]["name"] == "internal"
    assert payload["packs"][0]["version"] == "1.2.3"
    assert payload["quality_tier_overrides"] == {"internal-reviewer": "production"}
    assert payload["warnings"] == []


def test_config_validate_human_output_reports_warnings(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\n\n'
        '[quality_tiers.agents]\nretired-agent = "prototype"\n'
    )

    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])

    assert result.exit_code == 0
    assert "advisor=claude-opus" in result.output
    assert "Warnings" in result.output
    assert "Model tier mapping incomplete" in result.output
    assert "retired-agent" in result.output


def test_config_validate_warns_about_unknown_quality_tier_override(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[quality_tiers.agents]\nretired-agent = "prototype"\n'
    )

    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert "retired-agent" in payload["warnings"][0]


def test_config_validate_rejects_invalid_pack_path(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('packs = ["../outside"]\n')

    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])

    assert result.exit_code == 1
    assert "Pack path must stay inside" in result.output
