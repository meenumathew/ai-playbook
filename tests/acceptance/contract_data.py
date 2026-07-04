"""Shared contract data and readers for acceptance contract tests."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from deploy_ai_playbook.cli import get_source_root

TEST_NAME_PATTERN = "test_<what>_<condition>"


@dataclass(frozen=True)
class TextContract:
    """A behavior/documentation contract without pinning one exact sentence."""

    name: str
    terms: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    headings: tuple[str, ...] = ()


def contract(
    name: str,
    *,
    terms: tuple[str, ...] = (),
    references: tuple[str, ...] = (),
    headings: tuple[str, ...] = (),
) -> TextContract:
    return TextContract(name=name, terms=terms, references=references, headings=headings)


AGENT_CONTRACTS = {
    "story-refiner": [
        contract(
            "classifies work shape before writing",
            terms=("bug", "spike", "story", "chore"),
            references=("templates/story-bug-template.md", "templates/story-spike-template.md"),
        ),
        contract(
            "asks only material questions",
            terms=("highest-leverage", "question", "Prompt minimization"),
        ),
        contract(
            "researches but does not implement",
            terms=("Never write code", "plans", "implication"),
            references=("knowledge-base/domain-language.md", "knowledge-base/philosophy.md"),
        ),
    ],
    "slice-planner": [
        contract(
            "produces a plan and stops",
            terms=("complete plan artifact", "STOP", "Do not write source code"),
        ),
        contract(
            "keeps planning scoped",
            terms=("Prompt minimization", "Write is scoped", "plans/", "stories/"),
        ),
        contract(
            "names with domain language",
            terms=("domain-language.md", "before naming"),
        ),
    ],
    "xp-pair-programmer": [
        contract("requires TDD", terms=("production code", "failing test", "One test at a time")),
        contract(
            "supports interaction modes",
            terms=("Interactive mode", "Low-prompt", "user acknowledgment"),
        ),
        contract(
            "covers acceptance and test stories",
            terms=("Test-story", "Outer loop", TEST_NAME_PATTERN, "test_ac_<what>_<condition>"),
            references=("knowledge-base/testing.md",),
        ),
        contract(
            "keeps workflow metadata out of code",
            terms=("Ticket Context Belongs in Commits, Not Code", "workflow metadata"),
            references=("knowledge-base/style-guide.md",),
        ),
    ],
    "diff-reviewer": [
        contract("supports direct review", terms=("Direct review mode", "no story supplied")),
        contract(
            "checks quality anchors",
            references=(
                "knowledge-base/security.md",
                "knowledge-base/observability.md",
                "knowledge-base/performance.md",
            ),
        ),
        contract(
            "flags workflow metadata in code",
            terms=("Ticket Context Belongs in Commits, Not Code", "workflow artifact metadata"),
            references=("knowledge-base/style-guide.md",),
        ),
    ],
    "code-inspector": [
        contract("saves scored audits", terms=("scored", "audits/")),
        contract("reviews large scopes safely", terms=("Review in chunks",)),
        contract(
            "checks audit anchors",
            references=(
                "knowledge-base/security.md",
                "knowledge-base/performance.md",
                "knowledge-base/testing.md",
            ),
        ),
    ],
    "docs-maintainer": [
        contract("previews before saving", terms=("Preview", "approval")),
        contract(
            "handles ADRs explicitly", references=("docs/adr/",), terms=("ADR escalation gate",)
        ),
        contract("documents why and how", terms=("why", "how-to-use", "code already shows")),
        contract(
            "keeps workflow metadata out of docstrings",
            terms=("Ticket Context Belongs in Commits, Not Code", "workflow artifact IDs"),
            references=("knowledge-base/style-guide.md",),
        ),
    ],
    "release-captain": [
        contract(
            "uses host adapter operations",
            references=("skills/host-adapter/SKILL.md",),
            terms=("host.pr.create", "host.pr.checks", "host.pr.merge"),
        ),
        contract(
            "approval gates irreversible actions",
            references=("knowledge-base/release.md",),
            terms=("Say 'merge'", "Say 'push'", "Never auto-merge", "Never push"),
        ),
        contract("emits release notifications", references=("skills/notifier/SKILL.md",)),
    ],
    "incident-responder": [
        contract(
            "uses incident and debugging canon",
            references=("knowledge-base/incident-response.md", "knowledge-base/debugging.md"),
        ),
        contract(
            "keeps production safe", terms=("read-only", "Production state-changing commands")
        ),
        contract("keeps response blameless", terms=("roles", "names", "blameless")),
        contract(
            "writes postmortems and notifications",
            references=("templates/postmortem-template.md", "skills/notifier/SKILL.md"),
        ),
    ],
}

KB_CONTRACTS = {
    "testing.md": [
        contract(
            "testing discipline",
            headings=("Acceptance Test (AT) Standards", "When Tests Are Hard to Write"),
            terms=("FIRST", "Arrange-Act-Assert", TEST_NAME_PATTERN, "70%"),
        ),
    ],
    "testing-techniques.md": [
        contract(
            "advanced testing guidance",
            headings=(
                "Property-Based Testing",
                "Async and Event-Driven Test Patterns",
                "Mutation Testing",
                "Contract Testing",
                "Language-Specific Techniques",
            ),
            terms=("Message consumer acceptance tests", "critical-path registry", "pre-commit"),
        ),
    ],
    "languages/testing-python.md": [
        contract(
            "python testing conventions",
            headings=("Python pytest Techniques",),
            terms=("pytest-mock", "unittest.mock", "Parametrize", "Exception Testing"),
            references=("testing-techniques.md",),
        ),
    ],
    "languages/python.md": [
        contract(
            "python implementation conventions",
            terms=("PEP 8", "ruff", "pyright", "Pydantic v2", "TypedDict", "Protocol"),
        ),
    ],
    "security.md": [
        contract(
            "security review surface",
            headings=("Code Review Security Checklist",),
            terms=("SQL injection", "XSS", "CSRF", "SSRF", "CORS", "Rate limiting"),
        ),
        contract("auth rule", terms=("Never roll your own auth",)),
    ],
    "observability.md": [
        contract(
            "observability signals",
            headings=("Metrics", "Tracing", "Health Checks"),
            terms=("exc_info=True", "Never silently swallow exceptions"),
        ),
    ],
    "design-patterns.md": [
        contract(
            "design review patterns",
            terms=(
                "Silent Misalignment",
                "Flying Blind",
                "Sunk Cost",
                "Language/framework conventions",
            ),
        ),
    ],
    "INDEX.md": [
        contract(
            "routing taxonomy",
            terms=("Loading Rule", "Exact Section Routing", "Task-core", "Triggered", "Reference"),
            references=("testing.md", "security.md", "observability.md", "performance.md"),
        ),
    ],
    "performance.md": [
        contract(
            "performance review surface",
            headings=("Data Structure Selection", "Performance Review Checklist"),
            terms=("N+1", "O(n^2)", "Profile First"),
        ),
    ],
}

SKILL_CONTRACTS = {
    "git": [
        contract(
            "commit discipline",
            headings=("Commit Workflow", "Teach-back Trailer"),
            terms=("NEVER skip hooks", "One logical change", "Body explains", "hotfix"),
        ),
        contract(
            "merge safety",
            headings=("Squashing Commits", "Merge Conflict Resolution"),
            terms=("Run tests before and after", "Wait for user direction", "git merge --abort"),
        ),
    ],
    "story-writing": [
        contract(
            "story quality",
            headings=("INVEST Quick Check", "Story Point Sizing"),
            terms=(TEST_NAME_PATTERN, ">8 points"),
        ),
    ],
    "retrospective": [
        contract(
            "retrospective loop",
            headings=("The Loop",),
            terms=("Review Signals", "Surface", "Propose", "Approve", "Apply"),
        ),
    ],
    "issue-fetch": [
        contract(
            "work item intake adapters",
            headings=(
                "Adapter Selection",
                "Jira Adapter",
                "GitHub Adapter",
                "GitLab Adapter",
                "Bitbucket Adapter",
                "Manual Paste Fallback",
                "Untrusted Input",
            ),
            terms=("Resolve Locally First",),
        ),
    ],
    "host-adapter": [
        contract(
            "host operation API",
            headings=("Operations", "Adding a New Provider"),
            terms=(
                "host.pr.diff",
                "host.pr.review",
                "host.pr.create",
                "host.pr.merge",
                "host.pr.checks",
            ),
        ),
        contract("host configuration", terms=(".ai-playbook.toml",)),
    ],
    "notifier": [
        contract(
            "notification API",
            headings=("Operations", "Canonical event names", "Approval Gate"),
            terms=("notify(event, message, severity", "Default is `none`", "[notifier]"),
        ),
        contract(
            "canonical notification events",
            terms=(
                "release_shipped",
                "smoke_fail",
                "incident_sev1",
                "incident_resolved",
                "postmortem_ready",
            ),
        ),
    ],
}

AGENTS_WITH_READ_BUDGET = {
    "story-refiner",
    "slice-planner",
    "diff-reviewer",
    "code-inspector",
    "docs-maintainer",
    "release-captain",
    "incident-responder",
}
# xp-pair-programmer is deliberately absent: implementation reads as needed
# and self-tracks without a numeric cap (CLAUDE.md § Shared Rules § Read budget).

REMOVED_AGENT_NAMES = ["story-writer", "codebase-researcher", "adr-writer"]
UTILITY_COMMANDS = {"status"}


@dataclass(frozen=True)
class NegativeContract:
    """A phrase that was deliberately removed from an agent file.

    Anti-regression guard: the phrase must NOT reappear. Pair every entry
    with the rationale (`reason`) so a future contributor can decide whether
    to update the contract or revert their change.
    """

    agent: str
    forbidden_phrase: str
    reason: str


# Anti-regression list. Each entry encodes a behavioural decision that was
# made and recorded — not editorial preference. Add a row only when removing
# behaviour from an agent; remove a row only when the underlying decision is
# explicitly reversed.
AGENT_FORBIDDEN_PHRASES: tuple[NegativeContract, ...] = (
    NegativeContract(
        agent="slice-planner",
        forbidden_phrase="Commit the failing test",
        reason="bug stories: regression test stays uncommitted until green (Iron Law)",
    ),
    NegativeContract(
        agent="slice-planner",
        forbidden_phrase="every step ends with a Conventional Commit",
        reason="commit cadence is per-task, not per-TDD-step",
    ),
    NegativeContract(
        agent="diff-reviewer",
        forbidden_phrase="Do not review without an AC anchor.",
        reason="diff-reviewer supports direct review without a story",
    ),
    NegativeContract(
        agent="diff-reviewer",
        forbidden_phrase="No story? — STOP.",
        reason=(
            "diff-reviewer direct review mode proceeds without a story and marks "
            "AC coverage as no story supplied"
        ),
    ),
    NegativeContract(
        agent="incident-responder",
        forbidden_phrase="opens follow-up stories and ADRs",
        reason="incident-responder proposes follow-ups; ownership stays with story-refiner",
    ),
    NegativeContract(
        agent="incident-responder",
        forbidden_phrase="Write: scoped to `incidents/`, `stories/`, `docs/adr/`",
        reason="incident-responder writes only into incidents/; cross-tree writes were removed",
    ),
    NegativeContract(
        agent="code-inspector",
        forbidden_phrase="Write scoped to `audits/` and `knowledge-base/`",
        reason="code-inspector is audit-only; KB writes were removed",
    ),
    NegativeContract(
        agent="release-captain",
        forbidden_phrase="Single gate at merge",
        reason="release uses canonical multi-step gates, not a single merge approval",
    ),
)


def read_agent(agent_name: str) -> str:
    source_root = get_source_root()
    return (source_root / "agents" / f"{agent_name}.agent.md").read_text()


def read_kb(filename: str) -> str:
    source_root = get_source_root()
    return (source_root / "knowledge-base" / filename).read_text()


def read_skill(skill_name: str) -> str:
    source_root = get_source_root()
    return (source_root / "skills" / skill_name / "SKILL.md").read_text()


def contract_failures(content: str, contracts: Sequence[TextContract]) -> list[str]:
    """Return human-readable failures for structured text contracts."""
    lower_content = content.lower()
    headings = _markdown_headings(content)
    failures: list[str] = []
    for text_contract in contracts:
        missing_terms = [term for term in text_contract.terms if term.lower() not in lower_content]
        missing_references = [ref for ref in text_contract.references if ref not in content]
        missing_headings = [
            heading
            for heading in text_contract.headings
            if _normalize_heading(heading) not in headings
        ]
        missing_parts = []
        if missing_terms:
            missing_parts.append(f"terms={missing_terms!r}")
        if missing_references:
            missing_parts.append(f"references={missing_references!r}")
        if missing_headings:
            missing_parts.append(f"headings={missing_headings!r}")
        if missing_parts:
            failures.append(f"{text_contract.name}: " + ", ".join(missing_parts))
    return failures


def _markdown_headings(content: str) -> set[str]:
    return {
        _normalize_heading(match.group(1))
        for match in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)
    }


def _normalize_heading(heading: str) -> str:
    text = heading.strip().strip("`*_ ").rstrip("#").strip()
    return re.sub(r"\s+", " ", text).lower()
