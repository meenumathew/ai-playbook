"""Unit tests for target adapter metadata and command transforms."""

import pytest

from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.targets import (
    TARGET_ADAPTERS,
    UnsupportedTargetCapabilityError,
    get_target_adapter,
)


def test_target_adapter_registry_covers_every_tool() -> None:
    assert set(TARGET_ADAPTERS) == set(Tool)


def test_claude_adapter_exposes_layout_and_mcp_metadata() -> None:
    adapter = get_target_adapter(Tool.claude)

    assert adapter.destination("agents") == ".claude/agents"
    assert adapter.destination("rules") == "CLAUDE.md"
    assert adapter.rules_filename == "CLAUDE.md"
    assert adapter.mcp_config.path == ".claude/settings.json"
    assert adapter.mcp_config.key == "mcpServers"


def test_copilot_adapter_transforms_commands() -> None:
    adapter = get_target_adapter(Tool.copilot)

    output_name, content = adapter.transform_command(
        "story-refiner.md",
        "Run with $ARGUMENTS",
    )

    assert adapter.supports_commands is True
    assert output_name == "story-refiner.prompt.md"
    assert content == "Run with ${input:arguments}"


def test_cursor_adapter_supports_commands_and_mdc_rules() -> None:
    adapter = get_target_adapter(Tool.cursor)

    assert adapter.supports_commands is True
    assert adapter.destination("agents") == ".cursor/agents"
    assert adapter.destination("commands") == ".cursor/commands"
    assert adapter.destination("rules") == ".cursor/rules/ai-playbook.mdc"
    assert adapter.rules_filename == "ai-playbook.mdc"
    assert adapter.mcp_config.path == ".cursor/mcp.json"
    assert adapter.mcp_config.key == "mcpServers"

    output_name, content = adapter.transform_command(
        "story-refiner.md",
        "Run with $ARGUMENTS",
    )
    assert output_name == "story-refiner.md"
    assert content == "Run with $ARGUMENTS"


def test_codex_adapter_uses_native_toml_agents_and_no_commands() -> None:
    adapter = get_target_adapter(Tool.codex)

    assert adapter.supports_commands is False
    assert adapter.agent_output_suffix == ".toml"
    assert adapter.agent_output_name("story-refiner.agent.md") == "story-refiner.toml"
    assert adapter.destination("agents") == ".codex/agents"
    assert adapter.destination("skills") == ".agents/skills"
    assert adapter.destination("rules") == "AGENTS.md"
    assert adapter.mcp_config.path == ".codex/config.toml"
    assert adapter.mcp_config.key == "mcp_servers"
    with pytest.raises(UnsupportedTargetCapabilityError):
        adapter.transform_command("story-refiner.md", "Run with $ARGUMENTS")


def test_kiro_adapter_declares_no_slash_command_support() -> None:
    adapter = get_target_adapter(Tool.kiro)

    assert adapter.supports_commands is False
    assert "commands" not in adapter.destinations
    assert adapter.natural_language_command_note is not None
    with pytest.raises(UnsupportedTargetCapabilityError):
        adapter.transform_command("story-refiner.md", "Run with $ARGUMENTS")
