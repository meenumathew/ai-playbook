"""Contract tests for public documentation drift."""

from __future__ import annotations

import re

from deploy_ai_playbook.cli import get_source_root

ENV_VAR_RE = re.compile(r"\b[A-Z][A-Z0-9]+(?:_[A-Z0-9]+)+\b")


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE)
    assert match, f"missing section: {heading}"
    next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(text)
    return text[match.end() : end]


def _env_vars(text: str) -> set[str]:
    return set(ENV_VAR_RE.findall(text))


def test_cli_reference_agents_table_matches_shipped_agents():
    """The public agent list must track the shipped agents directory."""
    source_root = get_source_root()
    shipped = {
        path.name.removesuffix(".agent.md") for path in (source_root / "agents").glob("*.agent.md")
    }
    cli_reference = (source_root / "docs" / "cli-reference.md").read_text(encoding="utf-8")
    agents_section = _section(cli_reference, "Agents")

    # STRUCTURE-MARKER: table rows, not wording, are the public contract.
    rows = re.findall(
        r"^\| `([^`]+)` \| `([^`]+\.agent\.md)` \|",
        agents_section,
        re.MULTILINE,
    )
    documented = {agent for agent, _path in rows}
    path_mismatches = [
        f"{agent} -> {path_name}" for agent, path_name in rows if path_name != f"{agent}.agent.md"
    ]

    assert not path_mismatches, "Agent table rows with mismatched names/paths: " + ", ".join(
        path_mismatches
    )
    assert documented == shipped, (
        "docs/cli-reference.md agent table drifted from agents/ tree:\n"
        f"  shipped but undocumented: {sorted(shipped - documented)}\n"
        f"  documented but not shipped: {sorted(documented - shipped)}"
    )


def test_cli_reference_skills_table_matches_shipped_skills():
    """The public skill list must track the shipped skills directory."""
    source_root = get_source_root()
    shipped = {
        path.name
        for path in (source_root / "skills").iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    }
    cli_reference = (source_root / "docs" / "cli-reference.md").read_text(encoding="utf-8")
    skills_section = _section(cli_reference, "Skills")

    # STRUCTURE-MARKER: table rows, not wording, are the public contract.
    rows = re.findall(
        r"^\| `([^`]+)` \| `skills/([^`]+)/SKILL\.md` \|",
        skills_section,
        re.MULTILINE,
    )
    documented = {skill for skill, _path_skill in rows}
    path_mismatches = [
        f"{skill} -> skills/{path_skill}/SKILL.md"
        for skill, path_skill in rows
        if skill != path_skill
    ]

    assert not path_mismatches, "Skill table rows with mismatched names/paths: " + ", ".join(
        path_mismatches
    )
    assert documented == shipped, (
        "docs/cli-reference.md skill table drifted from skills/ tree:\n"
        f"  shipped but undocumented: {sorted(shipped - documented)}\n"
        f"  documented but not shipped: {sorted(documented - shipped)}"
    )


def test_project_management_tool_docs_only_name_skill_declared_env_vars():
    """Project-management tool docs must not invent credential environment variables."""
    source_root = get_source_root()
    skill_text = (source_root / "skills" / "issue-fetch" / "SKILL.md").read_text(encoding="utf-8")
    declared = _env_vars(skill_text)

    docs_to_check = (
        source_root / "docs" / "how-to" / "setup-issue-tracker.md",
        source_root / "docs" / "user-guide.md",
    )
    undocumented: list[str] = []
    for path in docs_to_check:
        doc_vars = _env_vars(path.read_text(encoding="utf-8"))
        # STRUCTURE-MARKER: credential variable names must come from the skill contract.
        for var in sorted(doc_vars - declared):
            rel = path.relative_to(source_root)
            undocumented.append(f"{rel}: `{var}` is not declared in skills/issue-fetch/SKILL.md")

    assert not undocumented, "Work item docs drifted from issue-fetch env vars:\n" + "\n".join(
        undocumented
    )


def test_project_management_tool_agnostic_work_item_language_is_documented():
    """Public docs must explain tracker work items separately from story artifacts."""
    source_root = get_source_root()
    docs = {
        "README.md": (source_root / "README.md").read_text(encoding="utf-8"),
        "docs/user-guide.md": (source_root / "docs" / "user-guide.md").read_text(encoding="utf-8"),
        "docs/how-to/invoke-agents.md": (
            source_root / "docs" / "how-to" / "invoke-agents.md"
        ).read_text(encoding="utf-8"),
        "skills/issue-fetch/SKILL.md": (
            source_root / "skills" / "issue-fetch" / "SKILL.md"
        ).read_text(encoding="utf-8"),
        "skills/story-writing/SKILL.md": (
            source_root / "skills" / "story-writing" / "SKILL.md"
        ).read_text(encoding="utf-8"),
    }

    for path, text in docs.items():
        lower_text = text.lower()
        assert "work item" in lower_text, (
            f"{path} must use project-management-tool agnostic work item language"
        )

    assert "project-management-tool agnostic" in docs["README.md"].lower()

    issue_fetch = docs["skills/issue-fetch/SKILL.md"].lower()
    for concept in ("external", "tracker", "work item", "story artifact", "issue-ref"):
        assert concept in issue_fetch, f"issue-fetch must document the {concept!r} boundary"

    story_writing = docs["skills/story-writing/SKILL.md"].lower()
    for concept in ("project-management", "work", "internal artifact", "stories/"):
        assert concept in story_writing, f"story-writing must document {concept!r}"


DEFAULT_CHAIN_AGENTS = (
    "story-refiner",
    "slice-planner",
    "xp-pair-programmer",
    "diff-reviewer",
    "release-captain",
)


def test_user_guide_default_loop_matches_claude_md_workflow_chain():
    """The user-guide's default invocation sequence must track CLAUDE.md § Workflow.

    Caught drifting in an audit: docs taught a 4-agent chain after CLAUDE.md
    grew the release-captain ship step.
    """
    source_root = get_source_root()
    claude_md = (source_root / "CLAUDE.md").read_text(encoding="utf-8")
    user_guide = (source_root / "docs" / "user-guide.md").read_text(encoding="utf-8")

    default_line = next(
        (line for line in claude_md.splitlines() if line.startswith("**Default workflow path:**")),
        None,
    )
    assert default_line, "CLAUDE.md lost its '**Default workflow path:**' line"

    # STRUCTURE-MARKER: the agent ordering is the contract, not the prose
    # around it (CLAUDE.md decorates the chain with bold and parentheticals).
    positions = [default_line.find(agent) for agent in DEFAULT_CHAIN_AGENTS]
    assert -1 not in positions and positions == sorted(positions), (
        "CLAUDE.md default workflow path no longer lists the agents this test "
        f"pins, in order: {DEFAULT_CHAIN_AGENTS}. Update DEFAULT_CHAIN_AGENTS "
        "here and docs/user-guide.md § The Loop together."
    )

    loop_section = _section(user_guide, "3. The Loop")
    literal_chain = " → ".join(DEFAULT_CHAIN_AGENTS)
    assert literal_chain in loop_section, (
        "docs/user-guide.md § 3. The Loop drifted from the CLAUDE.md § Workflow "
        f"default chain — expected the literal sequence: {literal_chain}"
    )


def test_which_path_decision_tree_is_identical_in_readme_and_how_to():
    """The Which-Path decision tree exists in two display surfaces — README
    (front door) and docs/how-to/choose-workflow-path.md (canonical detail).

    Hand-drawn duplicates drift (a whitespace delta had already
    crept in). Both copies stay because both surfaces need the tree; this pin
    keeps them byte-identical — edit the how-to first, then copy to README.
    """
    source_root = get_source_root()

    def tree(path):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"```text\n(Is the change trivial\?.*?)```", text, re.DOTALL)
        assert match, f"{path.name}: Which-Path tree fenced block not found"
        return match.group(1)

    readme_tree = tree(source_root / "README.md")
    howto_tree = tree(source_root / "docs" / "how-to" / "choose-workflow-path.md")
    # STRUCTURE-MARKER: byte-equality of the two copies is the contract, not
    # the tree's content — the tree itself is free to evolve in both at once.
    assert readme_tree == howto_tree, (
        "Which-Path decision tree drifted between README.md and "
        "docs/how-to/choose-workflow-path.md — sync them (how-to is canonical)"
    )
