"""Unit tests for DoctorService health calculation."""

from pathlib import Path

import pytest

from deploy_ai_playbook.doctor import (
    DeploymentNotFoundError,
    DoctorService,
    _pre_commit_config_has_commit_msg_stage,
)
from deploy_ai_playbook.paths import TOOL_DESTINATIONS, Tool
from tests import ALL_AGENTS


def test_doctor_service_reports_missing_deployment(sample_source_root: Path, tmp_path: Path):
    service = DoctorService()

    with pytest.raises(DeploymentNotFoundError) as exc_info:
        service.check(source_root=sample_source_root, project_root=tmp_path, tool=Tool.claude)

    assert exc_info.value.agents_dir == tmp_path / TOOL_DESTINATIONS[Tool.claude]["agents"]


def test_doctor_service_reports_missing_agent(sample_source_root: Path, tmp_path: Path):
    deployed_agents = tmp_path / TOOL_DESTINATIONS[Tool.claude]["agents"]
    deployed_agents.mkdir(parents=True)
    for agent_name in ALL_AGENTS:
        if agent_name == "xp-pair-programmer":
            continue
        source = sample_source_root / "agents" / f"{agent_name}.agent.md"
        (deployed_agents / source.name).write_text(source.read_text())

    report = DoctorService().check(
        source_root=sample_source_root,
        project_root=tmp_path,
        tool=Tool.claude,
    )

    assert any("xp-pair-programmer" in issue and "not deployed" in issue for issue in report.issues)


def _codex_deployment(tmp_path: Path) -> Path:
    agents_dir = tmp_path / TOOL_DESTINATIONS[Tool.codex]["agents"]
    agents_dir.mkdir(parents=True)
    return agents_dir


def test_doctor_reports_unparseable_codex_agent_toml(sample_source_root: Path, tmp_path: Path):
    agents_dir = _codex_deployment(tmp_path)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.toml").write_text(
            f'name = "{name}"\ndescription = "d"\ndeveloper_instructions = "# body"\n'
        )
    (agents_dir / "xp-pair-programmer.toml").write_text('name = "unterminated\n')
    # TOML requires UTF-8; a non-UTF-8 agent file is equally unloadable.
    (agents_dir / "story-refiner.toml").write_bytes(b'name = "x"\n\xff\xfe')

    report = DoctorService().check(
        source_root=sample_source_root,
        project_root=tmp_path,
        tool=Tool.codex,
    )

    assert any("xp-pair-programmer.toml" in issue and "TOML" in issue for issue in report.issues)
    assert any("story-refiner.toml" in issue and "TOML" in issue for issue in report.issues)


def test_doctor_skips_a_toml_entry_it_cannot_read(sample_source_root: Path, tmp_path: Path):
    """An entry that is not a readable file is skipped, not reported as bad TOML.

    `glob("*.toml")` also matches directories, so doctor must not turn a stray
    `something.toml/` folder into a syntax error the adopter cannot act on.
    """
    agents_dir = _codex_deployment(tmp_path)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.toml").write_text(
            f'name = "{name}"\ndescription = "d"\ndeveloper_instructions = "# body"\n'
        )
    (agents_dir / "stray.toml").mkdir()

    report = DoctorService().check(
        source_root=sample_source_root,
        project_root=tmp_path,
        tool=Tool.codex,
    )

    assert not any("stray.toml" in issue for issue in report.issues)


def test_doctor_accepts_parseable_codex_agent_toml_without_toml_issues(
    sample_source_root: Path, tmp_path: Path
):
    agents_dir = _codex_deployment(tmp_path)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.toml").write_text(
            f'name = "{name}"\ndescription = "d"\ndeveloper_instructions = "# body"\n'
        )

    report = DoctorService().check(
        source_root=sample_source_root,
        project_root=tmp_path,
        tool=Tool.codex,
    )

    assert not any("TOML" in issue for issue in report.issues)


def _pre_commit_config(stages: str) -> str:
    return f"repos:\n- repo: local\n  hooks:\n  - id: teach-back\n{stages}"


@pytest.mark.parametrize(
    "config_text",
    [
        _pre_commit_config("    stages: [commit-msg]\n"),
        _pre_commit_config('    stages: [pre-commit, "commit-msg"]\n'),
        _pre_commit_config("    stages:\n      - pre-commit\n      - commit-msg # required\n"),
        _pre_commit_config("    stages:\n      # comment\n      - 'commit-msg'\n"),
    ],
)
def test_pre_commit_config_detects_commit_msg_stage(config_text: str):
    assert _pre_commit_config_has_commit_msg_stage(config_text)


@pytest.mark.parametrize(
    "config_text",
    [
        "",
        "repos:\n- repo: local\n  hooks:\n  - id: lint\n",
        "repos:\n- repo: local\n  hooks:\n  - id: lint\n    stages: [pre-commit, manual]\n",
        "repos:\n- repo: local\n  hooks:\n  - id: lint\n    stages:\n      - pre-push\n",
    ],
)
def test_pre_commit_config_ignores_non_commit_msg_stages(config_text: str):
    assert not _pre_commit_config_has_commit_msg_stage(config_text)
