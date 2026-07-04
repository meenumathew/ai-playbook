"""Acceptance tests for pack content frontmatter validation.

Pack files were the one surface with no contract check: core agents/KB are
contract-tested upstream, but a malformed pack file deployed silently and
failed only at runtime. `config validate` now treats pack-content violations
as errors (pre-deploy gate, exit 1); `doctor` reports them as warnings
(deployed-state health, gated in CI via `--strict`).
"""

from pathlib import Path

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app

runner = CliRunner()

VALID_KB_FRONTMATTER = """---
id: django-views
size: small
tldr: Django view conventions for this project
load_when: django view, viewset, url routing
audience: all
canonical_for: django view conventions
cross_refs: design-patterns.md
verified: 2026-06-12
---

# Django Views

Rules here.
"""

VALID_AGENT_FRONTMATTER = """---
name: Django Helper
description: Helps with Django specifics
argument-hint: Describe the Django change
model: executor
id: django-helper
load_when: django, ORM, migration
inputs: a Django change request
outputs: implementation guidance
handoff: diff-reviewer
escalation: humans on schema migrations
verified: 2026-06-12
---

# Django Helper Agent

Body.
"""


def _make_pack(project_root: Path, name: str) -> Path:
    pack_root = project_root / ".ai-playbook" / "packs" / name
    pack_root.mkdir(parents=True)
    (project_root / ".ai-playbook.toml").write_text(f'packs = [".ai-playbook/packs/{name}"]\n')
    return pack_root


def test_config_validate_flags_pack_kb_missing_frontmatter_key(tmp_path: Path):
    pack = _make_pack(tmp_path, "django")
    kb = pack / "knowledge-base" / "django-views.md"
    kb.parent.mkdir(parents=True)
    # Drop the `load_when:` line — routing would silently never fire.
    broken = "\n".join(
        line for line in VALID_KB_FRONTMATTER.splitlines() if not line.startswith("load_when:")
    )
    kb.write_text(broken)

    result = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])
    assert result.exit_code != 0, result.output
    assert "django-views.md" in result.output
    assert "load_when" in result.output


def test_doctor_warns_on_pack_agent_missing_frontmatter(tmp_path: Path):
    pack = _make_pack(tmp_path, "django")
    agent = pack / "agents" / "django-helper.agent.md"
    agent.parent.mkdir(parents=True)
    broken = "\n".join(
        line for line in VALID_AGENT_FRONTMATTER.splitlines() if not line.startswith("handoff:")
    )
    agent.write_text(broken)

    deploy = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--no-mcp"]
    )
    assert deploy.exit_code == 0, deploy.output

    result = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])
    assert "django-helper.agent.md" in result.output
    assert "handoff" in result.output


def test_valid_pack_produces_no_new_warnings(tmp_path: Path):
    pack = _make_pack(tmp_path, "django")
    kb = pack / "knowledge-base" / "django-views.md"
    kb.parent.mkdir(parents=True)
    kb.write_text(VALID_KB_FRONTMATTER)
    agent = pack / "agents" / "django-helper.agent.md"
    agent.parent.mkdir(parents=True)
    agent.write_text(VALID_AGENT_FRONTMATTER)

    validate = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])
    assert validate.exit_code == 0, validate.output
    assert "frontmatter" not in validate.output

    deploy = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--no-mcp"]
    )
    assert deploy.exit_code == 0, deploy.output
    doctor = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])
    assert "frontmatter" not in doctor.output


def test_no_packs_validation_is_noop(tmp_path: Path):
    validate = runner.invoke(app, ["config", "validate", "-t", str(tmp_path)])
    assert validate.exit_code == 0, validate.output
    assert "frontmatter" not in validate.output

    deploy = runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--no-mcp"]
    )
    assert deploy.exit_code == 0
    doctor = runner.invoke(app, ["doctor", "--tool", "claude", "-t", str(tmp_path)])
    assert "frontmatter" not in doctor.output
