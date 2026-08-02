"""Constants and path-related metadata for the playbook deploy CLI.

This module is intentionally I/O-free and dependency-light so it can be
imported by every other module without risk of circular imports.
"""

from __future__ import annotations

import os
from contextlib import suppress
from enum import StrEnum
from pathlib import Path


def _capture_original_pwd() -> Path:
    """Prefer the shell's logical $PWD, but only when it is the real cwd.

    $PWD is inherited by subprocesses that change directory (subprocess
    with cwd=, make -C, CI runners), where it still points at the caller's
    directory. Trusting it blind would aim every write at the wrong tree,
    so it is used only when it resolves to the actual cwd: keeping the
    symlinked-path spelling the user typed: and ignored otherwise.
    """
    cwd = Path.cwd()
    pwd = os.getenv("PWD")
    if not pwd:
        return cwd
    candidate = Path(pwd)
    with suppress(OSError):
        if candidate.resolve() == cwd.resolve():
            return candidate
    return cwd


# Captured at import time, before any uv/wrapper changes the cwd.
ORIGINAL_PWD = _capture_original_pwd()

# Single source of truth for the agent-file suffix: fs, targets, discovery,
# and the deploy/diff services all filter on it; drift produces subtle
# selection bugs.
AGENT_FILE_SUFFIX = ".agent.md"

DISABLED_SUFFIX = ".disabled"
VERSION_FILE = ".playbook-version"
BACKUP_DIR = ".playbook-backup"
RULES_SOURCE_FILE = "CLAUDE.md"

ATLASSIAN_MCP_URL = "https://mcp.atlassian.com/mcp"


class Tool(StrEnum):
    """Supported deployment targets."""

    claude = "claude"
    copilot = "copilot"
    codex = "codex"
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
    Tool.codex: {
        "agents": ".codex/agents",
        "knowledge-base": ".codex/knowledge-base",
        "skills": ".agents/skills",
        "templates": ".codex/templates",
        "rules": "AGENTS.md",
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


# Per-tool MCP config: path and the JSON key under which servers are listed.
MCP_CONFIG: dict[Tool, dict[str, str]] = {
    Tool.claude: {
        "path": ".claude/settings.json",
        "key": "mcpServers",
    },
    Tool.copilot: {
        "path": ".vscode/mcp.json",
        "key": "servers",
    },
    Tool.codex: {
        "path": ".codex/config.toml",
        "key": "mcp_servers",
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
    # security.yml's SHA-pinned Actions rely on Dependabot for weekly bumps:
    # ship the config that makes that claim true.
    "dependabot.yml": ".github/dependabot.yml",
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
