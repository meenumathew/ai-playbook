"""Shared constants used across the acceptance test files.

Kept private (leading underscore) to signal "test plumbing, not a public API".
Pytest does not auto-collect this module because it doesn't start with `test_`.
"""

from __future__ import annotations

from deploy_ai_playbook.paths import Tool

# Agents whose deployed body is expected to reference each subsystem path.
# Used by the cross-product parametrize that asserts every agent's deployed
# copy has the right tool-specific path prefix and no unrewritten root refs.
AGENTS_WITH_KB_REFS = {
    "diff-reviewer",
    "code-inspector",
    "docs-maintainer",
    "slice-planner",
    "story-refiner",
}
AGENTS_WITH_SKILLS_REFS = {
    "story-refiner",
    "xp-pair-programmer",
    "slice-planner",
}
AGENTS_WITH_TEMPLATE_REFS = {"slice-planner", "story-refiner"}

# (Tool, agents subdir, agent suffix, kb prefix, skills prefix, templates prefix)
TOOL_MATRIX = [
    (
        Tool.claude,
        ".claude/agents",
        ".agent.md",
        ".claude/knowledge-base/",
        ".claude/skills/",
        ".claude/templates/",
    ),
    (
        Tool.copilot,
        ".github/agents",
        ".agent.md",
        ".github/knowledge-base/",
        ".github/skills/",
        ".github/templates/",
    ),
    (
        Tool.codex,
        ".codex/agents",
        ".toml",
        ".codex/knowledge-base/",
        ".agents/skills/",
        ".codex/templates/",
    ),
    (
        Tool.cursor,
        ".cursor/agents",
        ".agent.md",
        ".cursor/knowledge-base/",
        ".cursor/skills/",
        ".cursor/templates/",
    ),
    (
        Tool.kiro,
        ".kiro/agents",
        ".agent.md",
        ".kiro/knowledge-base/",
        ".kiro/skills/",
        ".kiro/templates/",
    ),
]
