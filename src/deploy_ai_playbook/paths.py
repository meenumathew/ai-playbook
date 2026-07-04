"""Constants and path-related metadata for the playbook deploy CLI.

This module is intentionally I/O-free and dependency-light so it can be
imported by every other module without risk of circular imports.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path

# Captured at import time, before any uv/wrapper changes the cwd.
ORIGINAL_PWD = Path(os.getenv("PWD", str(Path.cwd())))

DISABLED_SUFFIX = ".disabled"
VERSION_FILE = ".playbook-version"
BACKUP_DIR = ".playbook-backup"
RULES_SOURCE_FILE = "CLAUDE.md"

ATLASSIAN_MCP_URL = "https://mcp.atlassian.com/mcp"


class Tool(StrEnum):
    """Supported deployment targets."""

    claude = "claude"
    copilot = "copilot"
    cursor = "cursor"
    kiro = "kiro"


# Per-tool deploy layout. Keys map source-tree directories to the
# tool-specific destination relative to the target project root.
TOOL_DESTINATIONS: dict[Tool, dict[str, str]] = {
    Tool.claude: {
        "agents": ".claude/agents",
        "knowledge-base": ".claude/knowledge-base",
        "skills": ".claude/skills",
        "templates": ".claude/templates",
        "commands": ".claude/commands",
        "rules": "CLAUDE.md",
    },
    Tool.copilot: {
        "agents": ".github/agents",
        "knowledge-base": ".github/knowledge-base",
        "skills": ".github/skills",
        "templates": ".github/templates",
        "commands": ".github/prompts",
        "rules": ".github/copilot-instructions.md",
    },
    Tool.cursor: {
        "agents": ".cursor/agents",
        "knowledge-base": ".cursor/knowledge-base",
        "skills": ".cursor/skills",
        "templates": ".cursor/templates",
        "commands": ".cursor/commands",
        "rules": ".cursor/rules/ai-playbook.mdc",
    },
    Tool.kiro: {
        "agents": ".kiro/agents",
        "knowledge-base": ".kiro/knowledge-base",
        "skills": ".kiro/skills",
        "templates": ".kiro/templates",
        "rules": ".kiro/steering/rules.md",
    },
}


# Per-tool MCP config — path and the JSON key under which servers are listed.
MCP_CONFIG: dict[Tool, dict[str, str]] = {
    Tool.claude: {
        "path": ".claude/settings.json",
        "key": "mcpServers",
    },
    Tool.copilot: {
        "path": ".vscode/mcp.json",
        "key": "servers",
    },
    Tool.cursor: {
        "path": ".cursor/mcp.json",
        "key": "mcpServers",
    },
    Tool.kiro: {
        "path": ".kiro/settings/mcp.json",
        "key": "mcpServers",
    },
}


# Language-specific KB files that can be filtered at deploy time.
LANGUAGE_FILES: dict[str, list[str]] = {
    "python": [
        "languages/python.md",
        "languages/testing-python.md",
    ],
}


# Harness files: source name → deployed path (relative to project root).
HARNESS_FILES: dict[str, str] = {
    "Makefile": "Makefile",
    "pre-commit-config.yaml": ".pre-commit-config.yaml",
    "ci.yml": ".github/workflows/ci.yml",
    "security.yml": ".github/workflows/security.yml",
    "check-teachback.sh": "harness/check-teachback.sh",
    "telemetry.sh": "harness/telemetry.sh",
    "read-budget.sh": "harness/read-budget.sh",
    "settings.example.json": "harness/settings.example.json",
}


def resolve_project_root(target_dir: str | None) -> Path:
    """Resolve the project root from --target-dir or ORIGINAL_PWD.

    Relative paths are resolved against ORIGINAL_PWD (captured before any
    process cwd changes), not the Python process cwd.
    """
    if target_dir is None:
        return ORIGINAL_PWD
    p = Path(target_dir)
    return p if p.is_absolute() else ORIGINAL_PWD / p
