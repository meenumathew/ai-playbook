"""Deploy service: pure helpers for the deploy command.

The Typer command in `cli.py` orchestrates printing; this module owns the
calculation: language filtering, path rewriting, agent selection, harness
file enumeration. Anything that does not need a Console lives here.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from pathlib import Path

from deploy_ai_playbook.config import (
    ModelReasoningConfig,
    ModelTierConfig,
    load_model_reasoning_config,
    load_model_tier_config,
)
from deploy_ai_playbook.discovery import OVERLAY_DIRS, DeployableFile
from deploy_ai_playbook.paths import (
    AGENT_FILE_SUFFIX,
    HARNESS_FILES,
    LANGUAGE_FILES,
    RULES_SOURCE_FILE,
    Tool,
)

# Values Claude Code accepts in an agent's `model:` frontmatter field, plus
# full model IDs. Anything else stays a tier name: the adopter's tool maps it.
CLAUDE_MODEL_KEYWORDS = frozenset({"opus", "sonnet", "haiku", "inherit"})

# The mapped value is interpolated into a frontmatter line of every deployed
# agent; a permissive prefix check would let a config value smuggle newlines
# (and with them arbitrary frontmatter keys) into the deployed files.
_CLAUDE_MODEL_ID = re.compile(r"^claude-[A-Za-z0-9._-]+$")

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
        if value in CLAUDE_MODEL_KEYWORDS or _CLAUDE_MODEL_ID.match(value):
            mapping[tier] = value
        else:
            skipped[tier] = value
    return mapping, skipped


def agent_model_tier_transform(
    tool: Tool,
    project_root: Path,
) -> tuple[Callable[[str], str] | None, list[str]]:
    """Build the deploy-time agent frontmatter transform for `tool`, plus notes to print.

    Claude keeps Markdown agents and can materialize its `model:` frontmatter.
    Codex uses standalone TOML custom-agent files, so the same source Markdown
    becomes native Codex `name` / `description` / `developer_instructions`.
    """
    if tool is Tool.codex:
        model_tiers = load_model_tier_config(project_root)
        reasoning = load_model_reasoning_config(project_root)
        return lambda content: codex_agent_toml(content, model_tiers, reasoning), []
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

    Scoped to the leading YAML frontmatter block only: prose mentions of tier
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


def codex_agent_toml(
    content: str,
    model_tiers: ModelTierConfig | None = None,
    reasoning: ModelReasoningConfig | None = None,
) -> str:
    """Convert one playbook Markdown agent into Codex's custom-agent TOML."""
    metadata, body = _split_agent_markdown(content)
    agent_name = metadata.get("id") or _slug(metadata.get("name", "agent"))
    description = metadata.get("description") or metadata.get("name") or agent_name
    tier = metadata.get("model")

    lines = [
        f"name = {_toml_string(agent_name)}",
        f"description = {_toml_string(description)}",
    ]
    model = _tier_value(model_tiers, tier)
    if model is not None:
        lines.append(f"model = {_toml_string(model)}")
    effort = _tier_value(reasoning, tier)
    if effort is not None:
        lines.append(f"model_reasoning_effort = {_toml_string(effort)}")
    lines.append(f"developer_instructions = {_toml_string(_codex_instructions(metadata, body))}")
    return "\n".join(lines) + "\n"


def _split_agent_markdown(content: str) -> tuple[dict[str, str], str]:
    if not content.startswith("---\n"):
        return {}, content
    try:
        frontmatter, body = content[4:].split("\n---\n", 1)
    except ValueError:
        return {}, content
    metadata: dict[str, str] = {}
    for raw_line in frontmatter.splitlines():
        if not raw_line or raw_line.startswith("#") or ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        metadata[key.strip()] = _frontmatter_value(value)
    return metadata, body.lstrip()


def _frontmatter_value(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
        return stripped[1:-1].replace(f"\\{stripped[0]}", stripped[0])
    return stripped


def _codex_instructions(metadata: dict[str, str], body: str) -> str:
    metadata_lines = [
        f"{key}: {value}"
        for key, value in metadata.items()
        if key not in {"description", "model", "name"}
    ]
    if not metadata_lines:
        return body
    return "Source agent metadata:\n" + "\n".join(metadata_lines) + "\n\n" + body


def _tier_value(
    config: ModelTierConfig | ModelReasoningConfig | None,
    tier: str | None,
) -> str | None:
    if config is None or tier not in {"advisor", "executor"}:
        return None
    return getattr(config, tier)


def _toml_string(value: str) -> str:
    # ensure_ascii would escape non-BMP characters as UTF-16 surrogate
    # pairs (\ud83d...), which JSON allows but TOML rejects. Keeping the
    # characters literal is valid in both. DEL and C1 controls go the
    # other way: JSON leaves them literal but TOML basic strings forbid
    # them, so escape those explicitly.
    encoded = json.dumps(value, ensure_ascii=False)
    return re.sub(r"[\x7f-\x9f]", lambda m: f"\\u{ord(m.group()):04x}", encoded)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "agent"


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
