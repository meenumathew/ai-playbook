"""Fixtures shared by unit tests only."""

from pathlib import Path

import pytest

from tests import ALL_AGENTS


@pytest.fixture
def sample_source_root(tmp_path: Path) -> Path:
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    return tmp_path
