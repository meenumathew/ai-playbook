"""Semantic Version parsing and precedence tests."""

import pytest

from deploy_ai_playbook.semantic_version import SemanticVersion


def _version(value: str) -> SemanticVersion:
    parsed = SemanticVersion.parse(value)
    assert parsed is not None
    return parsed


def test_semver_orders_numeric_and_alphanumeric_prereleases() -> None:
    ordered = [
        "1.0.0-alpha",
        "1.0.0-alpha.1",
        "1.0.0-alpha.beta",
        "1.0.0-beta",
        "1.0.0-beta.2",
        "1.0.0-beta.11",
        "1.0.0-rc.1",
        "1.0.0",
    ]

    assert sorted(_version(value) for value in reversed(ordered)) == [
        _version(value) for value in ordered
    ]


def test_semver_build_metadata_does_not_change_precedence() -> None:
    assert _version("1.2.3+build.1") == _version("1.2.3+build.99")


def test_semver_rejects_numeric_identifiers_with_leading_zeroes() -> None:
    assert SemanticVersion.parse("01.2.3") is None
    assert SemanticVersion.parse("1.2.3-alpha.01") is None


def test_semver_rejects_non_ascii_core_digits() -> None:
    assert SemanticVersion.parse("1.٢.3") is None


def test_semver_ordering_against_a_foreign_type_raises_type_error() -> None:
    """Comparing to a non-version defers to Python instead of inventing an order.

    `__lt__` returns NotImplemented, so the operand mismatch surfaces as a
    TypeError. Returning False instead would let `sorted()` silently accept a
    list of mixed types and produce a meaningless order.
    """
    with pytest.raises(TypeError):
        _ = _version("1.2.3") < "1.2.4"
