"""Contract tests for agent files, commands, and global rules.

Three layers of contract pinning:

1. **Structural** — frontmatter is the machine-readable contract. We assert
   shape (required keys, valid model tier, command shim parity) so a
   regression breaks loudly without depending on prose wording.
2. **Behavioural (positive)** — `AGENT_CONTRACTS` in `contract_data.py`
   pins the *terms / references / headings* that must be present, not
   exact sentences. `contract_failures()` does case-insensitive matching
   so legitimate copy-edits don't fail tests.
3. **Anti-regression (negative)** — `AGENT_FORBIDDEN_PHRASES` records
   phrases we deliberately removed. Each row carries a `reason` so a
   future contributor can decide whether to revert or update the rule.

Citations between agent files and CLAUDE.md / KB / templates are validated
structurally by `test_pointer_contracts.py` (one canonical resolver), not
duplicated here as exact-substring assertions.
"""

from __future__ import annotations

import re

import yaml

from deploy_ai_playbook.cli import discover_agents, get_source_root
from tests import ALL_AGENTS
from tests.acceptance.contract_data import (
    AGENT_CONTRACTS,
    AGENT_FORBIDDEN_PHRASES,
    AGENTS_WITH_READ_BUDGET,
    REMOVED_AGENT_NAMES,
    UTILITY_COMMANDS,
    TextContract,
    contract_failures,
    read_agent,
)

# ---------------------------------------------------------------------------
# Structural frontmatter contract
# ---------------------------------------------------------------------------


_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_REQUIRED_FRONTMATTER_KEYS = (
    "id",
    "model",
    "load_when",
    "inputs",
    "outputs",
    "handoff",
    "escalation",
)
_VALID_MODEL_TIERS = frozenset({"advisor", "executor"})


def _parse_frontmatter(content: str) -> dict[str, object]:
    match = _FRONTMATTER_RE.search(content)
    assert match, "agent file must start with YAML frontmatter"
    return yaml.safe_load(match.group(1)) or {}


def test_every_agent_declares_required_frontmatter_keys():
    """Frontmatter is the machine-readable agent contract — pin its shape."""
    failures: list[str] = []
    for agent_name, agent_path in discover_agents(get_source_root()).items():
        content = agent_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(content)
        missing = [key for key in _REQUIRED_FRONTMATTER_KEYS if not fm.get(key)]
        if missing:
            failures.append(f"{agent_name}: missing/empty frontmatter keys {missing}")
        if fm.get("id") and fm["id"] != agent_name:
            failures.append(f"{agent_name}: frontmatter `id: {fm['id']}` does not match filename")
        if fm.get("model") and fm["model"] not in _VALID_MODEL_TIERS:
            failures.append(
                f"{agent_name}: `model: {fm['model']}` not in {sorted(_VALID_MODEL_TIERS)}"
            )
    assert not failures, "Frontmatter contract failures:\n  " + "\n  ".join(failures)


def test_every_agent_declares_machine_readable_read_budget():
    """`read-budget:` frontmatter feeds harness/read-budget.sh.

    Every agent declares either an integer cap or the literal `self-tracked`
    (xp-pair-programmer). The hook reads this key from the deployed agent
    file, so a missing or malformed value silently disables enforcement —
    hence the pin.
    """
    failures: list[str] = []
    for agent_name, agent_path in discover_agents(get_source_root()).items():
        fm = _parse_frontmatter(agent_path.read_text(encoding="utf-8"))
        value = fm.get("read-budget")
        if value is None:
            failures.append(f"{agent_name}: missing `read-budget:` frontmatter")
        elif str(value) != "self-tracked" and not str(value).isdigit():
            failures.append(f"{agent_name}: `read-budget: {value}` is neither int nor self-tracked")
    assert not failures, "read-budget contract failures:\n  " + "\n  ".join(failures)


def test_agents_with_read_budgets_state_a_per_session_cap():
    cap_pattern = re.compile(
        r"(?:read(?:s)?\s+(?:cap(?:ped)?|budget)\b[^\n]*?\b\d+\b[^\n]*?\bsession\b"
        r"|\bMax\s+reads\b[^\n]*?\b\d+\b)",
        re.IGNORECASE,
    )
    failures = [
        agent_name
        for agent_name in AGENTS_WITH_READ_BUDGET
        if not cap_pattern.search(read_agent(agent_name))
    ]
    assert not failures, f"Agents missing a numeric per-session read cap: {failures}"


# ---------------------------------------------------------------------------
# Positive behavioural contracts (delegated to contract_data.py)
# ---------------------------------------------------------------------------


def test_each_agent_contains_its_required_behavior_contracts():
    for agent_name, required_contracts in AGENT_CONTRACTS.items():
        content = read_agent(agent_name)
        failures = contract_failures(content, required_contracts)
        assert not failures, f"Contract failures in {agent_name}: {failures}"


def test_agent_contracts_are_structured_not_raw_phrase_pins():
    for agent_name, required_contracts in AGENT_CONTRACTS.items():
        assert required_contracts, f"{agent_name} has no behavior contracts"
        for text_contract in required_contracts:
            assert isinstance(text_contract, TextContract)
            assert text_contract.name
            assert text_contract.terms or text_contract.references or text_contract.headings


# ---------------------------------------------------------------------------
# CLAUDE.md global-rule presence — anchored on stable tokens only
# ---------------------------------------------------------------------------


def test_rules_document_minimal_path_and_default_workflow_path():
    """CLAUDE.md must define the minimal-path shortcut without forbidding it.

    We pin the *concept tokens* (`minimal path`, `story-refiner`, `non-trivial`),
    not the surrounding prose. Wording can be edited; the rule cannot vanish.
    """
    rules = (get_source_root() / "CLAUDE.md").read_text(encoding="utf-8")
    lower = rules.lower()
    for token in ("minimal path", "story-refiner", "non-trivial"):
        assert token in lower, f"CLAUDE.md must reference '{token}'"
    assert "xp-pair-programmer" in rules, (
        "CLAUDE.md must name xp-pair-programmer as the minimal-path executor"
    )


def test_quality_tier_section_exists_with_active_tier():
    rules = (get_source_root() / "CLAUDE.md").read_text(encoding="utf-8")

    assert "Quality Tier" in rules
    assert "prototype" in rules
    assert "production" in rules
    active_tiers = re.findall(r"^quality-tier:\s+(prototype|production)", rules, re.MULTILINE)
    assert len(active_tiers) == 1, (
        f"Expected exactly 1 active tier, found {len(active_tiers)}: {active_tiers}"
    )


def test_rules_include_prompt_and_output_controls():
    """Prompt-minimization and concise-communication rules must be present."""
    rules = (get_source_root() / "CLAUDE.md").read_text(encoding="utf-8")
    lower = rules.lower()
    for token in ("prompt minimization", "concise communication", "research depth"):
        assert token in lower, f"CLAUDE.md must define '{token}'"


def test_spike_workflow_exists_in_rules():
    rules = (get_source_root() / "CLAUDE.md").read_text(encoding="utf-8")

    assert "Spike path" in rules
    assert "timebox" in rules.lower()
    assert "research" in rules.lower()


# ---------------------------------------------------------------------------
# Inventory + command-shim parity
# ---------------------------------------------------------------------------


def test_agents_do_not_reference_removed_agent_names():
    source_root = get_source_root()
    for agent_path in (source_root / "agents").glob("*.agent.md"):
        content = agent_path.read_text(encoding="utf-8")
        for removed_name in REMOVED_AGENT_NAMES:
            assert removed_name not in content, (
                f"{agent_path.name} still references removed agent {removed_name}"
            )


def test_commands_reference_only_current_agents():
    source_root = get_source_root()
    command_files = sorted((source_root / "commands").glob("*.md"))
    expected_commands = set(AGENT_CONTRACTS) | UTILITY_COMMANDS

    assert len(command_files) == len(expected_commands)
    command_names = {f.stem for f in command_files}
    assert command_names == expected_commands, (
        f"command files do not match agents + utilities. "
        f"missing: {expected_commands - command_names}, extra: {command_names - expected_commands}"
    )
    for command_file in command_files:
        content = command_file.read_text(encoding="utf-8")
        for removed_name in REMOVED_AGENT_NAMES:
            assert removed_name not in content, (
                f"{command_file.name} still references {removed_name}"
            )


def test_tier_aware_ceremony_exists_in_all_agents():
    for agent_name in AGENT_CONTRACTS:
        content = read_agent(agent_name)
        has_tier = "Tier-aware ceremony" in content or (
            "tier" in content.lower() and "prototype" in content.lower()
        )
        assert has_tier, f"{agent_name} has no tier-aware ceremony documentation"


def test_all_agents_constant_matches_shipped_agents():
    shipped = set(discover_agents(get_source_root()).keys())
    assert shipped == set(ALL_AGENTS)


def test_every_agent_has_a_matching_command():
    source_root = get_source_root()
    commands_dir = source_root / "commands"
    for agent_name in discover_agents(source_root):
        assert (commands_dir / f"{agent_name}.md").exists()


def test_all_reference_paths_in_agents_resolve():
    source_root = get_source_root()
    reference_roots = {
        "knowledge-base": source_root / "knowledge-base",
        "templates": source_root / "templates",
        "skills": source_root / "skills",
    }
    allowed_adopter_paths = {
        ("knowledge-base", "domain-language.md"),
        ("knowledge-base", "quality-gates.md"),
    }

    missing: list[str] = []
    for agent_name, agent_path in discover_agents(source_root).items():
        content = agent_path.read_text(encoding="utf-8")
        for root_name, root_path in reference_roots.items():
            for match in re.findall(rf"`{root_name}/([^`]+)`", content):
                # `<placeholder>` and glob references (e.g. Vale scopes like
                # `knowledge-base/**`) are patterns, not paths to resolve.
                if "<" in match or "*" in match or (root_name, match) in allowed_adopter_paths:
                    continue
                if not (root_path / match).exists():
                    missing.append(f"{agent_name} -> {root_name}/{match}")

    assert not missing, f"Broken references: {missing}"


# ---------------------------------------------------------------------------
# Approval-gate citation — structural, not phrase-exact
# ---------------------------------------------------------------------------


def test_each_agent_cites_approval_gate_canonical_home():
    """Every agent must point at the canonical approval-gate location.

    The location is `CLAUDE.md` followed by the section anchor `Shared
    Rules` or `Approval gate`. We match each piece independently so the
    surrounding markdown (backticks, em-dash, link form) can change
    without breaking the test. Pointer-resolution itself is checked by
    `test_pointer_contracts.py`.
    """
    section_pattern = re.compile(
        r"CLAUDE\.md.*?(Shared Rules|Approval gate)", re.IGNORECASE | re.DOTALL
    )
    failures = [
        agent_name
        for agent_name, agent_path in discover_agents(get_source_root()).items()
        if not section_pattern.search(agent_path.read_text(encoding="utf-8"))
    ]
    assert not failures, (
        f"Agents missing reference to CLAUDE.md § Shared Rules / § Approval gate: {failures}"
    )


# ---------------------------------------------------------------------------
# Negative anti-regression contract
# ---------------------------------------------------------------------------


def test_no_agent_reintroduces_removed_phrase():
    """Phrases we deliberately removed must not creep back in.

    Each entry in `AGENT_FORBIDDEN_PHRASES` carries a reason. If the
    underlying behaviour is intentionally restored, delete the row from
    the contract list rather than working around the test.
    """
    failures: list[str] = []
    for negative in AGENT_FORBIDDEN_PHRASES:
        content = read_agent(negative.agent)
        if negative.forbidden_phrase in content:
            failures.append(
                f"{negative.agent} re-introduced {negative.forbidden_phrase!r} "
                f"(removed because: {negative.reason})"
            )
    assert not failures, "Anti-regression failures:\n  " + "\n  ".join(failures)


# ---------------------------------------------------------------------------
# Targeted positive behavioural pins (tokens, not full sentences)
# ---------------------------------------------------------------------------


def test_slice_planner_records_red_evidence_for_bug_stories():
    """Slice-planner must document RED-evidence capture without committing failures."""
    content = read_agent("slice-planner")
    assert "Capture RED evidence" in content, (
        "slice-planner must require capturing RED evidence for bug stories"
    )
    # Cadence is per-task, not per-TDD-step. Anchor on the canonical concept token.
    assert re.search(r"\bConventional Commit\b", content), (
        "slice-planner must reference the Conventional Commit cadence"
    )


def test_slice_planner_routes_documentation_only_plans_to_docs_maintainer():
    """Slice-planner must not hardcode xp-pair for documentation-only plans."""
    content = read_agent("slice-planner")
    assert "documentation-only plans" in content
    assert "docs-maintainer" in content
    assert "project-specific documentation content" in content
    assert "Use **xp-pair-programmer** for anything" in content
    assert "feature flag wiring" in content


def test_diff_reviewer_supports_direct_review_without_story():
    content = read_agent("diff-reviewer")
    assert "Direct review mode" in content, (
        "diff-reviewer must document a direct-review mode for story-less reviews"
    )
    assert "no story supplied" in content, (
        "diff-reviewer must label coverage as 'no story supplied' in direct mode"
    )
    # CONTRACT-PHRASE (negative): the retired no-story stop gate must not
    # reappear verbatim — direct-review mode replaced it.
    assert "No story? — STOP" not in content, (
        "diff-reviewer must not contradict direct review mode with a no-story stop gate"
    )


def test_incident_responder_writes_only_to_incidents():
    content = read_agent("incident-responder")
    assert "follow-up artifact checklist" in content, (
        "incident-responder must propose follow-ups via a checklist"
    )
    assert re.search(r"Write[^.\n]*incidents/", content), (
        "incident-responder write scope must be limited to incidents/"
    )


def test_code_inspector_is_audit_only_and_approval_gated():
    content = read_agent("code-inspector")
    assert "Preview report" in content
    # Exact-contract phrase: artifact approval prompts are user-facing gates.
    assert "Audit preview above" in content
    assert re.search(r"Write[^.\n]*audits/", content), (
        "code-inspector write scope must be limited to audits/"
    )


def test_docs_maintainer_escalates_adrs_before_drafting():
    content = read_agent("docs-maintainer")
    assert "ADR escalation gate" in content
    assert "advisor tier" in content.lower()


def test_docs_maintainer_write_scope_matches_documentation_surfaces():
    content = read_agent("docs-maintainer")
    for expected_surface in ("docs/", "knowledge-base/", "README.md", "CHANGELOG.md", "docstrings"):
        assert expected_surface in content
    assert "Do not change runtime behaviour" in content


def test_docs_maintainer_mermaid_diagrams_do_not_require_packages():
    content = read_agent("docs-maintainer")
    assert "Mermaid fenced blocks" in content
    assert "Do not search for or install Mermaid packages" in content
    assert "static syntax review" in content


def test_xp_pair_programmer_distinguishes_teachback_checkpoint_from_trailer():
    content = read_agent("xp-pair-programmer")
    assert re.search(r"interactive[^.\n]*teach-back[^.\n]*checkpoint", content)
    assert re.search(r"checkpoint[^.\n]*never removes[^.\n]*`Teach-back:` trailer", content)
    assert "COMMIT-CEREMONY" in content


def test_release_captain_defers_to_release_gates_kb():
    """release-captain must point at the canonical KB section, not redefine gates."""
    content = read_agent("release-captain")
    # Structural pointer — `test_pointer_contracts.py` validates that the
    # heading exists. Pinning the pointer (not a phrase) survives prose edits.
    assert "knowledge-base/release.md` § Release Gates" in content or (
        "`knowledge-base/release.md`" in content and "Release Gates" in content
    ), (
        "release-captain must reference knowledge-base/release.md § Release Gates "
        "rather than restating the gates inline"
    )
    # Releases must explicitly cover commit / tag-create / tag-push as gated
    # actions; we pin the concept tokens, not the connecting prose.
    for token in ("release commit", "tag creation", "tag push"):
        assert token in content, f"release-captain must name '{token}' as a gated action"
