"""Contract tests for knowledge base files, skills, and deployed path rewriting."""

import re

from typer.testing import CliRunner

from deploy_ai_playbook.cli import app, get_source_root
from tests.acceptance.contract_data import (
    KB_CONTRACTS,
    SKILL_CONTRACTS,
    TextContract,
    contract_failures,
    read_kb,
    read_skill,
)


def test_each_kb_file_contains_its_required_invariants():
    for filename, required_contracts in KB_CONTRACTS.items():
        content = read_kb(filename)
        failures = contract_failures(content, required_contracts)
        assert not failures, f"Contract failures in knowledge-base/{filename}: {failures}"


def test_root_kb_files_are_rule_first_with_agent_use_header():
    kb_dir = get_source_root() / "knowledge-base"
    for path in sorted(kb_dir.glob("*.md")):
        if path.name == "INDEX.md":
            continue
        content = path.read_text()
        frontmatter = _frontmatter(content)
        headings = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)

        assert re.search(r"^load_when:\s*", frontmatter, re.MULTILINE), (
            f"{path.name} must define load triggers in frontmatter"
        )
        assert headings and headings[0] == "Agent Use", (
            f"{path.name} must start body guidance with an Agent Use section"
        )
        agent_use = _section(content, "Agent Use")
        assert re.search(r"^- \*\*Read first:\*\*", agent_use, re.MULTILINE), (
            f"{path.name} must define first sections to read"
        )


def _frontmatter(content: str) -> str:
    assert content.startswith("---\n"), "expected YAML frontmatter"
    end = content.find("\n---", 4)
    assert end > 0, "expected closing YAML frontmatter marker"
    return content[4:end]


def _section(content: str, heading: str) -> str:
    match = re.search(rf"^##\s+{re.escape(heading)}\s*$", content, re.MULTILINE)
    assert match, f"missing section: {heading}"
    next_heading = re.search(r"^##\s+", content[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(content)
    return content[match.end() : end]


def test_each_skill_contains_its_required_invariants():
    for skill_name, required_contracts in SKILL_CONTRACTS.items():
        content = read_skill(skill_name)
        failures = contract_failures(content, required_contracts)
        assert not failures, f"Contract failures in skills/{skill_name}/SKILL.md: {failures}"


def test_quality_gates_are_filled_for_this_repo():
    content = read_kb("quality-gates.md")

    for placeholder in (
        "[format command]",
        "[lint command]",
        "[type-check command]",
        "[test command]",
        "[coverage command]",
        "[security command]",
        "[auth]",
        "[payments]",
    ):
        assert placeholder not in content
    assert "make format-check" in content
    assert "mutation-baseline.json" in content


def test_kb_and_skill_contracts_are_structured_not_raw_phrase_pins():
    all_contracts = [*KB_CONTRACTS.values(), *SKILL_CONTRACTS.values()]
    for required_contracts in all_contracts:
        assert required_contracts
        for text_contract in required_contracts:
            assert isinstance(text_contract, TextContract)
            assert text_contract.name
            assert text_contract.terms or text_contract.references or text_contract.headings


def test_deployed_kb_skills_templates_have_no_unresolved_root_paths(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["deploy", "--agent", "all", "--tool", "claude", "-t", str(tmp_path), "--no-mcp"],
    )
    assert result.exit_code == 0, result.output

    forbidden = (
        re.compile(r"(?<!\.claude/)\bknowledge-base/"),
        re.compile(r"(?<!\.claude/)(?<!\.kiro/)(?<!\.github/)\bskills/"),
        re.compile(r"(?<!\.claude/)(?<!\.kiro/)(?<!\.github/)\btemplates/"),
    )
    offenders: list[str] = []
    for deployed_dir in (
        tmp_path / ".claude" / "knowledge-base",
        tmp_path / ".claude" / "skills",
        tmp_path / ".claude" / "templates",
    ):
        for file_path in deployed_dir.rglob("*.md"):
            content = file_path.read_text()
            for pattern in forbidden:
                for match in pattern.finditer(content):
                    line_no = content[: match.start()].count("\n") + 1
                    offenders.append(
                        f"{file_path.relative_to(tmp_path)}:{line_no}: {match.group(0)!r}"
                    )

    assert not offenders, "Unresolved source-root path refs in deployed files:\n" + "\n".join(
        offenders
    )


def test_every_skill_is_cited_outside_the_index():
    """Every shipped skill is referenced by an agent, CLAUDE.md, or KB file.

    INDEX.md lists all skills by definition, so it doesn't count as a real
    citation. A skill that only appears in INDEX.md is a drift hazard — it
    will rot silently because no behaviour reaches for it. Wiring the skill
    into a concrete agent step keeps it load-bearing.
    """
    source_root = get_source_root()
    skills_dir = source_root / "skills"
    referrer_files: list[tuple[str, str]] = [("CLAUDE.md", (source_root / "CLAUDE.md").read_text())]
    referrer_files.extend(
        (f"agents/{path.name}", path.read_text())
        for path in sorted((source_root / "agents").glob("*.agent.md"))
    )
    referrer_files.extend(
        (f"skills/{path.parent.name}/SKILL.md", path.read_text())
        for path in sorted(skills_dir.glob("*/SKILL.md"))
    )
    referrer_files.extend(
        (f"knowledge-base/{path.relative_to(source_root / 'knowledge-base')}", path.read_text())
        for path in sorted((source_root / "knowledge-base").rglob("*.md"))
        if path.name != "INDEX.md"
    )

    orphans: list[str] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not (skill_dir / "SKILL.md").is_file():
            continue
        skill_ref = f"skills/{skill_dir.name}/"
        own_skill_path = f"skills/{skill_dir.name}/SKILL.md"
        cited = any(
            skill_ref in body for ref_path, body in referrer_files if ref_path != own_skill_path
        )
        if not cited:
            orphans.append(skill_dir.name)

    assert not orphans, (
        f"Skills cited only by INDEX.md (orphans): {orphans}.\n"
        f"Wire each into an agent step or CLAUDE.md so it stays load-bearing."
    )


def test_definition_of_done_templates_reference_canonical_source():
    source_root = get_source_root()

    def extract_dod_section(path: str) -> str:
        text = (source_root / path).read_text()
        heading = "## Definition of Done\n"
        assert heading in text, f"{path} has no '## Definition of Done' section"
        after_heading = text.split(heading, 1)[1]
        end_markers = [marker for marker in ("\n---", "\n## ") if marker in after_heading]
        end_index = min(
            (after_heading.index(marker) for marker in end_markers), default=len(after_heading)
        )
        return after_heading[:end_index]

    canonical = extract_dod_section("CLAUDE.md")
    canonical_bullets = set(re.findall(r"^- \[ \] (.+)$", canonical, re.MULTILINE))
    assert canonical_bullets
    for template in (
        "templates/story-template.md",
        "templates/story-bug-template.md",
        "templates/plan-template.md",
        "templates/review-template.md",
    ):
        section = extract_dod_section(template)
        # STRUCTURE-MARKER: template DoD sections must point at the canonical
        # home (any link format that names CLAUDE.md counts) instead of
        # restating its bullets.
        assert "CLAUDE.md" in section
        assert "Definition of Done" in section or "DoD" in section
        duplicated = canonical_bullets & set(re.findall(r"^- \[ \] (.+)$", section, re.MULTILINE))
        assert not duplicated, f"{template} duplicates canonical DoD bullets: {duplicated}"

    spike_section = extract_dod_section("templates/story-spike-template.md")
    # STRUCTURE-MARKER: the spike DoD must declare itself the reduced variant;
    # surrounding wording is free.
    assert "reduced" in spike_section.lower()
    assert re.findall(r"^- \[ \] ", spike_section, re.MULTILINE)
