"""Acceptance tests for `ai-playbook deploy`: driven through the CLI boundary."""

import re
from pathlib import Path

import pytest

from deploy_ai_playbook.cli import VERSION_FILE, Tool, app
from deploy_ai_playbook.paths import ATLASSIAN_MCP_URL
from deploy_ai_playbook.safety import WriteAccessError
from tests import ALL_AGENTS
from tests.acceptance._dsl import (
    assert_agent_deployed,
    assert_agent_not_deployed,
    deploy,
    runner,
)
from tests.acceptance._helpers import (
    AGENTS_WITH_KB_REFS,
    AGENTS_WITH_SKILLS_REFS,
    AGENTS_WITH_TEMPLATE_REFS,
    TOOL_MATRIX,
)


def test_deploy_dry_run_does_not_write_files(tmp_path: Path):
    result = deploy(tmp_path, dry_run=True)
    assert result.exit_code == 0
    assert "would copy" in result.output
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / VERSION_FILE).exists()


def test_deploy_csv_agents_deploys_only_named(tmp_path: Path):
    result = deploy(tmp_path, agents="story-refiner,xp-pair-programmer")
    assert result.exit_code == 0

    assert_agent_deployed(tmp_path, "story-refiner")
    assert_agent_deployed(tmp_path, "xp-pair-programmer")
    assert_agent_not_deployed(tmp_path, "slice-planner")

    commands_dir = tmp_path / ".claude" / "commands"
    assert (commands_dir / "story-refiner.md").exists()
    assert (commands_dir / "xp-pair-programmer.md").exists()
    assert (commands_dir / "status.md").exists()
    assert not (commands_dir / "slice-planner.md").exists()


def test_deploy_rejects_symlinked_destination_file(tmp_path: Path):
    """Deploy must not follow adopter-side symlinks out of the target tree."""
    outside = tmp_path / "outside.md"
    outside.write_text("do not overwrite")
    agents_dir = tmp_path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "story-refiner.agent.md").symlink_to(outside)

    result = deploy(tmp_path, agents="story-refiner")

    assert result.exit_code == 1
    assert "Unsafe destination" in result.output
    assert outside.read_text() == "do not overwrite"


def test_deploy_rejects_symlinked_mcp_config(tmp_path: Path):
    """Deploy must not write MCP settings through adopter-side symlinks."""
    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = "jira"\n')
    outside = tmp_path / "outside-settings.json"
    outside.write_text("{}")
    settings_dir = tmp_path / ".claude"
    settings_dir.mkdir()
    (settings_dir / "settings.json").symlink_to(outside)

    result = deploy(tmp_path, agents="story-refiner", harness=False)

    assert result.exit_code == 1
    assert "Unsafe destination" in result.output
    assert outside.read_text() == "{}"


def test_deploy_exits_nonzero_when_mcp_merge_fails(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = "jira"\n')
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("not json {{{")

    result = deploy(tmp_path, agents="story-refiner", harness=False)

    assert result.exit_code == 1
    assert "malformed JSON" in result.output
    assert settings_path.read_text() == "not json {{{"


def test_deploy_exits_nonzero_when_telemetry_merge_fails(tmp_path: Path):
    settings_path = tmp_path / ".claude" / "settings.json"
    settings_path.parent.mkdir(parents=True)
    settings_path.write_text("[]")

    result = deploy(tmp_path, agents="story-refiner", mcp=False)

    assert result.exit_code == 1
    # Rich wraps output at terminal width and the wrap point shifts with
    # tmp-path length (xdist workers add a path segment): compare on
    # whitespace-normalized text so the assertion is wrap-insensitive.
    assert "not a JSON object" in " ".join(result.output.split())
    assert settings_path.read_text() == "[]"


def test_deploy_rejects_symlinked_harness_directory(tmp_path: Path):
    """Deploy must not copy starter harness files through symlinked directories."""
    outside = tmp_path / "outside-harness"
    outside.mkdir()
    (tmp_path / "harness").symlink_to(outside, target_is_directory=True)

    result = deploy(tmp_path, agents="story-refiner", mcp=False)

    assert result.exit_code == 1
    assert "Unsafe destination" in result.output
    assert not any(outside.iterdir())


def test_deploy_all_agents_copies_full_asset_set(tmp_path: Path):
    result = deploy(tmp_path)
    assert result.exit_code == 0

    agents_dir = tmp_path / ".claude" / "agents"
    commands_dir = tmp_path / ".claude" / "commands"
    kb_dir = tmp_path / ".claude" / "knowledge-base"
    skills_dir = tmp_path / ".claude" / "skills"
    templates_dir = tmp_path / ".claude" / "templates"

    for name in ALL_AGENTS:
        assert (agents_dir / f"{name}.agent.md").exists()
        assert (commands_dir / f"{name}.md").exists()

    assert (tmp_path / "CLAUDE.md").exists()
    assert any(kb_dir.rglob("*.md"))
    assert any(skills_dir.rglob("*.md"))
    assert (templates_dir / "plan-template.md").exists()
    assert (templates_dir / "quality-gates-template.md").exists()
    assert (templates_dir / "research-template.md").exists()
    assert (templates_dir / "review-template.md").exists()
    assert (templates_dir / "how-to-template.md").exists()
    assert (templates_dir / "runbook-template.md").exists()
    assert (templates_dir / "story-template.md").exists()


def test_deploy_copilot_commands_use_prompt_extension(tmp_path: Path):
    result = deploy(tmp_path, tool="copilot")
    assert result.exit_code == 0

    prompts_dir = tmp_path / ".github" / "prompts"
    for name in ALL_AGENTS:
        prompt_path = prompts_dir / f"{name}.prompt.md"
        assert prompt_path.exists()
        content = prompt_path.read_text()
        assert "${input:arguments}" in content
        assert "$ARGUMENTS" not in content


def test_deploy_cursor_commands_use_md_extension(tmp_path: Path):
    result = deploy(tmp_path, tool="cursor")
    assert result.exit_code == 0

    commands_dir = tmp_path / ".cursor" / "commands"
    for name in ALL_AGENTS:
        command_path = commands_dir / f"{name}.md"
        assert command_path.exists()
        content = command_path.read_text()
        assert "$ARGUMENTS" in content
        assert "${input:arguments}" not in content
        assert not (commands_dir / f"{name}.prompt.md").exists()


def test_deploy_kiro_has_no_commands_dir(tmp_path: Path):
    result = deploy(tmp_path, tool="kiro")
    assert result.exit_code == 0
    assert not (tmp_path / ".kiro" / "commands").exists()


def test_codex_deploy_materializes_native_project_surfaces(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "gpt-5.6"\nexecutor = "gpt-5.6-terra"\n\n'
        '[model_reasoning_efforts]\nadvisor = "high"\nexecutor = "medium"\n'
    )

    result = deploy(tmp_path, agents="story-refiner,xp-pair-programmer", tool="codex")

    assert result.exit_code == 0, result.output
    assert (tmp_path / "AGENTS.md").exists()
    assert (tmp_path / ".codex" / "agents" / "story-refiner.toml").exists()
    assert (tmp_path / ".codex" / "agents" / "xp-pair-programmer.toml").exists()
    assert not (tmp_path / ".codex" / "commands").exists()
    assert (tmp_path / ".agents" / "skills" / "git" / "SKILL.md").exists()
    assert (tmp_path / ".codex" / "knowledge-base" / "testing.md").exists()
    assert (tmp_path / ".codex" / "templates" / "story-template.md").exists()

    story_refiner = (tmp_path / ".codex" / "agents" / "story-refiner.toml").read_text()
    assert 'name = "story-refiner"' in story_refiner
    assert 'description = "Refines ideas' in story_refiner
    assert 'model = "gpt-5.6"' in story_refiner
    assert 'model_reasoning_effort = "high"' in story_refiner
    assert "developer_instructions = " in story_refiner
    assert "# Story Refiner Agent" in story_refiner

    xp_pair = (tmp_path / ".codex" / "agents" / "xp-pair-programmer.toml").read_text()
    assert 'model = "gpt-5.6-terra"' in xp_pair
    assert 'model_reasoning_effort = "medium"' in xp_pair

    diff = runner.invoke(app, ["diff", "--tool", "codex", "-t", str(tmp_path), "--exit-code"])
    assert diff.exit_code == 0, diff.output

    doctor = runner.invoke(app, ["doctor", "--tool", "codex", "-t", str(tmp_path)])
    assert doctor.exit_code == 0, doctor.output
    assert "stale" not in doctor.output

    status = runner.invoke(app, ["status", "--tool", "codex", "-t", str(tmp_path)])
    assert status.exit_code == 0, status.output
    assert "story-refiner" in status.output

    disable = runner.invoke(
        app, ["disable", "story-refiner", "--tool", "codex", "-t", str(tmp_path)]
    )
    assert disable.exit_code == 0, disable.output
    assert (tmp_path / ".codex" / "agents" / "story-refiner.toml.disabled").exists()

    enable = runner.invoke(app, ["enable", "story-refiner", "--tool", "codex", "-t", str(tmp_path)])
    assert enable.exit_code == 0, enable.output
    assert (tmp_path / ".codex" / "agents" / "story-refiner.toml").exists()

    orphan = tmp_path / ".codex" / "agents" / "retired-agent.toml"
    orphan.write_text("# stale", encoding="utf-8")
    prune = deploy(
        tmp_path, agents="story-refiner,xp-pair-programmer", tool="codex", prune=True, yes=True
    )
    assert prune.exit_code == 0, prune.output
    assert "pruned" in prune.output
    assert not orphan.exists()


# ---------------------------------------------------------------------------
# MCP config deployment
# ---------------------------------------------------------------------------


def _configure_jira_provider(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = "jira"\n')


def test_deploy_creates_mcp_config_for_claude(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    result = deploy(tmp_path)
    assert result.exit_code == 0

    import json

    mcp_path = tmp_path / ".claude" / "settings.json"
    assert mcp_path.exists()
    config = json.loads(mcp_path.read_text())
    assert "atlassian" in config["mcpServers"]
    assert config["mcpServers"]["atlassian"]["url"] == "https://mcp.atlassian.com/mcp"


def test_deploy_creates_mcp_config_for_copilot(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    result = deploy(tmp_path, tool="copilot")
    assert result.exit_code == 0

    import json

    mcp_path = tmp_path / ".vscode" / "mcp.json"
    assert mcp_path.exists()
    config = json.loads(mcp_path.read_text())
    assert "atlassian" in config["servers"]
    assert config["servers"]["atlassian"]["url"] == "https://mcp.atlassian.com/mcp"


def test_deploy_creates_mcp_config_for_cursor(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    result = deploy(tmp_path, tool="cursor")
    assert result.exit_code == 0

    import json

    mcp_path = tmp_path / ".cursor" / "mcp.json"
    assert mcp_path.exists()
    config = json.loads(mcp_path.read_text())
    assert "atlassian" in config["mcpServers"]
    assert config["mcpServers"]["atlassian"]["url"] == "https://mcp.atlassian.com/mcp"


def test_deploy_skips_mcp_when_no_provider_configured(tmp_path: Path):
    """PM-tool agnosticism: without an `[issue-tracker]` provider, deploy must
    not push the Atlassian MCP into the project."""
    result = deploy(tmp_path)
    assert result.exit_code == 0

    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    # settings.json may exist for the telemetry Stop hook, but no MCP server
    # entry may be created without an explicit provider.
    if settings_path.exists():
        config = json.loads(settings_path.read_text())
        assert "atlassian" not in config.get("mcpServers", {})
    assert "skipped" in result.output
    assert "issue-tracker" in result.output


def test_deploy_skips_mcp_for_non_jira_provider(tmp_path: Path):
    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = "github"\n')

    result = deploy(tmp_path)
    assert result.exit_code == 0

    import json

    settings_path = tmp_path / ".claude" / "settings.json"
    if settings_path.exists():
        config = json.loads(settings_path.read_text())
        assert "atlassian" not in config.get("mcpServers", {})
    assert "github" in result.output


def test_deploy_creates_mcp_config_for_kiro(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    result = deploy(tmp_path, tool="kiro")
    assert result.exit_code == 0

    import json

    mcp_path = tmp_path / ".kiro" / "settings" / "mcp.json"
    assert mcp_path.exists()
    config = json.loads(mcp_path.read_text())
    assert "atlassian" in config["mcpServers"]


def test_codex_mcp_merge_preserves_existing_configuration(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text('model = "gpt-5.6"\n\n[agents]\nenabled = true\n')

    result = deploy(tmp_path, agents="story-refiner", tool="codex")

    assert result.exit_code == 0, result.output
    config = config_path.read_text()
    assert 'model = "gpt-5.6"' in config
    assert "[agents]" in config
    assert "[mcp_servers.atlassian]" in config
    assert f'url = "{ATLASSIAN_MCP_URL}"' in config


def test_codex_mcp_inline_table_entry_is_reported_not_corrupted(tmp_path: Path):
    """An atlassian entry in inline-table form must not be double-declared.

    The upsert only rewrites the `[mcp_servers.atlassian]` header form;
    appending that header when the entry exists in another TOML shape would
    declare the table twice and destroy a previously valid config.
    """
    _configure_jira_provider(tmp_path)
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    original = '[mcp_servers]\natlassian = { url = "https://old.example" }\n'
    config_path.write_text(original)

    result = deploy(tmp_path, agents="story-refiner", tool="codex")

    assert result.exit_code == 1
    assert "unsupported TOML shape" in result.output
    assert config_path.read_text() == original


def test_codex_mcp_preserves_malformed_config(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    config_path.write_text('model = "unterminated\n')

    result = deploy(tmp_path, agents="story-refiner", tool="codex")

    assert result.exit_code == 1
    assert "malformed TOML" in result.output
    assert config_path.read_text() == 'model = "unterminated\n'
    assert list(config_path.parent.glob("config.toml.broken-*"))


def test_codex_mcp_preserves_non_utf8_config(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    config_path = tmp_path / ".codex" / "config.toml"
    config_path.parent.mkdir()
    original = b"\xff\xfe"
    config_path.write_bytes(original)

    result = deploy(tmp_path, agents="story-refiner", tool="codex")

    assert result.exit_code == 1
    assert "notvalidUTF-8" in "".join(result.output.split())
    assert "Traceback" not in result.output
    assert config_path.read_bytes() == original
    broken_copies = list(config_path.parent.glob("config.toml.broken-*"))
    assert len(broken_copies) == 1
    assert broken_copies[0].read_bytes() == original


def test_deploy_mcp_preserves_existing_servers(tmp_path: Path):
    import json

    _configure_jira_provider(tmp_path)
    mcp_path = tmp_path / ".vscode" / "mcp.json"
    mcp_path.parent.mkdir(parents=True)
    mcp_path.write_text(json.dumps({"servers": {"custom": {"url": "http://example.com"}}}))

    result = deploy(tmp_path, tool="copilot")
    assert result.exit_code == 0

    config = json.loads(mcp_path.read_text())
    assert "custom" in config["servers"]
    assert "atlassian" in config["servers"]


def test_deploy_mcp_reports_already_configured(tmp_path: Path):
    _configure_jira_provider(tmp_path)
    deploy(tmp_path)
    result = deploy(tmp_path)
    assert result.exit_code == 0
    assert "already configured" in result.output


def test_deploy_no_mcp_skips_mcp_config(tmp_path: Path):
    import json

    result = deploy(tmp_path, mcp=False)
    assert result.exit_code == 0
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    assert "mcpServers" not in settings
    assert "hooks" in settings


def test_deploy_rewrites_kb_paths_in_story_refiner(tmp_path: Path):
    result = deploy(tmp_path, agents="story-refiner", tool="copilot")
    assert result.exit_code == 0

    deployed = (tmp_path / ".github" / "agents" / "story-refiner.agent.md").read_text()
    assert ".github/templates/story-template.md" in deployed
    assert ".github/templates/research-template.md" in deployed
    assert ".github/skills/story-writing/SKILL.md" in deployed
    assert ".github/knowledge-base/domain-language.md" in deployed
    assert ".github/knowledge-base/philosophy.md" in deployed


def test_deploy_rewrites_kb_paths_in_diff_reviewer(tmp_path: Path):
    result = deploy(tmp_path, agents="diff-reviewer")
    assert result.exit_code == 0

    deployed = (tmp_path / ".claude" / "agents" / "diff-reviewer.agent.md").read_text()
    assert ".claude/knowledge-base/security.md" in deployed
    assert ".claude/knowledge-base/observability.md" in deployed


def test_deploy_no_rules_skips_rules_file(tmp_path: Path):
    result = deploy(tmp_path, agents="story-refiner", rules=False)
    assert result.exit_code == 0
    assert not (tmp_path / "CLAUDE.md").exists()


def test_deploy_overwrites_modified_rules_silently(tmp_path: Path):
    deploy(tmp_path, agents="story-refiner")
    (tmp_path / "CLAUDE.md").write_text("# customised by team")

    result = deploy(tmp_path, agents="story-refiner")

    assert result.exit_code == 0
    assert (tmp_path / "CLAUDE.md").read_text() != "# customised by team"


def test_deploy_no_warning_when_rules_file_unchanged(tmp_path: Path):
    deploy(tmp_path, agents="story-refiner")
    result = deploy(tmp_path, agents="story-refiner")

    assert result.exit_code == 0
    assert "Warning" not in result.output


@pytest.mark.parametrize(
    "tool,agents_subdir,agent_suffix,kb_prefix,skills_prefix,templates_prefix",
    TOOL_MATRIX,
)
@pytest.mark.parametrize("agent_name", ALL_AGENTS)
def test_every_agent_deploys_to_every_tool(
    tmp_path: Path,
    tool: Tool,
    agents_subdir: str,
    agent_suffix: str,
    kb_prefix: str,
    skills_prefix: str,
    templates_prefix: str,
    agent_name: str,
):
    result = deploy(tmp_path, agents=agent_name, tool=tool.value)
    assert result.exit_code == 0, f"Deploy failed:\n{result.output}"

    deployed = tmp_path / agents_subdir / f"{agent_name}{agent_suffix}"
    assert deployed.exists(), f"{agent_name}{agent_suffix} not found at {deployed}"

    content = deployed.read_text()

    if agent_name in AGENTS_WITH_KB_REFS:
        assert kb_prefix in content
        assert re.search(r"(?<!/)knowledge-base/", content) is None

    if agent_name in AGENTS_WITH_SKILLS_REFS:
        assert skills_prefix in content
        assert re.search(r"(?<!/)skills/", content) is None

    if agent_name in AGENTS_WITH_TEMPLATE_REFS:
        assert templates_prefix in content
        assert re.search(r"(?<!/)templates/", content) is None


@pytest.mark.parametrize(
    "tool,rules_path",
    [
        (Tool.copilot, ".github/copilot-instructions.md"),
        (Tool.cursor, ".cursor/rules/ai-playbook.mdc"),
        (Tool.kiro, ".kiro/steering/rules.md"),
    ],
)
def test_deployed_content_cites_tool_rules_file_not_claude_md(
    tmp_path: Path, tool: Tool, rules_path: str
):
    """Non-Claude deploys must rewrite `CLAUDE.md` references to the target's
    rules file: a non-Claude adopter has no CLAUDE.md, so an unrewritten
    citation points at a file that does not exist in their tree."""
    result = deploy(tmp_path, tool=tool.value)
    assert result.exit_code == 0, result.output

    base = tmp_path / rules_path.split("/")[0]
    deployed_samples = [
        tmp_path / rules_path,
        base / "agents" / "diff-reviewer.agent.md",
        base / "knowledge-base" / "CHEATSHEET.md",
        base / "skills" / "git" / "SKILL.md",
    ]
    for deployed in deployed_samples:
        content = deployed.read_text()
        assert "CLAUDE.md" not in content, f"unrewritten CLAUDE.md reference in {deployed}"
        assert rules_path in content, f"no rules-file citation found in {deployed}"


@pytest.mark.parametrize(
    "tool,rules_path,command_path",
    [
        ("copilot", ".github/copilot-instructions.md", ".github/prompts/status.prompt.md"),
        ("cursor", ".cursor/rules/ai-playbook.mdc", ".cursor/commands/status.md"),
    ],
)
def test_deployed_command_cites_tool_rules_file(
    tmp_path: Path, tool: str, rules_path: str, command_path: str
):
    """Command shims go through their own transform: rules-file references
    must be rewritten there too."""
    result = deploy(tmp_path, tool=tool)
    assert result.exit_code == 0, result.output

    status_command = (tmp_path / command_path).read_text()
    assert "CLAUDE.md" not in status_command
    assert rules_path in status_command


def test_deployed_claude_content_keeps_claude_md_references(tmp_path: Path):
    """Claude is the identity target: its rules file IS CLAUDE.md."""
    result = deploy(tmp_path, agents="diff-reviewer")
    assert result.exit_code == 0, result.output

    content = (tmp_path / ".claude" / "agents" / "diff-reviewer.agent.md").read_text()
    assert "CLAUDE.md" in content


# ---------------------------------------------------------------------------
# Language filter
# ---------------------------------------------------------------------------


def test_deploy_language_python_skips_typescript(tmp_path: Path):
    result = deploy(tmp_path, language="python")
    assert result.exit_code == 0

    kb_dir = tmp_path / ".claude" / "knowledge-base" / "languages"
    assert (kb_dir / "python.md").exists()
    assert (kb_dir / "testing-python.md").exists()
    assert not (kb_dir / "typescript.md").exists()
    assert not (kb_dir / "testing-typescript.md").exists()
    assert "language: python" in (tmp_path / ".playbook-version").read_text()


def test_deploy_language_typescript_requires_team_language_file(tmp_path: Path):
    result = deploy(tmp_path, language="typescript")
    assert result.exit_code == 1
    assert "Unknown language" in result.output
    assert "python" in result.output
    assert not (tmp_path / ".claude").exists()


def test_deploy_language_unknown_exits_with_error(tmp_path: Path):
    result = deploy(tmp_path, language="rust")
    assert result.exit_code == 1
    assert "Unknown language" in result.output
    assert not (tmp_path / ".claude").exists()


# ---------------------------------------------------------------------------
# Template KB files (lazy deploy)
# ---------------------------------------------------------------------------


def test_deploy_default_deploys_all_kb_files(tmp_path: Path):
    """Deploy copies every non-language KB file: no skip-logic for 'template' files."""
    result = deploy(tmp_path)
    assert result.exit_code == 0

    kb_dir = tmp_path / ".claude" / "knowledge-base"
    assert (kb_dir / "testing.md").exists()
    assert (kb_dir / "testing-techniques.md").exists()
    assert (kb_dir / "security.md").exists()
    assert (kb_dir / "INDEX.md").exists()
    assert (kb_dir / "domain-language.md").exists()
    assert not (kb_dir / "limitations.md").exists()


def test_deploy_includes_singleton_templates(tmp_path: Path):
    """`templates/` ships singleton scaffolds and project registry starters."""
    result = deploy(tmp_path)
    assert result.exit_code == 0

    templates_dir = tmp_path / ".claude" / "templates"
    assert (templates_dir / "domain-language-template.md").exists()
    assert (templates_dir / "quality-gates-template.md").exists()
    assert (templates_dir / "limitations-template.md").exists()
    assert (templates_dir / "adr-template.md").exists()


# ---------------------------------------------------------------------------
# Edge cases: missing source dirs
# ---------------------------------------------------------------------------


def test_deploy_no_agents_found_exits_with_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy exits with error when no agents found in source root."""
    empty_source = tmp_path / "empty_source"
    empty_source.mkdir()
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: empty_source)

    result = deploy(tmp_path / "target")

    assert result.exit_code == 1
    assert "No agents found" in result.output


def test_deploy_source_without_rules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy when source has no CLAUDE.md: rules step is skipped."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    result = deploy(target)

    assert result.exit_code == 0
    assert not (target / "CLAUDE.md").exists()


def test_deploy_source_without_kb(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy when source has no knowledge-base dir."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    (fake_source / "CLAUDE.md").write_text("rules")
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    result = deploy(target)

    assert result.exit_code == 0
    assert not (target / ".claude" / "knowledge-base").exists()


def test_deploy_source_without_skills(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy when source has no skills dir."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    (fake_source / "CLAUDE.md").write_text("rules")
    kb = fake_source / "knowledge-base"
    kb.mkdir()
    (kb / "testing.md").write_text("testing")
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    result = deploy(target)

    assert result.exit_code == 0
    assert not (target / ".claude" / "skills").exists()


def test_deploy_prune_removes_orphaned_agent_file(tmp_path: Path):
    """`--prune --yes` removes deployed files with no corresponding source file."""
    deploy(tmp_path, mcp=False)
    orphan = tmp_path / ".claude" / "agents" / "retired-agent.agent.md"
    orphan.write_text("# left over from a previous version")
    assert orphan.exists()

    result = deploy(tmp_path, mcp=False, prune=True, yes=True)
    assert result.exit_code == 0
    assert "pruned" in result.output
    assert not orphan.exists()


def test_deploy_prune_preserves_disabled_files(tmp_path: Path):
    """`--prune` must not remove `*.disabled` files (user-managed state)."""
    deploy(tmp_path, mcp=False)
    disabled = tmp_path / ".claude" / "agents" / "xp-pair-programmer.agent.md.disabled"
    disabled.write_text("# user-disabled, should be preserved")

    result = deploy(tmp_path, mcp=False, prune=True, yes=True)
    assert result.exit_code == 0
    assert disabled.exists()


def test_deploy_prune_dry_run_does_not_delete(tmp_path: Path):
    """`--prune --dry-run` reports what would be pruned but deletes nothing."""
    deploy(tmp_path, mcp=False)
    orphan = tmp_path / ".claude" / "knowledge-base" / "retired-topic.md"
    orphan.write_text("# stale")
    assert orphan.exists()

    result = deploy(tmp_path, mcp=False, prune=True, dry_run=True)
    assert result.exit_code == 0
    assert "would prune" in result.output
    assert orphan.exists()


def test_deploy_without_prune_leaves_orphans(tmp_path: Path):
    """Default deploy (no `--prune`) does not remove orphaned files."""
    deploy(tmp_path, mcp=False)
    orphan = tmp_path / ".claude" / "agents" / "retired-agent.agent.md"
    orphan.write_text("# left over")

    result = deploy(tmp_path, mcp=False)
    assert result.exit_code == 0
    assert orphan.exists(), "Without --prune, orphaned files should be preserved"


def test_deploy_source_without_templates(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Deploy when source has no templates dir."""
    fake_source = tmp_path / "fake_source"
    agents_dir = fake_source / "agents"
    agents_dir.mkdir(parents=True)
    for name in ALL_AGENTS:
        (agents_dir / f"{name}.agent.md").write_text(f"# {name}")
    (fake_source / "CLAUDE.md").write_text("rules")
    kb = fake_source / "knowledge-base"
    kb.mkdir()
    (kb / "testing.md").write_text("testing")
    (fake_source / "skills").mkdir()
    monkeypatch.setattr("deploy_ai_playbook.cli.get_source_root", lambda: fake_source)

    target = tmp_path / "target"
    result = deploy(target)

    assert result.exit_code == 0
    assert not (target / ".claude" / "templates").exists()


# ---------------------------------------------------------------------------
# Harness deployment
# ---------------------------------------------------------------------------


def test_deploy_copies_harness_files(tmp_path: Path):
    """Deploy copies the complete starter harness on first deploy."""
    result = deploy(tmp_path, mcp=False)
    assert result.exit_code == 0
    assert (tmp_path / "Makefile").exists()
    assert (tmp_path / ".pre-commit-config.yaml").exists()
    assert (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    assert (tmp_path / ".github" / "workflows" / "security.yml").exists()
    # Backs security.yml's claim that Dependabot bumps its pinned SHAs weekly.
    assert (tmp_path / ".github" / "dependabot.yml").exists()
    assert (tmp_path / "harness" / "check-teachback.sh").exists()
    assert (tmp_path / "harness" / "telemetry.sh").exists()
    assert (tmp_path / "harness" / "settings.example.json").exists()
    assert "Harness" in result.output
    assert "copied" in result.output


def test_deploy_configures_claude_telemetry_stop_hook_by_default(tmp_path: Path):
    """Deploy wires the Claude Stop hook when the starter harness is installed."""
    import json

    result = deploy(tmp_path, mcp=False)

    assert result.exit_code == 0
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text())
    stop_hooks = settings["hooks"]["Stop"]
    assert any(
        hook.get("command") == "${CLAUDE_PROJECT_DIR}/harness/telemetry.sh"
        for entry in stop_hooks
        for hook in entry.get("hooks", [])
    )
    assert "telemetry Stop hook" in result.output


def test_deploy_configures_codex_telemetry_session_end_hook_by_default(tmp_path: Path):
    """Codex deploy wires a trusted-on-review SessionEnd hook."""
    import json

    result = deploy(tmp_path, tool="codex", mcp=False)

    assert result.exit_code == 0, result.output
    hooks = json.loads((tmp_path / ".codex" / "hooks.json").read_text())
    commands = [
        hook.get("command")
        for entry in hooks["hooks"]["SessionEnd"]
        for hook in entry.get("hooks", [])
    ]
    assert any("harness/telemetry.sh" in command for command in commands)
    assert "telemetry SessionEnd hook" in result.output
    assert "review and trust" in result.output


def test_deploy_harness_skips_existing_files(tmp_path: Path):
    """Deploy does not overwrite harness files that already exist."""
    (tmp_path / "Makefile").write_text("# custom project make targets")
    (tmp_path / ".pre-commit-config.yaml").write_text("# custom project hooks")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text("# custom CI")

    result = deploy(tmp_path, mcp=False)
    assert result.exit_code == 0
    assert "exists, kept" in result.output
    assert "--harness-force" in result.output
    assert (tmp_path / "Makefile").read_text() == "# custom project make targets"
    assert (tmp_path / ".pre-commit-config.yaml").read_text() == "# custom project hooks"
    assert (tmp_path / ".github" / "workflows" / "ci.yml").read_text() == "# custom CI"


def test_deploy_harness_force_overwrites_existing_files(tmp_path: Path):
    """`--harness-force` overwrites adopter edits: opt-in only."""
    (tmp_path / "Makefile").write_text("# old custom Makefile")

    result = deploy(tmp_path, mcp=False, harness_force=True)
    assert result.exit_code == 0
    assert "overwrote" in result.output
    assert (tmp_path / "Makefile").read_text() != "# old custom Makefile"


def test_deploy_harness_force_dry_run_announces_overwrite(tmp_path: Path):
    (tmp_path / "Makefile").write_text("# existing")
    result = deploy(tmp_path, mcp=False, harness_force=True, dry_run=True)
    assert result.exit_code == 0
    assert "would overwrite" in result.output
    assert (tmp_path / "Makefile").read_text() == "# existing"


def test_deploy_no_harness_flag_skips_harness(tmp_path: Path):
    """--no-harness suppresses harness file deployment entirely."""
    result = deploy(tmp_path, mcp=False, harness=False)
    assert result.exit_code == 0
    assert not (tmp_path / "Makefile").exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()
    assert not (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    assert not (tmp_path / "harness" / "telemetry.sh").exists()
    assert not (tmp_path / "harness" / "settings.example.json").exists()
    assert not (tmp_path / ".claude" / "settings.json").exists()
    assert "Harness" not in result.output


def test_deploy_harness_dry_run(tmp_path: Path):
    """--dry-run previews harness deployment without writing files."""
    result = deploy(tmp_path, mcp=False, dry_run=True)
    assert result.exit_code == 0
    assert "would copy" in result.output
    assert not (tmp_path / "Makefile").exists()
    assert not (tmp_path / ".pre-commit-config.yaml").exists()
    assert not (tmp_path / ".github" / "workflows" / "ci.yml").exists()
    assert not (tmp_path / "harness" / "telemetry.sh").exists()
    assert not (tmp_path / "harness" / "settings.example.json").exists()


def test_deploy_harness_shell_hook_is_executable(tmp_path: Path):
    """Shell hooks (e.g. check-teachback.sh) deploy with the +x bit set.

    write_text drops the executable bit; cli._deploy_harness restores it for
    `.sh` files. Without this, adopters silently get a non-executable hook
    that pre-commit wires up and then fails to run: bypassing the
    teach-back gate without warning.
    """
    import os
    import stat

    result = deploy(tmp_path, mcp=False)
    assert result.exit_code == 0
    for hook_name in ("check-teachback.sh", "telemetry.sh"):
        hook = tmp_path / "harness" / hook_name
        assert hook.exists(), f"{hook_name} must be deployed"
        mode = hook.stat().st_mode
        assert mode & stat.S_IXUSR, (
            f"{hook_name} must be executable for the user (mode {oct(mode)})"
        )
        assert os.access(hook, os.X_OK), f"{hook_name} must pass os.access X_OK"


def test_redeploy_repairs_harness_executable_bit_without_overwriting(tmp_path: Path):
    """Normal redeploy repairs hook permissions while preserving adopter edits."""
    import stat

    hook = tmp_path / "harness" / "telemetry.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\n# adopter customization\n", encoding="utf-8")
    hook.chmod(0o640)

    result = deploy(tmp_path, mcp=False)

    assert result.exit_code == 0, result.output
    assert "repaired executable bit" in result.output
    assert hook.read_text(encoding="utf-8") == "#!/bin/sh\n# adopter customization\n"
    assert stat.S_IMODE(hook.stat().st_mode) == 0o740


def test_redeploy_dry_run_previews_executable_repair_without_changing_mode(
    tmp_path: Path,
) -> None:
    import stat

    hook = tmp_path / "harness" / "telemetry.sh"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\n# adopter customization\n", encoding="utf-8")
    hook.chmod(0o640)

    result = deploy(tmp_path, mcp=False, dry_run=True)

    assert result.exit_code == 0, result.output
    assert "would repair executable bit" in result.output
    assert stat.S_IMODE(hook.stat().st_mode) == 0o640


def test_deploy_is_idempotent(tmp_path: Path):
    """Two consecutive deploys produce byte-identical state and a clean diff.

    Idempotency is one of the README's headline guarantees: running deploy a
    second time on an unchanged playbook must be a no-op for every file
    (status `unchanged`) and `ai-playbook diff` must report nothing changed.
    Catches regressions where a newly-added subsystem writes nondeterministic
    content (timestamps in copied files, sorted-set iteration ordering, etc.).
    """
    import hashlib

    def _snapshot(root: Path) -> dict[str, str]:
        # `.playbook-version` and `.playbook-backup/` are timestamped by design;
        # exclude both from the byte-identity check (their content drift is
        # tested separately in test_doctor / test_backup).
        snapshot: dict[str, str] = {}
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            top = rel.parts[0]
            if top in {".playbook-version", ".playbook-backup"}:
                continue
            snapshot[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return snapshot

    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0, first.output
    snapshot_after_first = _snapshot(tmp_path)

    second = deploy(tmp_path, mcp=False)
    assert second.exit_code == 0, second.output
    snapshot_after_second = _snapshot(tmp_path)

    assert snapshot_after_first == snapshot_after_second, (
        "Second deploy mutated content — deploy must be idempotent on unchanged source"
    )
    # Second-deploy reporting: every file in the layered tree must be `unchanged`.
    assert "copied" not in second.output, (
        "Second deploy reported newly-copied files — should be all `unchanged`"
    )

    # Diff command must agree there is nothing to redeploy.
    diff_result = runner.invoke(app, ["diff", "--tool", "claude", "-t", str(tmp_path)])
    assert diff_result.exit_code == 0
    assert "Everything up to date." in diff_result.output, (
        f"diff reported drift after a clean second deploy:\n{diff_result.output}"
    )


# ---------------------------------------------------------------------------
# Prune confirmation gate: keeps `--prune` from silently deleting files.
# ---------------------------------------------------------------------------


def test_deploy_prune_aborts_when_user_declines(tmp_path: Path):
    """Without --yes, prune must prompt and abort cleanly when the user says no."""
    deploy(tmp_path, mcp=False)
    orphan = tmp_path / ".claude" / "agents" / "retired-agent.agent.md"
    orphan.write_text("# left over")

    # CliRunner with input="n\n" simulates a user declining the prompt.
    result = deploy(tmp_path, mcp=False, prune=True, input="n\n")
    assert result.exit_code == 0
    assert "will prune" in result.output
    assert "Prune aborted" in result.output
    assert orphan.exists(), "Orphan must survive an aborted prune"


def test_deploy_prune_warns_about_files_from_removed_pack(tmp_path: Path):
    """Removing a pack from .ai-playbook.toml then pruning must warn the user.

    The version file remembers the previously-deployed pack names. When the
    current `.ai-playbook.toml` no longer lists one, prune surfaces the name
    so adopters can recognise an unintentional pack removal before deleting.
    """
    # First deploy with a pack present.
    pack_root = tmp_path / "company-pack"
    pack_root.mkdir()
    (pack_root / "pack.toml").write_text('name = "company-pack"\nversion = "1.0.0"\n')
    (pack_root / "agents").mkdir()
    pack_agent = pack_root / "agents" / "company-reviewer.agent.md"
    pack_agent.write_text("# pack-only agent\n")
    (tmp_path / ".ai-playbook.toml").write_text('packs = ["./company-pack"]\n')

    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0, first.output
    deployed_pack_agent = tmp_path / ".claude" / "agents" / "company-reviewer.agent.md"
    assert deployed_pack_agent.exists()

    # Remove the pack from config and re-deploy with --prune.
    (tmp_path / ".ai-playbook.toml").write_text("packs = []\n")
    second = deploy(tmp_path, mcp=False, prune=True, yes=True)
    assert second.exit_code == 0, second.output
    assert "company-pack" in second.output, (
        "Prune must surface the name of removed packs whose files are about to be deleted"
    )
    assert not deployed_pack_agent.exists(), "Orphaned pack file should be pruned after --yes"


def test_deploy_prune_dry_run_skips_confirmation(tmp_path: Path):
    """`--prune --dry-run` must NOT prompt: preview is non-destructive."""
    deploy(tmp_path, mcp=False)
    (tmp_path / ".claude" / "agents" / "retired.agent.md").write_text("# stale")

    # No input provided: prompt would hang if it fired.
    result = deploy(tmp_path, mcp=False, prune=True, dry_run=True, input="")
    assert result.exit_code == 0
    assert "would prune" in result.output
    assert "Prune aborted" not in result.output


# ---------------------------------------------------------------------------
# Backup failure recovery
# ---------------------------------------------------------------------------


def test_deploy_aborts_cleanly_when_backup_creation_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """If backup creation raises, deploy must surface the error and not leave half-written state.

    This guards the riskiest path: a redeploy where backup fails partway. The
    pre-existing deployed files must remain readable (so the adopter can rerun)
    and the version file must not regress to a state that misrepresents the
    deployment fingerprint.
    """
    # Initial clean deploy.
    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0

    deployed_agent = tmp_path / ".claude" / "agents" / "xp-pair-programmer.agent.md"
    pre_failure_content = deployed_agent.read_text()
    pre_failure_version = (tmp_path / VERSION_FILE).read_text()

    # Patch where the call site resolves it: backup_existing_deployment lives
    # in deploy_render, so cli's re-export is not the seam.
    def boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated disk full during backup")

    monkeypatch.setattr("deploy_ai_playbook.deploy_render.backup_deployed_files", boom)

    second = deploy(tmp_path, mcp=False)
    # Deploy must fail. Either via typer.Exit or by re-raising: but it must NOT
    # silently succeed and overwrite the deployment.
    assert second.exit_code != 0, f"Deploy must abort when backup fails. Output:\n{second.output}"
    # Pre-existing deployment must be intact for the adopter to retry.
    assert deployed_agent.exists()
    assert deployed_agent.read_text() == pre_failure_content, (
        "Backup-failed deploy must not have touched the previous deployment"
    )
    assert (tmp_path / VERSION_FILE).read_text() == pre_failure_version, (
        "Backup-failed deploy must not have rewritten the version fingerprint"
    )
    assert "Traceback" not in second.output


def test_deploy_failure_after_backup_points_to_rollback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0

    def fail_after_backup(*_args: object, **_kwargs: object) -> None:
        raise WriteAccessError("Cannot write to simulated destination")

    monkeypatch.setattr("deploy_ai_playbook.cli._deploy_layered", fail_after_backup)

    second = deploy(tmp_path, mcp=False)

    assert second.exit_code == 1
    assert "Deploy failed after creating a backup" in second.output
    assert "ai-playbook rollback --tool claude" in second.output
    assert "Traceback" not in second.output


def test_deploy_surfaces_graceful_error_on_readonly_target(tmp_path: Path):
    """Section-5 fix: read-only target must produce a one-line `Error:` not a
    Python traceback.

    First-time users who deploy into a locked-down directory (or CI with
    restricted mounts) deserve a clean diagnostic, not a `pathlib.PermissionError`
    stack with internal frames. The CLI catches `OSError` at the safety layer
    and raises a typed `WriteAccessError` (a subclass of `AIPlaybookError`).
    """
    # Make the parent dir read-only; the deploy will try to mkdir under it.
    target = tmp_path / "ro"
    target.mkdir()
    target.chmod(0o555)
    try:
        result = deploy(target / "sub", mcp=False)
        assert result.exit_code == 1, "read-only target must exit 1"
        assert "Error:" in result.output, "must surface a graceful Error: line"
        # The traceback should NOT leak. Tracebacks contain `File "...py", line N, in`.
        assert "Traceback" not in result.output, (
            "read-only target must not surface a raw Python traceback"
        )
        assert "Cannot write to" in result.output, "error must name the destination path and reason"
    finally:
        target.chmod(0o755)


def test_rollback_accepts_yes_alias(tmp_path: Path):
    """Section-5 unification: rollback `--yes`/`-y` mirrors the deploy flag.

    `--force`/`-f` is kept as a backward-compatible alias; both spellings
    must skip the confirmation prompt without prompting.
    """
    # Set up two deploys so a backup exists.
    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0
    second = deploy(tmp_path, mcp=False)
    assert second.exit_code == 0

    # `--yes` (canonical) must skip the prompt and exit 0.
    yes_result = runner.invoke(app, ["rollback", "--tool", "claude", "-t", str(tmp_path), "--yes"])
    assert yes_result.exit_code == 0, yes_result.output

    # `--force` (alias) still works for adopters who picked up the prior name.
    third = deploy(tmp_path, mcp=False)
    assert third.exit_code == 0
    force_result = runner.invoke(
        app, ["rollback", "--tool", "claude", "-t", str(tmp_path), "--force"]
    )
    assert force_result.exit_code == 0, force_result.output


def test_deploy_unexpected_failure_still_prints_rollback_hint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An UNTYPED mid-deploy failure must still point at the backup.

    The typed-error path (WriteAccessError) is covered above; this pins the
    broadened handler: the hint prints, and the unexpected error stays loud
    (re-raised, not converted to a tidy exit code).
    """
    first = deploy(tmp_path, mcp=False)
    assert first.exit_code == 0

    def explode(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("simulated unexpected failure")

    monkeypatch.setattr("deploy_ai_playbook.cli._deploy_layered", explode)

    second = deploy(tmp_path, mcp=False)

    assert second.exit_code != 0
    assert "Deploy failed after creating a backup" in second.output
    assert "ai-playbook rollback --tool claude" in second.output
    assert isinstance(second.exception, RuntimeError), "unexpected errors must stay loud"
