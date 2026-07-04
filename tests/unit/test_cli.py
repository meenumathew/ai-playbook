"""Unit tests for deploy_ai_playbook.cli — pure functions and helpers in isolation.

Filesystem use is limited to `tmp_path` and exercises a single helper with no
CLI-runner invocation. CLI-boundary tests live in `tests/acceptance/`.
"""

from pathlib import Path

import pytest
import typer

from deploy_ai_playbook.cli import (
    DISABLED_SUFFIX,
    ORIGINAL_PWD,
    VERSION_FILE,
    Tool,
    _deployed_quality_tier,
    _resolve_project_root,
    compute_source_fingerprint,
    copy_directory,
    copy_file,
    deploy_mcp_config,
    diff_file,
    discover_agents,
    find_deployed_agent,
    get_source_root,
    resolve_agent_names,
    write_version_file,
)
from tests import ALL_AGENTS


def test_tool_enum_values():
    assert Tool.claude.value == "claude"
    assert Tool.copilot.value == "copilot"
    assert Tool.cursor.value == "cursor"
    assert Tool.kiro.value == "kiro"


def test_version_flag_prints_package_version():
    """Standard CLI convention — `--version` returns the package version + exit 0."""
    from typer.testing import CliRunner

    from deploy_ai_playbook import __version__
    from deploy_ai_playbook.cli import app

    result = CliRunner().invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_version_short_flag_works():
    """`-V` is the documented short alias for `--version`."""
    from typer.testing import CliRunner

    from deploy_ai_playbook import __version__
    from deploy_ai_playbook.cli import app

    result = CliRunner().invoke(app, ["-V"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_resolve_agent_names_all_returns_every_agent():
    agents = {name: Path(name) for name in ALL_AGENTS}
    assert resolve_agent_names("all", agents) == ALL_AGENTS


def test_resolve_agent_names_csv_returns_subset():
    agents = {name: Path(name) for name in ALL_AGENTS}
    assert resolve_agent_names("story-refiner,xp-pair-programmer", agents) == [
        "story-refiner",
        "xp-pair-programmer",
    ]


def test_resolve_agent_names_unknown_raises_typed_error():
    """Library raises a structured ValueError; presentation lives in cli.py."""
    from deploy_ai_playbook.discovery import UnknownAgentError

    with pytest.raises(UnknownAgentError) as exc:
        resolve_agent_names("nonexistent", {"story-refiner": Path("story-refiner")})
    assert exc.value.unknown == ["nonexistent"]
    assert exc.value.available == ["story-refiner"]
    assert exc.value.label == "agent"


def test_resolve_agent_names_or_exit_translates_to_typer_exit():
    """CLI wrapper renders the error and exits 1 — thin presentation layer."""
    from deploy_ai_playbook.cli import _resolve_agent_names_or_exit

    with pytest.raises(typer.Exit) as exc:
        _resolve_agent_names_or_exit("nonexistent", {"story-refiner": Path("story-refiner")})
    assert exc.value.exit_code == 1


# ---------------------------------------------------------------------------
# get_source_root / discover_agents
# ---------------------------------------------------------------------------


def test_get_source_root_returns_path_with_agents_dir():
    root = get_source_root()
    assert (root / "agents").exists()


def test_get_source_root_prefers_bundled_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When a 'data' dir exists next to discovery.py, it's used as source root."""
    import deploy_ai_playbook.discovery as discovery_module

    fake_module = tmp_path / "discovery.py"
    fake_module.write_text("")
    bundled = tmp_path / "data"
    bundled.mkdir()

    monkeypatch.setattr(discovery_module, "__file__", str(fake_module))
    from deploy_ai_playbook.cli import get_source_root as _get_source_root

    assert _get_source_root() == bundled


def test_discover_agents_returns_all_shipped_agents(sample_source_root: Path):
    agents = discover_agents(sample_source_root)
    assert list(agents.keys()) == ALL_AGENTS


def test_discover_agents_returns_empty_when_dir_missing(tmp_path: Path):
    assert discover_agents(tmp_path) == {}


def test_discover_agents_ignores_non_agent_files(tmp_path: Path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "story-refiner.agent.md").write_text("agent")
    (agents_dir / "README.md").write_text("docs")
    (agents_dir / "notes.txt").write_text("notes")

    agents = discover_agents(tmp_path)

    assert list(agents.keys()) == ["story-refiner"]


# ---------------------------------------------------------------------------
# find_deployed_agent
# ---------------------------------------------------------------------------


def test_find_deployed_agent_prefers_active_over_disabled(tmp_path: Path):
    active = tmp_path / "story-refiner.agent.md"
    disabled = tmp_path / f"story-refiner.agent.md{DISABLED_SUFFIX}"
    active.write_text("active")
    disabled.write_text("disabled")

    path, is_disabled = find_deployed_agent(tmp_path, "story-refiner")

    assert path == active
    assert is_disabled is False


def test_find_deployed_agent_finds_disabled_when_active_missing(tmp_path: Path):
    disabled = tmp_path / f"story-refiner.agent.md{DISABLED_SUFFIX}"
    disabled.write_text("agent")

    path, is_disabled = find_deployed_agent(tmp_path, "story-refiner")

    assert path == disabled
    assert is_disabled is True


# ---------------------------------------------------------------------------
# copy_file / copy_directory
# ---------------------------------------------------------------------------


def test_copy_file_rewrite_substitutes_text(tmp_path: Path):
    src = tmp_path / "src.md"
    src.write_text("see knowledge-base/domain-language.md for terms")
    dst = tmp_path / "dst.md"

    status = copy_file(
        src,
        dst,
        dry_run=False,
        rewrite={"knowledge-base/": ".github/knowledge-base/"},
    )

    assert dst.read_text() == "see .github/knowledge-base/domain-language.md for terms"
    assert "copied" in status


def test_copy_file_reports_unchanged_when_identical(tmp_path: Path):
    src = tmp_path / "src.md"
    dst = tmp_path / "dst.md"
    src.write_text("same content")
    dst.write_text("same content")

    status = copy_file(src, dst, dry_run=False)

    assert "unchanged" in status


def test_copy_file_dry_run_returns_would_copy(tmp_path: Path):
    src = tmp_path / "src.md"
    src.write_text("content")

    status = copy_file(src, tmp_path / "dst.md", dry_run=True)

    assert "would copy" in status
    assert not (tmp_path / "dst.md").exists()


def test_copy_file_copies_binary_files_without_utf8_decode(tmp_path: Path):
    src = tmp_path / "image.bin"
    content = b"\x89PNG\r\n\x1a\n\x80"
    src.write_bytes(content)
    dst = tmp_path / "dst.bin"

    status = copy_file(src, dst, dry_run=False, rewrite={"knowledge-base/": ".claude/"})

    assert "copied" in status
    assert dst.read_bytes() == content


def test_copy_directory_skips_hidden_files(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "visible.md").write_text("content")
    (src / ".DS_Store").write_bytes(b"ignored")

    results = copy_directory(src, tmp_path / "dst", dry_run=False)

    assert results == [("visible.md", "[green]copied[/green]")]


def test_copy_directory_reports_skipped_files(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "keep.md").write_text("keep")
    (src / "skip.md").write_text("skip")

    results = copy_directory(src, tmp_path / "dst", dry_run=False, skip_files={"skip.md"})

    status_map = dict(results)
    assert "copied" in status_map["keep.md"]
    assert "skipped" in status_map["skip.md"]


# ---------------------------------------------------------------------------
# diff_file
# ---------------------------------------------------------------------------


def test_diff_file_returns_none_when_identical(tmp_path: Path):
    src = tmp_path / "src.md"
    dst = tmp_path / "dst.md"
    src.write_text("same content")
    dst.write_text("same content")

    assert diff_file(src, dst) is None


def test_diff_file_returns_changed_when_different(tmp_path: Path):
    src = tmp_path / "src.md"
    dst = tmp_path / "dst.md"
    src.write_text("new content")
    dst.write_text("old content")

    result = diff_file(src, dst)

    assert result is not None
    assert "changed" in result


def test_diff_file_returns_not_deployed_when_missing(tmp_path: Path):
    src = tmp_path / "src.md"
    src.write_text("content")

    result = diff_file(src, tmp_path / "missing.md")

    assert result is not None
    assert "not deployed" in result


def test_diff_file_applies_rewrite_before_comparing(tmp_path: Path):
    src = tmp_path / "src.md"
    dst = tmp_path / "dst.md"
    src.write_text("see knowledge-base/foo.md")
    dst.write_text("see .claude/knowledge-base/foo.md")

    result = diff_file(src, dst, rewrite={"knowledge-base/": ".claude/knowledge-base/"})

    assert result is None


def test_diff_file_compares_binary_files_without_utf8_decode(tmp_path: Path):
    content = b"\x89PNG\r\n\x1a\n\x80"
    src = tmp_path / "src.bin"
    dst = tmp_path / "dst.bin"
    src.write_bytes(content)
    dst.write_bytes(content)

    assert diff_file(src, dst, rewrite={"knowledge-base/": ".claude/"}) is None


# ---------------------------------------------------------------------------
# compute_source_fingerprint
# ---------------------------------------------------------------------------


def _discover(root: Path) -> list:
    from deploy_ai_playbook.discovery import discover_layered

    return discover_layered(root, packs=[]).files


def test_compute_source_fingerprint_skips_missing_subdirs(tmp_path: Path):
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir()
    (agents_dir / "a.agent.md").write_text("agent")

    fingerprint = compute_source_fingerprint(tmp_path, _discover(tmp_path))

    assert isinstance(fingerprint, str)
    assert len(fingerprint) == 12


def test_compute_source_fingerprint_includes_rules_file(tmp_path: Path):
    (tmp_path / "CLAUDE.md").write_text("rules v1")
    fp1 = compute_source_fingerprint(tmp_path, _discover(tmp_path))

    (tmp_path / "CLAUDE.md").write_text("rules v2")
    fp2 = compute_source_fingerprint(tmp_path, _discover(tmp_path))

    assert fp1 != fp2


def test_compute_source_fingerprint_skips_language_files(tmp_path: Path):
    languages = tmp_path / "knowledge-base" / "languages"
    languages.mkdir(parents=True)
    (languages / "python.md").write_text("python")
    typescript = languages / "typescript.md"
    typescript.write_text("typescript v1")

    fp1 = compute_source_fingerprint(
        tmp_path, _discover(tmp_path), skip_files={"languages/typescript.md"}
    )
    typescript.write_text("typescript v2")
    fp2 = compute_source_fingerprint(
        tmp_path, _discover(tmp_path), skip_files={"languages/typescript.md"}
    )

    assert fp1 == fp2


# ---------------------------------------------------------------------------
# write_version_file
# ---------------------------------------------------------------------------


def test_write_version_file_dry_run_does_not_write(tmp_path: Path):
    status = write_version_file(tmp_path, tmp_path, Tool.claude, dry_run=True)

    assert "would write" in status
    assert not (tmp_path / VERSION_FILE).exists()


def test_write_version_file_writes_metadata(tmp_path: Path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "a.agent.md").write_text("agent")

    status = write_version_file(tmp_path, tmp_path, Tool.claude, dry_run=False)

    assert "written" in status
    content = (tmp_path / VERSION_FILE).read_text()
    assert "playbook-fingerprint:" in content
    assert "deployed-at:" in content
    assert "tool: claude" in content
    assert "language: all" in content


def test_write_version_file_records_language_filter(tmp_path: Path):
    (tmp_path / "agents").mkdir()
    (tmp_path / "agents" / "a.agent.md").write_text("agent")

    status = write_version_file(
        tmp_path,
        tmp_path,
        Tool.claude,
        dry_run=False,
        language="python",
    )

    assert "written" in status
    assert "language: python" in (tmp_path / VERSION_FILE).read_text()


# ---------------------------------------------------------------------------
# _resolve_project_root
# ---------------------------------------------------------------------------


def test_resolve_project_root_helpers(tmp_path: Path):
    assert _resolve_project_root(None) == ORIGINAL_PWD
    assert _resolve_project_root(str(tmp_path)) == tmp_path
    assert _resolve_project_root("some/relative/path") == ORIGINAL_PWD / "some/relative/path"


# ---------------------------------------------------------------------------
# deploy_mcp_config
# ---------------------------------------------------------------------------


def test_deploy_mcp_config_dry_run(tmp_path: Path):
    status = deploy_mcp_config(tmp_path, Tool.claude, dry_run=True)

    assert "would configure" in status
    assert not (tmp_path / ".claude" / "settings.json").exists()


def test_deploy_mcp_config_preserves_malformed_json_and_reports_error(tmp_path: Path):
    config_path = tmp_path / ".claude" / "settings.json"
    config_path.parent.mkdir(parents=True)
    original = "not valid json {{{"
    config_path.write_text(original)

    status = deploy_mcp_config(tmp_path, Tool.claude, dry_run=False)

    assert "malformed JSON" in status
    # Original file is NOT overwritten with {} — user data preserved.
    assert config_path.read_text() == original
    # A timestamped backup copy was written alongside it.
    backups = list(config_path.parent.glob("settings.json.broken-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == original


def test_deploy_mcp_config_preserves_non_object_top_level_json(tmp_path: Path):
    """Valid-but-non-object JSON (e.g. `[]`) gets the same protection as
    malformed JSON: preserve the file, save a `.broken-*` copy, report an
    actionable error — never crash, never silently rewrite."""
    config_path = tmp_path / ".claude" / "settings.json"
    config_path.parent.mkdir(parents=True)
    original = "[]"
    config_path.write_text(original)

    status = deploy_mcp_config(tmp_path, Tool.claude, dry_run=False)

    assert "not a JSON object" in status
    assert config_path.read_text() == original
    backups = list(config_path.parent.glob("settings.json.broken-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == original


def test_deployed_quality_tier_ignores_empty_tier_value(tmp_path: Path):
    """A deployed rules file whose `quality-tier:` line was edited to an empty
    value must be treated as no declared tier, not crash with IndexError."""
    rules_path = tmp_path / "CLAUDE.md"
    rules_path.write_text("quality-tier:\n")

    assert _deployed_quality_tier(tmp_path, Tool.claude) == ""


def test_deploy_mcp_config_overwrites_existing_atlassian_with_different_url(tmp_path: Path):
    """If `mcpServers.atlassian` exists with a different URL, deploy updates it
    to the canonical URL and reports `configured` (not `already configured`).

    Pins the documented behaviour. A user-customised atlassian URL is a real
    edge case (self-hosted Jira, alternate proxy); the deploy CLI standardises
    on the canonical URL but **must preserve every other server entry**.
    """
    import json

    from deploy_ai_playbook.paths import ATLASSIAN_MCP_URL

    config_path = tmp_path / ".claude" / "settings.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "atlassian": {"type": "http", "url": "https://self-hosted.example.com/mcp"},
                    "custom": {"url": "http://other.example.com"},
                }
            }
        )
    )

    status = deploy_mcp_config(tmp_path, Tool.claude, dry_run=False)

    assert "configured" in status and "already" not in status, (
        f"Different-URL case must report `configured`, not `already configured`: {status!r}"
    )
    config = json.loads(config_path.read_text())
    assert config["mcpServers"]["atlassian"]["url"] == ATLASSIAN_MCP_URL, (
        "atlassian URL must be standardised to the canonical URL"
    )
    # Other servers must survive — the conflict resolution is per-key, not whole-file.
    assert config["mcpServers"]["custom"] == {"url": "http://other.example.com"}, (
        "other MCP servers must be preserved when atlassian is updated"
    )


def test_deploy_mcp_config_recovers_from_non_dict_server_collection(tmp_path: Path):
    import json

    config_path = tmp_path / ".claude" / "settings.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(json.dumps({"mcpServers": []}))

    status = deploy_mcp_config(tmp_path, Tool.claude, dry_run=False)

    assert "configured" in status
    config = json.loads(config_path.read_text())
    assert "atlassian" in config["mcpServers"]


def test_deploy_mcp_config_rapid_redeploy_does_not_collide(tmp_path: Path):
    """Calling backup_deployed_files twice in tight succession must not raise."""
    from deploy_ai_playbook.cli import backup_deployed_files

    # Set up a deployed tree to back up.
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "a.agent.md").write_text("x")

    first = backup_deployed_files(tmp_path, Tool.claude)
    second = backup_deployed_files(tmp_path, Tool.claude)
    third = backup_deployed_files(tmp_path, Tool.claude)

    assert first is not None and second is not None and third is not None
    assert first != second != third
    assert first.exists() and second.exists() and third.exists()


# ---------------------------------------------------------------------------
# Section 6: CLI surface contracts
# ---------------------------------------------------------------------------


def test_root_help_includes_quickstart_epilog():
    """`ai-playbook --help` must orient new users with a quick-start hint."""
    import click
    from typer.testing import CliRunner

    from deploy_ai_playbook.cli import app

    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    # Whitespace-collapse so terminal-width wrapping doesn't break the assertion.
    flat = " ".join(click.unstyle(result.output).split())
    assert "Quick start:" in flat
    assert "ai-playbook deploy --tool claude --dry-run" in flat
    assert "Claude, Copilot, Cursor, or Kiro" in flat


def test_errors_route_to_stderr_not_stdout():
    """Error output must land on stderr so CI can keep stdout clean for JSON.

    The CLI uses two Rich consoles: `console` for normal output (stdout) and
    `error_console` for `[red]Error:[/red]` messages (stderr). Adopters who
    pipe `ai-playbook ... --json | jq ...` need stderr to absorb the error
    text without corrupting the JSON pipeline. CliRunner exposes `mix_stderr=
    False` to keep the streams separate.
    """
    from typer.testing import CliRunner

    from deploy_ai_playbook.cli import app

    runner = CliRunner()
    result = runner.invoke(
        app, ["deploy", "--agent", "no-such-agent", "--tool", "claude", "--dry-run"]
    )

    assert result.exit_code == 1
    # Whitespace-collapse — Rich wraps long lines to terminal width.
    out_flat = " ".join(result.stdout.split())
    err_flat = " ".join(result.stderr.split())
    # The error text is in stderr.
    assert "Unknown" in err_flat or "Error" in err_flat
    # And it is NOT mixed into stdout.
    assert "Error" not in out_flat
    assert "Unknown" not in out_flat


def test_no_agents_error_suggests_list_command():
    """When deploy can't find agents, the error must point at `ai-playbook list`.

    Ensures first-time users get a recovery hint instead of a low-level path.
    """
    from typer.testing import CliRunner

    import deploy_ai_playbook.cli as cli_module
    from deploy_ai_playbook.cli import app

    runner = CliRunner()
    fake_source = Path("/nonexistent-source-for-cli-test")
    monkey_target = lambda: fake_source  # noqa: E731 — one-line CLI source patch
    original = cli_module.get_source_root
    try:
        cli_module.get_source_root = monkey_target
        result = runner.invoke(app, ["deploy", "--agent", "all", "--tool", "claude", "--dry-run"])
    finally:
        cli_module.get_source_root = original

    assert result.exit_code == 1
    flat = " ".join(result.stderr.split())
    assert "ai-playbook list" in flat
