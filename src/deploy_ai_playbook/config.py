"""Adopter-side `.ai-playbook.toml` reader for playbook configuration."""

from __future__ import annotations

import re
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from types import MappingProxyType
from typing import Any, NoReturn

from deploy_ai_playbook.errors import AIPlaybookError

PACK_CONFIG_FILE = ".ai-playbook.toml"
PACK_METADATA_FILE = "pack.toml"
QUALITY_TIER_VALUES = frozenset({"production", "prototype"})
_VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:[-+][0-9A-Za-z.-]+)?$")


class ConfigError(ValueError, AIPlaybookError):
    """Raised when `.ai-playbook.toml` or pack metadata is invalid."""


@dataclass(frozen=True, slots=True)
class PackMetadata:
    """Optional metadata declared by a pack-local `pack.toml` manifest."""

    name: str
    version: str | None = None
    min_playbook_version: str | None = None
    max_playbook_version: str | None = None


@dataclass(frozen=True, slots=True)
class Source:
    """A discoverable source of deployable files (core or pack)."""

    origin: str
    root: Path
    metadata: PackMetadata | None = None


@dataclass(frozen=True, slots=True)
class ModelTierConfig:
    """Model mapping declared by adopter-side `.ai-playbook.toml`."""

    advisor: str | None = None
    executor: str | None = None


@dataclass(frozen=True, slots=True)
class QualityTierConfig:
    """Per-agent quality tier overrides from `.ai-playbook.toml`."""

    agent_overrides: Mapping[str, str]


def load_pack_config(project_root: Path) -> list[Source]:
    """Read `.ai-playbook.toml` from the project root and return pack sources in declared order.

    Returns an empty list if the config file is absent.
    """
    config = _read_playbook_config(project_root)
    if config is None:
        return []

    pack_paths = _validate_pack_paths(config.get("packs", []))
    sources: list[Source] = []
    seen_roots: set[Path] = set()
    seen_names: set[str] = set()
    for pack in pack_paths:
        pack_root = _resolve_pack_root(project_root, pack)
        if not pack_root.is_dir():
            _config_error(f"Pack directory does not exist: {pack} (resolved to {pack_root})")
        pack_real = pack_root.resolve()
        if pack_real in seen_roots:
            _config_error(f"Duplicate pack path: {pack}")
        seen_roots.add(pack_real)
        metadata = _load_pack_metadata(pack_root)
        if metadata.name in seen_names:
            _config_error(f"Duplicate pack name: {metadata.name}")
        seen_names.add(metadata.name)
        sources.append(Source(origin=f"pack:{metadata.name}", root=pack_root, metadata=metadata))
    return sources


def load_model_tier_config(project_root: Path) -> ModelTierConfig | None:
    """Read optional `[model_tiers]` mapping from `.ai-playbook.toml`."""
    config = _read_playbook_config(project_root)
    if config is None:
        return None
    raw_model_tiers = config.get("model_tiers")
    if raw_model_tiers is None:
        return None
    if not isinstance(raw_model_tiers, dict):
        _config_error("`model_tiers` must be a table with advisor/executor strings")
    return ModelTierConfig(
        advisor=_optional_non_empty_string(raw_model_tiers, "advisor", "model_tiers"),
        executor=_optional_non_empty_string(raw_model_tiers, "executor", "model_tiers"),
    )


def load_issue_tracker_provider(project_root: Path) -> str | None:
    """Read the optional `[issue-tracker].provider` from `.ai-playbook.toml`.

    Drives MCP auto-configuration during deploy: only `jira` triggers the
    Atlassian MCP entry; any other provider (or none) leaves MCP setup to the
    adopter, keeping the deploy PM-tool agnostic.
    """
    config = _read_playbook_config(project_root)
    if config is None:
        return None
    raw_tracker = config.get("issue-tracker")
    if raw_tracker is None:
        return None
    if not isinstance(raw_tracker, dict):
        _config_error("`issue-tracker` must be a table with a `provider` string")
    provider = _optional_non_empty_string(raw_tracker, "provider", "issue-tracker")
    return provider.lower() if provider is not None else None


def load_quality_tier_config(project_root: Path) -> QualityTierConfig:
    """Read optional per-agent quality tier overrides from `.ai-playbook.toml`."""
    config = _read_playbook_config(project_root)
    if config is None:
        return QualityTierConfig(agent_overrides=MappingProxyType({}))
    raw_quality_tiers = config.get("quality_tiers")
    if raw_quality_tiers is None:
        return QualityTierConfig(agent_overrides=MappingProxyType({}))
    if not isinstance(raw_quality_tiers, dict):
        _config_error("`quality_tiers` must be a table")
    raw_agent_overrides = raw_quality_tiers.get("agents", {})
    if not isinstance(raw_agent_overrides, dict):
        _config_error("`quality_tiers.agents` must be a table of agent names to tiers")
    return QualityTierConfig(
        agent_overrides=MappingProxyType(_quality_tier_overrides(raw_agent_overrides))
    )


def _read_playbook_config(project_root: Path) -> dict[str, Any] | None:
    config_path = project_root / PACK_CONFIG_FILE
    if not config_path.exists():
        return None
    try:
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        _config_error(f"Malformed {PACK_CONFIG_FILE}: {exc}", cause=exc)
    if not isinstance(config, dict):
        _config_error(f"{PACK_CONFIG_FILE} must contain a TOML table")
    return config


def _optional_non_empty_string(data: dict[str, Any], field: str, table: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _config_error(f"`{table}.{field}` must be a non-empty string")
    return value.strip()


def _quality_tier_overrides(raw_agent_overrides: dict[str, Any]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for agent_name, tier in raw_agent_overrides.items():
        if not agent_name.strip():
            _config_error("`quality_tiers.agents` agent names must be non-empty")
        if not isinstance(tier, str):
            _config_error(f"`quality_tiers.agents.{agent_name}` must be a string")
        normalized_tier = tier.strip().lower()
        if normalized_tier not in QUALITY_TIER_VALUES:
            allowed = ", ".join(sorted(QUALITY_TIER_VALUES))
            _config_error(f"`quality_tiers.agents.{agent_name}` must be one of: {allowed}")
        overrides[agent_name.strip()] = normalized_tier
    return overrides


def _load_pack_metadata(pack_root: Path) -> PackMetadata:
    metadata_path = pack_root / PACK_METADATA_FILE
    if not metadata_path.exists():
        return PackMetadata(name=pack_root.name)
    try:
        data = tomllib.loads(metadata_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        _config_error(f"Malformed {metadata_path}: {exc}", cause=exc)

    metadata = PackMetadata(
        name=_metadata_name(data, metadata_path, default=pack_root.name),
        version=_metadata_version(data, metadata_path, "version"),
        min_playbook_version=_metadata_version(data, metadata_path, "min_playbook_version"),
        max_playbook_version=_metadata_version(data, metadata_path, "max_playbook_version"),
    )
    _validate_pack_compatibility(metadata, metadata_path)
    return metadata


def _metadata_name(data: dict[str, Any], metadata_path: Path, default: str) -> str:
    value = data.get("name", default)
    if not isinstance(value, str) or not value.strip():
        _config_error(f"{metadata_path}: `name` must be a non-empty string")
    return value.strip()


def _metadata_version(data: dict[str, Any], metadata_path: Path, field: str) -> str | None:
    value = data.get(field)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        _config_error(f"{metadata_path}: `{field}` must be a semantic-version string")
    version = value.strip()
    if _version_key(version) is None:
        _config_error(f"{metadata_path}: `{field}` must be a semantic-version string")
    return version


def _version_key(version: str) -> tuple[int, int, int] | None:
    match = _VERSION_RE.match(version)
    if match is None:
        return None
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def _validate_pack_compatibility(metadata: PackMetadata, metadata_path: Path) -> None:
    current_version = current_playbook_version()
    current = _version_key(current_version)
    if current is None:
        return
    min_version = metadata.min_playbook_version
    min_key = _version_key(min_version) if min_version else None
    if min_version and min_key and current < min_key:
        _config_error(
            f"{metadata_path}: pack {metadata.name} requires ai-playbook >= "
            f"{min_version} (current {current_version})"
        )
    max_version = metadata.max_playbook_version
    max_key = _version_key(max_version) if max_version else None
    if max_version and max_key and current > max_key:
        _config_error(
            f"{metadata_path}: pack {metadata.name} requires ai-playbook <= "
            f"{max_version} (current {current_version})"
        )


def current_playbook_version() -> str:
    """Return the running ai-playbook version, falling back to local pyproject."""
    try:
        return version("ai-playbook")
    except PackageNotFoundError:
        return _local_pyproject_version() or "0.0.0+unknown"


def _local_pyproject_version() -> str | None:
    for parent in Path(__file__).resolve().parents:
        pyproject_path = parent / "pyproject.toml"
        if not pyproject_path.exists():
            continue
        try:
            data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError):
            continue
        project = data.get("project")
        if not isinstance(project, dict) or project.get("name") != "ai-playbook":
            continue
        project_version = project.get("version")
        if isinstance(project_version, str) and project_version.strip():
            return project_version.strip()
    return None


def _validate_pack_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        _config_error("`packs` must be a list of project-relative path strings")

    packs: list[str] = []
    seen: set[str] = set()
    for index, pack in enumerate(value):
        if not isinstance(pack, str):
            _config_error(f"`packs[{index}]` must be a path string")
        if not pack.strip():
            _config_error(f"`packs[{index}]` must not be empty")
        if pack in seen:
            _config_error(f"Duplicate pack path: {pack}")
        seen.add(pack)
        packs.append(pack)
    return packs


def _resolve_pack_root(project_root: Path, pack: str) -> Path:
    pack_path = Path(pack)
    if pack_path.is_absolute():
        _config_error(f"Pack path must be relative to the project root: {pack}")

    pack_root = project_root / pack_path
    project_real = project_root.resolve()
    pack_real = pack_root.resolve()
    try:
        pack_real.relative_to(project_real)
    except ValueError as exc:
        _config_error(f"Pack path must stay inside the project root: {pack}", cause=exc)
    return pack_root


def _config_error(message: str, cause: Exception | None = None) -> NoReturn:
    if cause is None:
        raise ConfigError(message)
    raise ConfigError(message) from cause
