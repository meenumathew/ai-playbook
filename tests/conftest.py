"""Fixtures shared by every test package."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def deterministic_cli_rendering(monkeypatch: pytest.MonkeyPatch) -> None:
    """Render CLI output identically on a developer machine and on CI.

    Typer decides `FORCE_TERMINAL` at import time from `GITHUB_ACTIONS`,
    `FORCE_COLOR`, and `PY_COLORS`, so Rich colours its output on CI and
    leaves it plain locally. Colour is not cosmetic here: Click's error
    formatter styles an option name as its own span, which splits `--tool`
    into two escape-wrapped pieces, so a substring the user plainly reads on
    screen is absent from `result.output`. Width matters for the same reason,
    because Rich wraps a panel at the console width.

    Pinning both makes an assertion about rendered text mean one thing
    everywhere, and makes a local run able to fail the way CI fails.
    """
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setenv("COLUMNS", "80")
