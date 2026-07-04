"""Skill operation-surface contracts.

Skills like `host-adapter`, `notifier`, and `issue-fetch` expose a vendor-neutral
operation API that agents call by name (`host.pr.create`, `notify(release_shipped,
…)`, `issue.fetch`). When an agent references an operation, event, or config key
that the skill never declares, the playbook ships a silent broken surface — the
agent calls into the void.

These tests are structural, not phrase-pinned: they walk every agent and CLAUDE.md,
extract operation references, and require each to resolve to a declaration in the
corresponding skill. They also pin the safe-default fallbacks (notifier `none`,
issue-fetch manual paste) and the failure-mode coverage adopters need to wire new
providers in.
"""

from __future__ import annotations

import re
from pathlib import Path

from deploy_ai_playbook.cli import get_source_root
from tests.acceptance.contract_data import read_skill


def _agent_and_rules_text() -> dict[str, str]:
    source_root = get_source_root()
    files: dict[str, str] = {"CLAUDE.md": (source_root / "CLAUDE.md").read_text()}
    for path in sorted((source_root / "agents").glob("*.agent.md")):
        files[f"agents/{path.name}"] = path.read_text()
    return files


def _strip_code_fences(content: str) -> str:
    """Remove fenced blocks so example/snippet text isn't treated as a binding call."""
    return re.sub(r"```.*?```", "", content, flags=re.DOTALL)


def test_every_host_pr_operation_referenced_by_agents_is_declared_in_host_adapter():
    skill = read_skill("host-adapter")
    declared = set(re.findall(r"`host\.pr\.([a-z_]+)\(", skill))
    assert declared, (
        "host-adapter must declare host.pr.<op> entries with a heading like `host.pr.diff(ref)`"
    )

    referenced: dict[str, set[str]] = {}
    for ref_path, content in _agent_and_rules_text().items():
        for op in re.findall(r"host\.pr\.([a-z_]+)", content):
            referenced.setdefault(op, set()).add(ref_path)

    undeclared = {op: sources for op, sources in referenced.items() if op not in declared}
    assert not undeclared, (
        "Agents reference host.pr ops that skills/host-adapter/SKILL.md never declares: "
        f"{undeclared}. Either remove the reference or add the operation to the skill."
    )


def test_every_notifier_event_emitted_by_agents_is_a_canonical_event_name():
    skill = read_skill("notifier")
    canonical_section = re.search(
        r"###\s+Canonical event names\s*\n(.*?)(?=\n##\s|\Z)",
        skill,
        re.DOTALL,
    )
    assert canonical_section, "notifier SKILL.md must keep a `### Canonical event names` table"
    declared = set(re.findall(r"`([a-z_]+)`", canonical_section.group(1)))
    assert declared, "notifier canonical event names table must list events in backticks"

    pattern = re.compile(r"emit\s+`([a-z_]+)`")
    referenced: dict[str, set[str]] = {}
    for ref_path, content in _agent_and_rules_text().items():
        if ref_path.endswith("/notifier/SKILL.md"):
            continue
        body = _strip_code_fences(content)
        for event in pattern.findall(body):
            referenced.setdefault(event, set()).add(ref_path)

    undeclared = {event: sources for event, sources in referenced.items() if event not in declared}
    assert not undeclared, (
        "Agents emit notifier events that skills/notifier/SKILL.md doesn't list as canonical: "
        f"{undeclared}. Add the event to the canonical table or correct the agent."
    )


def test_skills_declare_failure_modes_or_fallback_path():
    """Every vendor-neutral skill must document its failure surface.

    Without a declared failure mode an adopter wiring a new provider has no
    contract for what to do when the provider returns 4xx, 5xx, or is missing
    config. We don't pin wording — we just require the section exists.
    """
    expected = {
        "host-adapter": ("Failure Modes",),
        "notifier": ("Failure Modes",),
        "issue-fetch": ("Manual Paste Fallback",),
    }
    missing: list[str] = []
    for skill_name, headings in expected.items():
        body = read_skill(skill_name)
        missing.extend(
            f"skills/{skill_name}/SKILL.md missing `## {heading}`"
            for heading in headings
            if not re.search(rf"^##\s+{re.escape(heading)}\s*$", body, re.MULTILINE)
        )
    assert not missing, missing


def test_notifier_default_provider_is_safe_and_documented_as_no_op():
    """`provider = "none"` must remain the default so first-time adopters don't accidentally page.

    Verified at the skill level (not just config) so the contract survives even
    if someone moves the example .toml around.
    """
    skill = read_skill("notifier")
    assert re.search(r'provider\s*=\s*"slack".*\bnone\s*\(default\)', skill, re.DOTALL), (
        "notifier SKILL.md must document `none` as the default provider"
    )
    assert "no-op" in skill.lower() or "Default `none`" in skill, (
        "notifier SKILL.md must call out that the default provider does not send"
    )


def test_notifier_payloads_are_sanitized_before_external_send():
    skill = read_skill("notifier")

    # STRUCTURE-MARKER: section heading must exist; body wording is free to evolve.
    assert "## Sanitization" in skill
    # CONTRACT-PHRASE: these are the explicit categories the skill MUST list.
    # Removing one is a contract change — silent drop = silent leakage of that category.
    for required in ("raw issue bodies", "logs", "stack traces", "context"):
        assert required in skill
    # CONTRACT-PHRASE (negative): forbidden anti-patterns. Re-introducing either
    # phrase signals the skill drifted back toward unsafe defaults.
    assert "Print response body" not in skill
    assert "would have sent: <event> <message>" not in skill
    # STRUCTURE-MARKER: indirect env expansion is unsafe regardless of wording.
    assert "${!" not in skill, "notifier snippets must not use indirect env expansion"


def test_issue_fetch_resolves_locally_before_calling_a_provider():
    """`Step 0: Resolve Locally First` is the rule that lets adopters work offline.

    Removing it would push every story-refiner session into a network call; pin
    its presence so the offline path can't silently regress.
    """
    skill = read_skill("issue-fetch")
    assert re.search(r"^##\s+Step 0:\s+Resolve Locally First", skill, re.MULTILINE), (
        "issue-fetch SKILL.md must keep `Step 0: Resolve Locally First` so agents "
        "can short-circuit on local story artifacts"
    )
    assert "stories/" in skill, (
        "issue-fetch SKILL.md must point at story artifacts for local resolution"
    )


def test_external_provider_skills_minimize_error_and_pasted_content():
    issue_fetch = read_skill("issue-fetch")
    host_adapter = read_skill("host-adapter")

    # STRUCTURE-MARKER: section heading must exist; body wording is free to evolve.
    assert "## Sanitized Record Contract" in issue_fetch
    # CONTRACT-PHRASE: these are user-visible skill rules. Re-wording them loosens
    # the rule (e.g. "Avoid asking for credentials" is weaker than "Do not ask").
    assert "Do not ask for credentials" in issue_fetch
    assert "Never print raw provider responses" in issue_fetch
    # CONTRACT-PHRASE (negative): the skill must not regress to credential prompting.
    assert "prompt the user for credentials" not in issue_fetch

    # STRUCTURE-MARKER: section heading must exist.
    assert "## Output Safety" in host_adapter
    # CONTRACT-PHRASE: raw API body printing is a leak-class rule pinned by exact wording.
    assert "Do not print raw API response bodies" in host_adapter
    # CONTRACT-PHRASE (negative): "Print exact response" was an old anti-pattern;
    # if it reappears, the skill regressed.
    assert "Print exact response" not in host_adapter


def test_skills_referencing_ai_playbook_toml_declare_a_provider_key():
    """Each vendor-neutral skill that reads .ai-playbook.toml must show its `provider =` key.

    Adopters who deploy a new pack copy the example skeleton; if the skill stops
    documenting the key, the example drifts and provider selection breaks.
    """
    expected_section_keys = {
        "host-adapter": "[host]",
        "notifier": "[notifier]",
        "issue-fetch": "[issue-tracker]",
    }
    failures: list[str] = []
    for skill_name, section in expected_section_keys.items():
        body = read_skill(skill_name)
        if section not in body:
            failures.append(f"skills/{skill_name}/SKILL.md missing `{section}` section in config")
            continue
        idx = body.index(section)
        window = body[idx : idx + 400]
        if "provider" not in window:
            failures.append(
                f"skills/{skill_name}/SKILL.md `{section}` block must declare a `provider` key"
            )
    assert not failures, failures


def test_release_captain_uses_only_declared_host_pr_operations():
    """Defence in depth on the release path: release-captain is the only agent
    that mutates host state, so cross-check it explicitly even though the
    generic test above already covers it."""
    source_root = get_source_root()
    agent = (source_root / "agents" / "release-captain.agent.md").read_text()
    used = set(re.findall(r"host\.pr\.([a-z_]+)", agent))
    must_use = {"create", "checks", "merge"}
    assert must_use <= used, f"release-captain must reference {must_use}; saw {used}"

    declared = set(re.findall(r"`host\.pr\.([a-z_]+)\(", read_skill("host-adapter")))
    assert used <= declared, (
        f"release-captain references host.pr ops not in host-adapter: {used - declared}"
    )


def test_skill_operation_tests_walk_at_least_the_known_skills():
    """Sanity guard: if someone removes a skill but forgets to update tests, fail loudly."""
    skills_dir: Path = get_source_root() / "skills"
    expected = {"host-adapter", "notifier", "issue-fetch"}
    found = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    assert expected <= found, f"Vendor-neutral skills missing from repo: {expected - found}"


def test_vendor_neutral_skills_state_contract_boundary():
    # CONTRACT-PHRASE: these phrases are how each skill tells adopters the
    # boundary between markdown contract and runtime code. Re-wording them
    # blurs that boundary — exactly the README ambiguity PR-A clarified.
    for skill_name in ("host-adapter", "issue-fetch", "notifier"):
        body = read_skill(skill_name)
        assert "agent operation contract" in body
        assert "not a Python runtime" in body
        assert "src/deploy_ai_playbook/" in body
