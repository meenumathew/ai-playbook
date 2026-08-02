"""Typed, backward-compatible deployment record values."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ScopeKind(StrEnum):
    """Whether a deployment covers the complete supported surface."""

    full = "full"
    partial = "partial"


@dataclass(frozen=True, slots=True)
class DeploymentScope:
    """The source surfaces selected by one deploy operation."""

    kind: ScopeKind = ScopeKind.full
    agents: tuple[str, ...] = ()
    rules: bool = True
    commands: bool = True
    harness: bool = True
    mcp: bool = True

    @property
    def is_partial(self) -> bool:
        return self.kind is ScopeKind.partial

    @property
    def fingerprint_agent_names(self) -> set[str] | None:
        if not self.is_partial:
            return None
        return set(self.agents)

    def as_dict(self) -> dict[str, object]:
        return {
            "agents": list(self.agents),
            "commands": self.commands,
            "harness": self.harness,
            "kind": self.kind.value,
            "mcp": self.mcp,
            "rules": self.rules,
        }


@dataclass(frozen=True, slots=True)
class DeploymentRecord:
    """What the last deploy selected and fingerprinted."""

    fingerprint: str | None = None
    deployed_at: str | None = None
    tool: str | None = None
    language: str | None = None
    packs: list[str] = field(default_factory=list)
    scope: DeploymentScope = field(default_factory=DeploymentScope)


def parse_deployment_record(text: str) -> DeploymentRecord:
    """Parse ``.playbook-version`` content; scope fields are optional with full-scope defaults."""
    values: dict[str, str] = {}
    packs: list[str] = []
    agents: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if key == "pack":
            packs.append(value)
        elif key == "agent":
            agents.append(value)
        else:
            values[key] = value

    kind = ScopeKind.partial if values.get("scope") == ScopeKind.partial else ScopeKind.full
    scope = DeploymentScope(
        kind=kind,
        agents=tuple(agents),
        rules=_parse_bool(values.get("rules"), default=True),
        commands=_parse_bool(values.get("commands"), default=True),
        harness=_parse_bool(values.get("harness"), default=True),
        mcp=_parse_bool(values.get("mcp"), default=True),
    )
    return DeploymentRecord(
        fingerprint=values.get("playbook-fingerprint"),
        deployed_at=values.get("deployed-at"),
        tool=values.get("tool"),
        language=values.get("language"),
        packs=packs,
        scope=scope,
    )


def deployment_record_text(record: DeploymentRecord) -> str:
    """Serialize a record in the existing human-readable line format."""
    lines = [
        f"playbook-fingerprint: {record.fingerprint or ''}",
        f"deployed-at: {record.deployed_at or ''}",
        f"tool: {record.tool or ''}",
        f"language: {record.language or 'all'}",
        f"scope: {record.scope.kind.value}",
    ]
    lines.extend(f"agent: {name}" for name in record.scope.agents)
    lines.extend(
        (
            f"rules: {_bool_text(record.scope.rules)}",
            f"commands: {_bool_text(record.scope.commands)}",
            f"harness: {_bool_text(record.scope.harness)}",
            f"mcp: {_bool_text(record.scope.mcp)}",
        )
    )
    lines.extend(f"pack: {pack}" for pack in record.packs)
    return "\n".join(lines) + "\n"


def _parse_bool(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default
    normalized = value.lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return default


def _bool_text(value: bool) -> str:
    return "true" if value else "false"
