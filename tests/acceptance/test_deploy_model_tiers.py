"""Acceptance tests for materializing model tiers into deployed agent frontmatter."""

from pathlib import Path

import pytest

from deploy_ai_playbook.discovery import get_source_root
from tests.acceptance._dsl import deploy, diff, doctor

ADVISOR_AGENT = "story-refiner"
EXECUTOR_AGENT = "xp-pair-programmer"


def _frontmatter(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    assert content.startswith("---\n"), f"{path} has no frontmatter"
    return content.split("\n---\n", 1)[0]


def _deploy(tmp_path: Path, tool: str = "claude") -> None:
    result = deploy(tmp_path, tool=tool)
    assert result.exit_code == 0, result.output


def test_deploy_claude_materializes_mapped_tiers(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "opus"\nexecutor = "haiku"\n'
    )

    _deploy(tmp_path)

    agents_dir = tmp_path / ".claude" / "agents"
    advisor_frontmatter = _frontmatter(agents_dir / f"{ADVISOR_AGENT}.agent.md")
    executor_frontmatter = _frontmatter(agents_dir / f"{EXECUTOR_AGENT}.agent.md")
    assert "model: opus" in advisor_frontmatter
    assert "model: advisor" not in advisor_frontmatter
    assert "model: haiku" in executor_frontmatter
    assert "model: executor" not in executor_frontmatter

    source_agents = get_source_root() / "agents"
    assert "model: advisor" in _frontmatter(source_agents / f"{ADVISOR_AGENT}.agent.md")
    assert "model: executor" in _frontmatter(source_agents / f"{EXECUTOR_AGENT}.agent.md")


def test_deploy_claude_without_model_tiers_keeps_tier_names_and_notes_skip(tmp_path: Path):
    result = deploy(tmp_path)
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".claude" / "agents"
    assert "model: advisor" in _frontmatter(agents_dir / f"{ADVISOR_AGENT}.agent.md")
    assert "model: executor" in _frontmatter(agents_dir / f"{EXECUTOR_AGENT}.agent.md")
    assert "not configured" in result.output
    assert "[model_tiers]" in result.output


def test_deploy_claude_notes_non_claude_values(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "ollama:qwen3:32b"\nexecutor = "ollama:qwen3:8b"\n'
    )

    result = deploy(tmp_path)
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".claude" / "agents"
    assert "model: advisor" in _frontmatter(agents_dir / f"{ADVISOR_AGENT}.agent.md")
    assert "model: executor" in _frontmatter(agents_dir / f"{EXECUTOR_AGENT}.agent.md")
    assert "not Claude-recognizable" in result.output
    assert "ollama:qwen3:32b" in result.output


def test_diff_and_doctor_clean_after_materialized_deploy(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "opus"\nexecutor = "haiku"\n'
    )
    _deploy(tmp_path)

    diff_result = diff(tmp_path, exit_code=True)
    assert "changed" not in diff_result.output
    assert diff_result.exit_code == 0, diff_result.output

    doctor_result = doctor(tmp_path)
    assert "stale" not in doctor_result.output, doctor_result.output


def test_redeploy_with_materialized_tiers_is_idempotent(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "opus"\nexecutor = "haiku"\n'
    )
    _deploy(tmp_path)

    second = deploy(tmp_path)
    assert second.exit_code == 0, second.output
    # The second deploy writes identical materialized content, so every agent
    # reports unchanged rather than being rewritten.
    for line in second.output.splitlines():
        if line.strip().endswith(".agent.md"):
            assert "unchanged" in line, line

    diff_result = diff(tmp_path, exit_code=True)
    assert diff_result.exit_code == 0, diff_result.output


@pytest.mark.parametrize(
    ("tool", "agents_subdir"),
    [
        ("copilot", ".github/agents"),
        ("cursor", ".cursor/agents"),
        ("kiro", ".kiro/agents"),
    ],
)
def test_deploy_non_claude_tools_never_rewrite_model(tmp_path: Path, tool: str, agents_subdir: str):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "opus"\nexecutor = "haiku"\n'
    )

    _deploy(tmp_path, tool=tool)

    agents_dir = tmp_path / Path(agents_subdir)
    assert "model: advisor" in _frontmatter(agents_dir / f"{ADVISOR_AGENT}.agent.md")
    assert "model: executor" in _frontmatter(agents_dir / f"{EXECUTOR_AGENT}.agent.md")


def test_deploy_codex_materializes_model_and_reasoning_mappings(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "gpt-5.6"\nexecutor = "gpt-5.6-terra"\n\n'
        '[model_reasoning_efforts]\nadvisor = "high"\nexecutor = "medium"\n'
    )

    _deploy(tmp_path, tool="codex")

    agents_dir = tmp_path / ".codex" / "agents"
    advisor_agent = (agents_dir / f"{ADVISOR_AGENT}.toml").read_text(encoding="utf-8")
    executor_agent = (agents_dir / f"{EXECUTOR_AGENT}.toml").read_text(encoding="utf-8")
    assert 'model = "gpt-5.6"' in advisor_agent
    assert 'model_reasoning_effort = "high"' in advisor_agent
    assert 'model = "gpt-5.6-terra"' in executor_agent
    assert 'model_reasoning_effort = "medium"' in executor_agent

    diff_result = diff(tmp_path, tool="codex", exit_code=True)
    assert diff_result.exit_code == 0, diff_result.output

    doctor_result = doctor(tmp_path, tool="codex")
    assert "stale" not in doctor_result.output, doctor_result.output


def test_deploy_codex_without_mappings_inherits_model_and_reasoning(tmp_path: Path):
    _deploy(tmp_path, tool="codex")

    agent = (tmp_path / ".codex" / "agents" / f"{ADVISOR_AGENT}.toml").read_text(encoding="utf-8")
    assert "model =" not in agent
    assert "model_reasoning_effort =" not in agent


def test_deploy_claude_rewrites_only_recognizable_tier(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "ollama:qwen3:32b"\nexecutor = "haiku"\n'
    )

    result = deploy(tmp_path)
    assert result.exit_code == 0, result.output

    agents_dir = tmp_path / ".claude" / "agents"
    assert "model: advisor" in _frontmatter(agents_dir / f"{ADVISOR_AGENT}.agent.md")
    assert "model: haiku" in _frontmatter(agents_dir / f"{EXECUTOR_AGENT}.agent.md")
    assert "not Claude-recognizable" in result.output

    diff_result = diff(tmp_path, exit_code=True)
    assert diff_result.exit_code == 0, diff_result.output
