"""Target adapters for tool-specific deployment behavior."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from deploy_ai_playbook.errors import AIPlaybookError
from deploy_ai_playbook.paths import MCP_CONFIG, TOOL_DESTINATIONS, Tool

COMMAND_ARGUMENTS_PLACEHOLDER = "$ARGUMENTS"


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
    natural_language_command_note: str | None = None,
) -> TargetAdapter:
    return TargetAdapter(
        tool=tool,
        destinations=MappingProxyType(dict(TOOL_DESTINATIONS[tool])),
        mcp_config=McpConfig(**MCP_CONFIG[tool]),
        command_output_suffix=command_output_suffix,
        command_argument_placeholder=command_argument_placeholder,
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
