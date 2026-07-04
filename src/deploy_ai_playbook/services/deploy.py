"""Deploy service — pure helpers for the deploy command.

The Typer command in `cli.py` orchestrates printing; this module owns the
calculation: language filtering, path rewriting, agent selection, harness
file enumeration. Anything that does not need a Console lives here.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from pathlib import Path

from deploy_ai_playbook.config import ModelTierConfig, load_model_tier_config
from deploy_ai_playbook.discovery import OVERLAY_DIRS, DeployableFile
from deploy_ai_playbook.paths import HARNESS_FILES, LANGUAGE_FILES, RULES_SOURCE_FILE, Tool

AGENT_FILE_SUFFIX = ".agent.md"

# Values Claude Code accepts in an agent's `model:` frontmatter field, plus
# full model IDs. Anything else stays a tier name — the adopter's tool maps it.
CLAUDE_MODEL_KEYWORDS = frozenset({"opus", "sonnet", "haiku", "inherit"})

_MODEL_TIER_LINE = re.compile(r"^model:\s*(advisor|executor)\s*$")


def claude_model_tier_mapping(
    model_tiers: ModelTierConfig | None,
) -> tuple[dict[str, str], dict[str, str]]:
    """Split the adopter's tier mapping into Claude-recognizable and skipped.

    Returns (mapping, skipped): `mapping` holds tier → model for values Claude
    Code understands natively (opus/sonnet/haiku/inherit or a `claude-*` model
    ID); `skipped` holds tier → value for everything else, so deploy can note
    why those tiers keep their names.
    """
    mapping: dict[str, str] = {}
    skipped: dict[str, str] = {}
    if model_tiers is None:
        return mapping, skipped
    for tier, value in (("advisor", model_tiers.advisor), ("executor", model_tiers.executor)):
        if value is None:
            continue
        if value in CLAUDE_MODEL_KEYWORDS or value.startswith("claude-"):
            mapping[tier] = value
        else:
            skipped[tier] = value
    return mapping, skipped


def agent_model_tier_transform(
    tool: Tool,
    project_root: Path,
) -> tuple[Callable[[str], str] | None, list[str]]:
    """Build the deploy-time agent frontmatter transform for `tool`, plus notes to print.

    Only the `claude` target has a native per-agent `model:` field, so every
    other tool gets no transform and no note (CLAUDE.md § Model Tier stays
    documentation-only for those adopters, exactly as before this feature).
    """
    if tool is not Tool.claude:
        return None, []
    model_tiers = load_model_tier_config(project_root)
    mapping, skipped = claude_model_tier_mapping(model_tiers)
    notes: list[str] = []
    if model_tiers is None:
        notes.append(
            "Model tiers not configured — deployed agents keep tier names "
            "(add [model_tiers] to .ai-playbook.toml to route advisor/executor "
            "to real models)."
        )
    for tier, value in sorted(skipped.items()):
        notes.append(
            f"Model tier '{tier}' = \"{value}\" is not Claude-recognizable "
            "(expected opus/sonnet/haiku/inherit or a claude-* model ID) — "
            f"{tier} agents keep the tier name."
        )
    if not mapping:
        return None, notes
    return lambda content: materialize_model_tier(content, mapping), notes


def materialize_model_tier(content: str, mapping: dict[str, str]) -> str:
    """Rewrite `model: advisor|executor` frontmatter lines to the mapped model.

    Scoped to the leading YAML frontmatter block only — prose mentions of tier
    names are never touched. Content without frontmatter, or with an empty
    mapping, is returned unchanged.
    """
    if not mapping or not content.startswith("---\n"):
        return content
    lines = content.split("\n")
    for index, line in enumerate(lines[1:], start=1):
        if line == "---":
            break
        match = _MODEL_TIER_LINE.match(line)
        if match and match.group(1) in mapping:
            lines[index] = f"model: {mapping[match.group(1)]}"
    return "\n".join(lines)


def normalize_language_filter(language: str | None) -> str | None:
    """Validate and normalize an optional language filter.

    Returns the lowercase filter name, None if no filter, or raises ValueError
    if the language is not in LANGUAGE_FILES.
    """
    if language is None:
        return None
    language_filter = language.lower()
    if language_filter not in LANGUAGE_FILES:
        raise ValueError(
            f"Unknown language '{language}'. Available: {', '.join(LANGUAGE_FILES.keys())}"
        )
    return language_filter


def language_skip_files(language_filter: str | None) -> set[str]:
    """Return KB files omitted by a normalized language filter."""
    if language_filter is None:
        return set()
    skipped: set[str] = set()
    for language_name, files in LANGUAGE_FILES.items():
        if language_name != language_filter:
            skipped.update(files)
    return skipped


def path_rewrite(destinations: Mapping[str, str]) -> dict[str, str]:
    """Build the source-path → deployed-path rewrite map.

    Includes the rules-file alias for non-Claude targets: deployed content
    citing `CLAUDE.md` must point at the file the adopter actually has
    (`.github/copilot-instructions.md`, `.cursor/rules/ai-playbook.mdc`,
    `.kiro/steering/rules.md`).
    """
    rewrite = {
        "knowledge-base/": f"{destinations['knowledge-base']}/",
        "skills/": f"{destinations['skills']}/",
        "templates/": f"{destinations['templates']}/",
    }
    rules_destination = destinations["rules"]
    if rules_destination != RULES_SOURCE_FILE:
        rewrite[RULES_SOURCE_FILE] = rules_destination
    return rewrite


def group_deployable_files_by_overlay(
    discovered_files: list[DeployableFile],
) -> dict[str, list[DeployableFile]]:
    """Group discovered files by their overlay directory in OVERLAY_DIRS order."""
    files_by_overlay: dict[str, list[DeployableFile]] = {dir_name: [] for dir_name in OVERLAY_DIRS}
    for entry in discovered_files:
        overlay = entry.relative.parts[0]
        if overlay in files_by_overlay:
            files_by_overlay[overlay].append(entry)
    return files_by_overlay


def agent_filtered_out(
    entry: DeployableFile,
    overlay_dir: str,
    agent_names: set[str],
) -> bool:
    """Return True if entry is an agent file outside the requested selection."""
    if overlay_dir != "agents":
        return False
    agent_name = entry.relative.name.removesuffix(AGENT_FILE_SUFFIX)
    return agent_name not in agent_names


def iter_harness_files(
    harness_dir: Path,
    project_root: Path,
) -> list[tuple[Path, str, Path]]:
    """Yield (src_file, dst_relative, dst_absolute) for shipped harness files that exist."""
    files: list[tuple[Path, str, Path]] = []
    for src_name, dst_rel in HARNESS_FILES.items():
        src_file = harness_dir / src_name
        if src_file.exists():
            files.append((src_file, dst_rel, project_root / dst_rel))
    return files
