"""Unit tests for codex MCP config merging (`~/.codex/config.toml`).

The codex path edits a TOML file the adopter also edits by hand; every
branch below protects that file from being corrupted (duplicate table
declarations are invalid TOML) or silently overwritten.
"""

from __future__ import annotations

import tomllib
from pathlib import Path
from types import SimpleNamespace
from typing import cast

from deploy_ai_playbook.mcp import (
    _deploy_codex_mcp_config,
    _next_toml_table,
    _toml_error_location,
)
from deploy_ai_playbook.paths import ATLASSIAN_MCP_URL


def _broken_copies(config: Path) -> list[Path]:
    return sorted(config.parent.glob(f"{config.name}.broken-*"))


def test_codex_config_created_when_missing(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[green]configured[/green]"
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL


def test_codex_config_appends_block_preserving_existing_tables(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[profile]\nname = "dev"\n', encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[green]configured[/green]"
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["profile"]["name"] == "dev"
    assert parsed["mcp_servers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL


def test_codex_config_appends_even_without_trailing_newline(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text('[profile]\nname = "dev"', encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[green]configured[/green]"
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["profile"]["name"] == "dev"
    assert parsed["mcp_servers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL


def test_codex_config_already_configured_leaves_file_untouched(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = f'[mcp_servers.atlassian]\nurl = "{ATLASSIAN_MCP_URL}"\n'
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[dim]already configured[/dim]"
    assert config.read_text(encoding="utf-8") == original


def test_codex_config_replaces_stale_url_within_its_own_table(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text(
        "[mcp_servers.atlassian]\n"
        'url = "https://old.example"\n'
        "\n"
        "[other]\n"
        'url = "https://keep.example"\n',
        encoding="utf-8",
    )

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[green]configured[/green]"
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL
    assert parsed["other"]["url"] == "https://keep.example", (
        "the rewrite must stay inside the atlassian table"
    )


def test_codex_config_inserts_url_when_table_has_none(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    config.write_text("[mcp_servers.atlassian]\ntimeout = 5\n", encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert status == "[green]configured[/green]"
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL
    assert parsed["mcp_servers"]["atlassian"]["timeout"] == 5


def test_codex_config_malformed_toml_preserved_not_overwritten(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    broken = "not = valid = toml\n"
    config.write_text(broken, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "malformed TOML" in status
    assert config.read_text(encoding="utf-8") == broken
    assert _broken_copies(config), "a .broken-<ts> copy must be saved for recovery"


def test_codex_config_non_utf8_preserved_not_overwritten(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = b"\xff\xfe"
    config.write_bytes(original)

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "not valid UTF-8" in status
    assert config.read_bytes() == original
    broken_copies = _broken_copies(config)
    assert len(broken_copies) == 1
    assert broken_copies[0].read_bytes() == original


def test_codex_config_non_table_mcp_servers_is_refused(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = "mcp_servers = 3\n"
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "non-table mcp_servers" in status
    assert config.read_text(encoding="utf-8") == original
    assert _broken_copies(config)


def test_codex_config_non_table_atlassian_is_refused(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = "[mcp_servers]\natlassian = 5\n"
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "non-table mcp_servers.atlassian" in status
    assert config.read_text(encoding="utf-8") == original
    assert _broken_copies(config)


def test_codex_config_inline_table_shape_is_refused(tmp_path: Path) -> None:
    """An inline-table entry cannot be line-upserted; appending a second
    `[mcp_servers.atlassian]` declaration would be invalid TOML."""
    config = tmp_path / "config.toml"
    original = 'mcp_servers = { atlassian = { url = "https://old.example" } }\n'
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "unsupported TOML shape" in status
    assert config.read_text(encoding="utf-8") == original
    assert _broken_copies(config)


def test_next_toml_table_finds_next_header_and_defaults_to_eof() -> None:
    lines = ["url = 1", "# comment", "[next]", "x = 2"]

    assert _next_toml_table(lines, 0) == 2
    assert _next_toml_table(lines, 3) == len(lines)


def test_next_toml_table_ignores_non_header_bracket_lines() -> None:
    lines = ["[broken", "value = [", "]", "[real]"]

    assert _next_toml_table(lines, 0) == 3


def test_toml_error_location_formats_position_when_present() -> None:
    exc = cast(tomllib.TOMLDecodeError, SimpleNamespace(lineno=3, colno=7))

    assert _toml_error_location(exc) == "(line 3, col 7): "


def test_toml_error_location_empty_when_position_missing() -> None:
    exc = cast(tomllib.TOMLDecodeError, SimpleNamespace())

    assert _toml_error_location(exc) == ""


def test_codex_config_empty_inline_mcp_servers_is_refused(tmp_path: Path) -> None:
    """An empty inline `mcp_servers = {}` is closed TOML; appending a
    `[mcp_servers.atlassian]` header would redeclare it invalidly."""
    config = tmp_path / "config.toml"
    original = "mcp_servers = {}\n"
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "unsupported TOML shape" in status
    assert config.read_text(encoding="utf-8") == original
    assert _broken_copies(config)


def test_codex_config_empty_inline_atlassian_is_refused(tmp_path: Path) -> None:
    config = tmp_path / "config.toml"
    original = "[mcp_servers]\natlassian = {}\n"
    config.write_text(original, encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "unsupported TOML shape" in status
    assert config.read_text(encoding="utf-8") == original
    assert _broken_copies(config)


def test_codex_config_other_server_header_still_appends(tmp_path: Path) -> None:
    """A sibling `[mcp_servers.github]` header table must not trip the
    inline-shape refusal; appending a new header table is valid there."""
    config = tmp_path / "config.toml"
    config.write_text('[mcp_servers.github]\nurl = "https://example.com"\n', encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "configured" in status
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["atlassian"]["url"]
    assert parsed["mcp_servers"]["github"]["url"] == "https://example.com"


def test_codex_upsert_preserves_url_prefixed_sibling_keys(tmp_path: Path) -> None:
    """`url_timeout = 5` must survive: only the exact `url` key is rewritten."""
    config = tmp_path / "config.toml"
    config.write_text("[mcp_servers.atlassian]\nurl_timeout = 5\n", encoding="utf-8")

    status = _deploy_codex_mcp_config(config, tmp_path)

    assert "configured" in status
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed["mcp_servers"]["atlassian"]["url_timeout"] == 5
    assert parsed["mcp_servers"]["atlassian"]["url"]
