"""Unit tests for paths helpers: logical $PWD capture.

$PWD is only meaningful straight from an interactive shell. Subprocesses
that change directory (subprocess with cwd=, make -C, CI runners) inherit
the caller's stale $PWD; trusting it blind retargets every write at the
wrong directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from deploy_ai_playbook.paths import _capture_original_pwd


def test_capture_ignores_stale_pwd_pointing_elsewhere(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    fake = tmp_path / "fake"
    real.mkdir()
    fake.mkdir()
    monkeypatch.chdir(real)
    monkeypatch.setenv("PWD", str(fake))

    assert _capture_original_pwd() == Path.cwd()


def test_capture_prefers_logical_pwd_when_it_resolves_to_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    monkeypatch.chdir(link)
    monkeypatch.setenv("PWD", str(link))

    assert _capture_original_pwd() == link


def test_capture_falls_back_to_cwd_when_pwd_unset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PWD", raising=False)

    assert _capture_original_pwd() == Path.cwd()
