"""Dependency-free Semantic Version precedence."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import total_ordering

_SEMVER_RE = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


@total_ordering
@dataclass(frozen=True, slots=True)
class SemanticVersion:
    """An immutable SemVer value ordered by the 2.0.0 precedence rules."""

    major: int
    minor: int
    patch: int
    prerelease: tuple[str, ...] = ()
    build: tuple[str, ...] = field(default=(), compare=False)

    @classmethod
    def parse(cls, value: str) -> SemanticVersion | None:
        match = _SEMVER_RE.fullmatch(value)
        if match is None:
            return None
        prerelease = tuple(match.group(4).split(".")) if match.group(4) else ()
        if any(_has_numeric_leading_zero(identifier) for identifier in prerelease):
            return None
        build = tuple(match.group(5).split(".")) if match.group(5) else ()
        return cls(
            major=int(match.group(1)),
            minor=int(match.group(2)),
            patch=int(match.group(3)),
            prerelease=prerelease,
            build=build,
        )

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        own_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        if own_core != other_core:
            return own_core < other_core
        if not self.prerelease:
            return False
        if not other.prerelease:
            return True
        return _prerelease_is_lower(self.prerelease, other.prerelease)


def _has_numeric_leading_zero(identifier: str) -> bool:
    return identifier.isdigit() and len(identifier) > 1 and identifier.startswith("0")


def _prerelease_is_lower(own: tuple[str, ...], other: tuple[str, ...]) -> bool:
    for own_identifier, other_identifier in zip(own, other, strict=False):
        if own_identifier == other_identifier:
            continue
        own_is_numeric = own_identifier.isdigit()
        other_is_numeric = other_identifier.isdigit()
        if own_is_numeric and other_is_numeric:
            return int(own_identifier) < int(other_identifier)
        if own_is_numeric != other_is_numeric:
            return own_is_numeric
        return own_identifier < other_identifier
    return len(own) < len(other)
