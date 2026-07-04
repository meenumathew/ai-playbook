"""Frontmatter contract validation for adopter pack content.

Core agents and KB files are contract-tested upstream, but adopters never run
those tests — so pack files were the one surface where a malformed file
deployed silently and failed only at runtime (an agent misbehaving, or KB
routing that never fires). This module ports the two frontmatter contracts so
`config validate` (error) and `doctor` (warning) catch the breakage first.

The key lists mirror the upstream contracts: the KB 8-key contract enforced by
`tools/check-kb-frontmatter.py`, and the agent contract pinned by
`tests/acceptance/test_agent_contracts.py`.
"""

from __future__ import annotations

from pathlib import Path

from deploy_ai_playbook.config import Source

KB_REQUIRED_FRONTMATTER: tuple[str, ...] = (
    "id",
    "size",
    "tldr",
    "load_when",
    "audience",
    "canonical_for",
    "cross_refs",
    "verified",
)

AGENT_REQUIRED_FRONTMATTER: tuple[str, ...] = (
    "id",
    "model",
    "load_when",
    "inputs",
    "outputs",
    "handoff",
    "escalation",
)


def validate_pack_content(packs: list[Source]) -> list[str]:
    """Return human-readable findings for pack files that break their contract.

    Empty list when every pack file conforms (or when there are no packs) —
    callers decide severity: `config validate` treats findings as errors,
    `doctor` as warnings.
    """
    findings: list[str] = []
    for pack in packs:
        agents_dir = pack.root / "agents"
        if agents_dir.exists():
            for agent_file in sorted(agents_dir.rglob("*.agent.md")):
                findings.extend(
                    _frontmatter_findings(agent_file, AGENT_REQUIRED_FRONTMATTER, pack.origin)
                )
        kb_dir = pack.root / "knowledge-base"
        if kb_dir.exists():
            for kb_file in sorted(kb_dir.rglob("*.md")):
                if kb_file.name == "README.md":
                    continue
                findings.extend(
                    _frontmatter_findings(kb_file, KB_REQUIRED_FRONTMATTER, pack.origin)
                )
    return findings


def _frontmatter_findings(path: Path, required: tuple[str, ...], origin: str) -> list[str]:
    label = f"{origin}: {path.name}"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{label} could not be read: {exc.strerror or exc.__class__.__name__}"]
    if not text.startswith("---\n"):
        return [f"{label} is missing the frontmatter block (required keys: {', '.join(required)})"]
    end = text.find("\n---", 4)
    if end < 0:
        return [f"{label} has an unterminated frontmatter block"]
    keys: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if ":" not in line or line.startswith((" ", "\t", "#")):
            continue
        key, _, value = line.partition(":")
        keys[key.strip()] = value.strip()
    missing = [key for key in required if not keys.get(key)]
    if missing:
        return [f"{label} missing/empty frontmatter key(s): {', '.join(missing)}"]
    return []
