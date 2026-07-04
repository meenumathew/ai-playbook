"""Shared fixtures available to all test types."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from deploy_ai_playbook.cli import app
from tests import ALL_AGENTS

_runner = CliRunner()


@pytest.fixture()
def sample_source_root(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    return tmp_path


@pytest.fixture()
def deployed_claude(tmp_path: Path) -> Path:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n'
    )
    result = _runner.invoke(
        app, ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path)]
    )
    assert result.exit_code == 0, f"Deploy setup failed:\n{result.output}"
    return tmp_path
