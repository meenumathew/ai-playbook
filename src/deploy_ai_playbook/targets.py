"""Target adapters for tool-specific deployment behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from deploy_ai_playbook.errors import AIPlaybookError
from deploy_ai_playbook.paths import AGENT_FILE_SUFFIX, MCP_CONFIG, TOOL_DESTINATIONS, Tool

COMMAND_ARGUMENTS_PLACEHOLDER = "$ARGUMENTS"
SOURCE_AGENT_SUFFIX = AGENT_FILE_SUFFIX


class UnsupportedTargetCapabilityError(ValueError, AIPlaybookError):
    """Raised when a target is asked to perform an unsupported operation."""


@dataclass(frozen=True, slots=True)
class McpConfig:
    """MCP configuration location and server collection key for a target."""

    path: str
    key: str


@dataclass(frozen=True, slots=True)
class TargetAdapter:
    """Tool-specific deployment metadata and small target transformations."""

    tool: Tool
    destinations: Mapping[str, str]
    mcp_config: McpConfig
    command_output_suffix: str | None
    command_argument_placeholder: str | None
    agent_output_suffix: str = SOURCE_AGENT_SUFFIX
    natural_language_command_note: str | None = None

    @property
    def supports_commands(self) -> bool:
        return self.command_output_suffix is not None and "commands" in self.destinations

    @property
    def rules_filename(self) -> str:
        return Path(self.destination("rules")).name

    def destination(self, key: str) -> str:
        return self.destinations[key]

    def optional_destination(self, key: str) -> str | None:
        return self.destinations.get(key)

    def agent_output_name(self, source_name: str) -> str:
        agent_name = source_name.removesuffix(SOURCE_AGENT_SUFFIX)
        return f"{agent_name}{self.agent_output_suffix}"

    def deployed_overlay_relative(self, overlay_dir: str, relative: Path) -> Path:
        if overlay_dir != "agents":
            return relative
        return relative.with_name(self.agent_output_name(relative.name))

    def transform_command(self, source_name: str, content: str) -> tuple[str, str]:
        if not self.supports_commands or self.command_output_suffix is None:
            raise UnsupportedTargetCapabilityError(
                f"{self.tool.value} does not support deployed slash commands"
            )
        output_name = f"{Path(source_name).stem}{self.command_output_suffix}"
        placeholder = self.command_argument_placeholder or COMMAND_ARGUMENTS_PLACEHOLDER
        return output_name, content.replace(COMMAND_ARGUMENTS_PLACEHOLDER, placeholder)


def _adapter(
    tool: Tool,
    command_output_suffix: str | None,
    command_argument_placeholder: str | None,
    agent_output_suffix: str = SOURCE_AGENT_SUFFIX,
    natural_language_command_note: str | None = None,
) -> TargetAdapter:
    return TargetAdapter(
        tool=tool,
        destinations=MappingProxyType(dict(TOOL_DESTINATIONS[tool])),
        mcp_config=McpConfig(**MCP_CONFIG[tool]),
        command_output_suffix=command_output_suffix,
        command_argument_placeholder=command_argument_placeholder,
        agent_output_suffix=agent_output_suffix,
        natural_language_command_note=natural_language_command_note,
    )


TARGET_ADAPTERS: Mapping[Tool, TargetAdapter] = MappingProxyType(
    {
        Tool.claude: _adapter(
            Tool.claude,
            command_output_suffix=".md",
            command_argument_placeholder=COMMAND_ARGUMENTS_PLACEHOLDER,
        ),
        Tool.copilot: _adapter(
            Tool.copilot,
            command_output_suffix=".prompt.md",
            command_argument_placeholder="${input:arguments}",
        ),
        Tool.codex: _adapter(
            Tool.codex,
            command_output_suffix=None,
            command_argument_placeholder=None,
            agent_output_suffix=".toml",
            natural_language_command_note=(
                "Codex does not use deployed slash-command shims; invoke custom agents by name."
            ),
        ),
        Tool.cursor: _adapter(
            Tool.cursor,
            command_output_suffix=".md",
            command_argument_placeholder=COMMAND_ARGUMENTS_PLACEHOLDER,
        ),
        Tool.kiro: _adapter(
            Tool.kiro,
            command_output_suffix=None,
            command_argument_placeholder=None,
            natural_language_command_note=(
                "Kiro does not support deployed slash commands; invoke agents by name."
            ),
        ),
    }
)


def get_target_adapter(tool: Tool) -> TargetAdapter:
    """Return the adapter for an existing Tool enum value."""
    return TARGET_ADAPTERS[tool]
