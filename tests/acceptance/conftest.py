"""Fixtures shared by acceptance tests only."""

from pathlib import Path

import pytest

from tests.acceptance._dsl import deploy


@pytest.fixture
def deployed_claude(tmp_path: Path) -> Path:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "claude-opus"\nexecutor = "claude-sonnet"\n'
    )
    result = deploy(tmp_path)
    assert result.exit_code == 0, f"Deploy setup failed:\n{result.output}"
    return tmp_path
