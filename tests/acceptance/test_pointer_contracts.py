"""Contract tests for cross-file markdown section pointers."""

import re

from deploy_ai_playbook.cli import discover_agents, get_source_root

_POINTER_RE = re.compile(
    r"(?<![\w/<])`?(?P<path>(?:(?:knowledge-base|skills|templates|docs|agents|evals)/)?"
    r"[^`<>\s()\]]+\.md)`?"
    r"\s+§\s+"
    # Heading capture stops on terminators: punctuation, pipe, em-dash,
    # backtick, paren, or closing markdown bracket. Multi-section
    # continuations connect via "+ §" or "and §".
    r"([^.,;:)\]\n|+`—]+(?:\s+(?:\+|and)\s+§\s+[^.,;:)\]\n|+`—]+)*)"
)
_HEADING_RE = re.compile(r"^#+\s+(.+)$", re.MULTILINE)
_TOP_LEVEL_POINTER_FILES = {
    "AGENTS.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CODE_OF_CONDUCT.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "README.md",
    "RELEASING.md",
    "SECURITY.md",
}


def _normalize_heading(raw: str) -> str:
    """Normalize a heading or pointer-cited heading for comparison.

    A pointer cites the semantic prefix; target headings often carry
    decoration that doesn't load-bear the meaning. Strip:
    - backticks and trailing punctuation
    - parenthetical decoration `*(scope hint)*` or `(clarification)`
    - em-dash qualifier ` — when the deliverable is tests`
    - leading step enumeration `5. ` (how-to Steps are numbered; pointers
      cite the heading text so they survive renumbering)
    """
    text = raw.strip().strip("`").rstrip(".,;:)").strip()
    text = re.sub(r"\s*\*?\([^)]*\)?\*?\s*$", "", text).strip()
    text = re.sub(r"\s*—\s+.*$", "", text).strip()
    return re.sub(r"^\d+\.\s+", "", text).strip()


def _extract_headings(path) -> set[str]:
    return {_normalize_heading(m) for m in _HEADING_RE.findall(path.read_text())}


def _check_pointer_targets(text: str, source_label: str, source_root) -> list[str]:
    """Return failure messages for dangling `<root>/X.md` § Heading pointers in `text`."""
    failures: list[str] = []
    for match in _POINTER_RE.finditer(text):
        pointer_path = match.group("path")
        heading_block = match.group(2)
        target_relative = _resolve_pointer_path(pointer_path)
        if "<" in pointer_path:
            continue
        target = source_root / target_relative
        if not target.exists():
            failures.append(f"{source_label}: target file missing: {target_relative}")
            continue
        target_headings = _extract_headings(target)
        # Multi-section pointer: `<file>` § A + § B  or  § A and § B
        raw_parts = re.split(r"\s+(?:\+|and)\s+§\s+", heading_block)
        for idx, raw_heading in enumerate(raw_parts):
            heading = _normalize_heading(raw_heading)
            # Only the LAST captured part can have a colon-suffix in source
            # text (the regex split already consumed any `+ §` / `and §`
            # continuations). Look at source text after the regex match to
            # disambiguate `Reference: Agent-First Automation` (colon in
            # heading) from `Configuration: detail follows` (colon ends cite).
            after = text[match.end() :] if idx == len(raw_parts) - 1 else ""
            if _heading_resolves(heading, target_headings, after):
                continue
            line_no = text[: match.start()].count("\n") + 1
            failures.append(
                f"{source_label}:{line_no} pointer to `{target_relative}` § {heading!r} "
                f"does not resolve. Headings in target: {sorted(target_headings)}"
            )
    return failures


def _resolve_pointer_path(pointer_path: str):
    first_part = pointer_path.split("/", 1)[0]
    if first_part in {"knowledge-base", "skills", "templates", "docs", "agents", "evals"}:
        return pointer_path
    if pointer_path in _TOP_LEVEL_POINTER_FILES:
        return pointer_path
    return f"knowledge-base/{pointer_path}"


def _heading_resolves(captured: str, target_headings: set[str], source_after: str = "") -> bool:
    """Match a captured heading against target headings.

    Direct membership wins. Otherwise, look for a target heading
    `<captured>: <suffix>` AND verify that the source text after the regex
    match begins with `: <suffix>` (the colon stopped the regex; the
    suffix sits in the unmatched remainder). This is required to detect
    typos in the suffix — a prefix-only match would silently accept
    `Reference: Agent-First Automaton` against the real heading
    `Reference: Agent-First Automation`.
    """
    return any(
        _single_heading_resolves(candidate, target_headings, source_after)
        for candidate in _heading_candidates(captured)
    )


def _single_heading_resolves(
    captured: str, target_headings: set[str], source_after: str = ""
) -> bool:
    if captured in target_headings:
        return True
    prefix = f"{captured}:"
    candidates = [h for h in target_headings if h.startswith(prefix)]
    if not candidates:
        space_prefix_candidates = [h for h in target_headings if h.startswith(f"{captured} ")]
        return len(space_prefix_candidates) == 1
    if not source_after.startswith(":"):
        return len(candidates) == 1
    # Strip leading colon + whitespace from source remainder; capture up to
    # a sentence terminator (`.` followed by space/EOL, paren, backtick,
    # newline, em-dash, pipe).
    remainder_match = re.match(r":\s*([^.\n)`—|]+)", source_after)
    if not remainder_match:
        return False
    source_suffix = _normalize_heading(remainder_match.group(1))
    return any(h == f"{captured}: {source_suffix}" for h in candidates)


def _heading_candidates(captured: str) -> list[str]:
    candidates = [_normalize_heading(captured)]
    context_patterns = [
        r"\s+§\s+.*$",
        r"\s+applies\b.*$",
        r"\s+already\b.*$",
        r"\s+and\b.*$",
        r"\s+as\b.*$",
        r"\s+before\b.*$",
        r"\s+after\b.*$",
        r"\s+entry\b.*$",
        r"\s+first\b.*$",
        r"\s+for\b.*$",
        r"\s+in\b.*$",
        r"\s+requires\b.*$",
        r"\s+rows?\b.*$",
        r"\s+checklist\b.*$",
        r"\s+citations?\b.*$",
        r"\s+step\s+\d+\b.*$",
        r"\s+still\b.*$",
        r"\s+when\b.*$",
        r"\s+with\b.*$",
        r"\s+[\"“].*$",
        r"\s+→.*$",
    ]
    for pattern in context_patterns:
        candidate = _normalize_heading(re.sub(pattern, "", captured))
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def test_claude_md_section_pointers_resolve():
    """Pointers like `knowledge-base/X.md` § Heading in CLAUDE.md must resolve.

    Catches drift when section headings in target files are renamed without
    updating cross-file pointers in CLAUDE.md.
    """
    source_root = get_source_root()
    claude_md = source_root / "CLAUDE.md"
    failures = _check_pointer_targets(claude_md.read_text(), "CLAUDE.md", source_root)
    assert not failures, "Dangling section pointers in CLAUDE.md:\n" + "\n".join(failures)


def test_agent_section_pointers_resolve():
    """Pointers like `knowledge-base/X.md` § Heading in agent files must resolve.

    Same rules as CLAUDE.md.
    """
    source_root = get_source_root()
    failures: list[str] = []
    for agent_name, agent_path in discover_agents(source_root).items():
        failures.extend(
            _check_pointer_targets(
                agent_path.read_text(),
                f"agents/{agent_name}.agent.md",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in agent files:\n" + "\n".join(failures)


def test_skill_section_pointers_resolve():
    """Pointers in skills/*/SKILL.md must resolve."""
    source_root = get_source_root()
    failures: list[str] = []
    for skill_path in sorted((source_root / "skills").glob("*/SKILL.md")):
        failures.extend(
            _check_pointer_targets(
                skill_path.read_text(),
                f"skills/{skill_path.parent.name}/SKILL.md",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in skill files:\n" + "\n".join(failures)


def test_kb_section_pointers_resolve():
    """Pointers in top-level KB files must resolve.

    CHEATSHEET.md is by-design a one-line digest where loose-form citations
    are intentional; excluded.
    """
    source_root = get_source_root()
    skip = {"CHEATSHEET.md"}
    failures: list[str] = []
    for kb_path in sorted((source_root / "knowledge-base").glob("*.md")):
        if kb_path.name in skip:
            continue
        failures.extend(
            _check_pointer_targets(
                kb_path.read_text(),
                f"knowledge-base/{kb_path.name}",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in KB files:\n" + "\n".join(failures)


def test_pointer_parser_handles_trailing_markdown_bracket(tmp_path):
    """Closing `]` after a heading must not be captured as part of the heading.

    Real prose:
        `[Log line ... per `knowledge-base/security.md` § Data Handling]`

    The parser must capture `Data Handling`, not `Data Handling]`.
    """
    target = tmp_path / "knowledge-base" / "security.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Security\n\n## Data Handling\n\nstuff\n")

    source = "[Log line — link or quote, per `knowledge-base/security.md` § Data Handling]\n"
    failures = _check_pointer_targets(source, "src.md", tmp_path)
    assert failures == [], failures


def test_pointer_parser_handles_colon_in_heading(tmp_path):
    """A target heading containing `:` must be matchable, and typos surface.

    Real prose:
        ``knowledge-base/working-agreement.md` § Reference: Agent-First Automation``

    `_POINTER_RE` stops at the colon, capturing only `Reference`. The
    fix reads the source text after the regex match, expects `: <suffix>`,
    and exact-matches `<captured>: <suffix>` against target headings. A
    typo anywhere in `<suffix>` must surface as a failure rather than
    silently matching the real heading via prefix.
    """
    target = tmp_path / "knowledge-base" / "working-agreement.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Working Agreement\n\n## Reference: Agent-First Automation\n\nstuff\n")

    # Correct cite — must resolve.
    source_ok = (
        "Detail: `knowledge-base/working-agreement.md` § Reference: Agent-First Automation.\n"
    )
    failures = _check_pointer_targets(source_ok, "src.md", tmp_path)
    assert failures == [], f"colon-in-heading citation must resolve: {failures}"

    # Typo in suffix — must NOT be silently masked by prefix-only match.
    source_typo = (
        "Detail: `knowledge-base/working-agreement.md` § Reference: Agent-First Automaton.\n"
    )
    failures = _check_pointer_targets(source_typo, "src.md", tmp_path)
    assert any("'Reference'" in f for f in failures), (
        f"colon-in-heading with typo in suffix must surface as failure: {failures}"
    )


def test_pointer_parser_checks_bare_root_file_pointers(tmp_path):
    target = tmp_path / "CLAUDE.md"
    target.write_text("# Rules\n\n## Shared Rules\n\nstuff\n")

    source_ok = "See CLAUDE.md § Shared Rules.\n"
    assert _check_pointer_targets(source_ok, "src.md", tmp_path) == []

    source_typo = "See CLAUDE.md § Shared Rulez.\n"
    failures = _check_pointer_targets(source_typo, "src.md", tmp_path)
    assert failures, "bare CLAUDE.md section pointer typo must be checked"


def test_pointer_parser_checks_bare_kb_file_pointers(tmp_path):
    target = tmp_path / "knowledge-base" / "testing.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Testing\n\n## Test Quality Rules\n\nstuff\n")

    source_ok = "See testing.md § Test Quality Rules.\n"
    assert _check_pointer_targets(source_ok, "src.md", tmp_path) == []

    source_typo = "See testing.md § Test Quality Rulez.\n"
    failures = _check_pointer_targets(source_typo, "src.md", tmp_path)
    assert failures, "bare KB section pointer typo must be checked"


def test_template_section_pointers_resolve():
    """Pointers in templates/*.md must resolve."""
    source_root = get_source_root()
    failures: list[str] = []
    for template_path in sorted((source_root / "templates").glob("*.md")):
        failures.extend(
            _check_pointer_targets(
                template_path.read_text(),
                f"templates/{template_path.name}",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in template files:\n" + "\n".join(failures)


def test_docs_section_pointers_resolve():
    """Pointers in docs/**/*.md must resolve.

    Recursive glob covers `docs/how-to/` and `docs/adr/` subdirs.
    """
    source_root = get_source_root()
    docs_root = source_root / "docs"
    failures: list[str] = []
    for doc_path in sorted(docs_root.rglob("*.md")):
        failures.extend(
            _check_pointer_targets(
                doc_path.read_text(),
                f"docs/{doc_path.relative_to(docs_root)}",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in docs files:\n" + "\n".join(failures)


def test_eval_section_pointers_resolve():
    """Pointers in evals/*.md must resolve."""
    source_root = get_source_root()
    failures: list[str] = []
    for eval_path in sorted((source_root / "evals").glob("*.md")):
        failures.extend(
            _check_pointer_targets(
                eval_path.read_text(),
                f"evals/{eval_path.name}",
                source_root,
            )
        )
    assert not failures, "Dangling section pointers in eval files:\n" + "\n".join(failures)
