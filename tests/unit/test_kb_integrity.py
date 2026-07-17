"""Knowledge-base integrity tests — guardrails for the playbook's own docs.

These tests catch the class of bug a 95%-coverage Python suite cannot:
text-level rot in CLAUDE.md, agent files, skill files, and KB files. Examples
of bugs caught here:

  - Citation `foo.md § Bar` where `foo.md` exists but `## Bar` does not
  - Reference to a renamed file pattern (`AUDIT-YYYY-MM-DD-` after rename to `AUDIT-NNN-`)
  - Frontmatter key removed from templates but still referenced in agent specs
  - Agent declared in `agents/` with no matching `commands/<id>.md` shim
  - KB file missing required frontmatter (`id`, `tldr`, `verified`, etc.)

The tests run as part of the regular pytest job — no separate CI step needed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
KB_DIR = REPO_ROOT / "knowledge-base"
AGENTS_DIR = REPO_ROOT / "agents"
COMMANDS_DIR = REPO_ROOT / "commands"
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATES_DIR = REPO_ROOT / "templates"
DOCS_DIR = REPO_ROOT / "docs"
EVALS_DIR = REPO_ROOT / "evals"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"


# ---------------------------------------------------------------------------
# File discovery helpers
# ---------------------------------------------------------------------------


def _markdown_files_to_check() -> list[Path]:
    """All markdown files whose text is part of the playbook contract.

    Excludes adopter-generated artifacts (stories/, plans/, research/, audits/,
    reviews/, incidents/) which are local-only and not shipped with the playbook.
    """
    roots = [
        CLAUDE_MD,
        # README is the most-read file and was the last doc surface outside
        # the contract — stale chains and dead operation IDs
        # survived there while every checked file stayed clean.
        REPO_ROOT / "README.md",
        *AGENTS_DIR.glob("*.md"),
        *COMMANDS_DIR.glob("*.md"),
        *KB_DIR.rglob("*.md"),
        *SKILLS_DIR.rglob("SKILL.md"),
        *TEMPLATES_DIR.glob("*.md"),
        *DOCS_DIR.rglob("*.md"),
        *EVALS_DIR.rglob("*-expected.md"),
        *EVALS_DIR.rglob("*-input.md"),
    ]
    # De-duplicate (CLAUDE.md is already a file, the rest are globs).
    return sorted({p for p in roots if p.is_file()})


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Stale-pattern guards
#
# Each entry is a renamed pattern that used to be valid. If any new file
# reintroduces the old form, the test fails with the file:line that contains it.
# Add new entries here when you rename a file pattern, frontmatter key, or
# section name across the playbook.
# ---------------------------------------------------------------------------

STALE_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, human-readable name, replacement guidance)
    (
        r"AUDIT-YYYY-MM-DD-",
        "AUDIT-YYYY-MM-DD- filename pattern",
        "audits/ uses AUDIT-NNN-<scope>.md (zero-padded number); "
        "see agents/code-inspector.agent.md",
    ),
    (
        r"^\s*jira-key:",
        "jira-key: frontmatter key",
        "Use the canonical issue-ref: field; "
        "see skills/story-writing/SKILL.md § Frontmatter Fields",
    ),
    (
        r"^\s*github-issue:",
        "github-issue: frontmatter key",
        "Use the canonical issue-ref: field",
    ),
    (
        r"^\s*linear-id:",
        "linear-id: frontmatter key",
        "Use the canonical issue-ref: field",
    ),
    (
        r"0001-host-adapter-skill\.md",
        "reference to non-existent ADR 0001-host-adapter-skill.md",
        "ADR-0001 is 0001-bitbucket-server-not-supported.md",
    ),
    (
        r"\bdecision caption\b",
        "'decision caption' as a separate concept",
        "DoD merges decision rationale with the Teach-back: trailer; "
        "see CLAUDE.md § Definition of Done",
    ),
    (
        r"ai-playbook telemetry (status|enable|disable) --tool\b",
        "telemetry subcommand example with --tool",
        "Telemetry subcommands are Claude-only and do not accept --tool; "
        "use `ai-playbook telemetry status`.",
    ),
    (
        r"these four operations",
        "host-adapter 'four operations' phrasing",
        "host-adapter has five operations: diff, review, create, merge, checks",
    ),
]


@pytest.mark.parametrize(
    "pattern,name,guidance",
    STALE_PATTERNS,
    ids=[name for _, name, _ in STALE_PATTERNS],
)
def test_no_stale_patterns(pattern: str, name: str, guidance: str) -> None:
    """No file in the playbook contract reintroduces a renamed/removed pattern."""
    regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
    hits: list[str] = []
    for path in _markdown_files_to_check():
        # Skip this test file itself — STALE_PATTERNS is the authoritative list,
        # and the regexes appear here as data.
        if path == Path(__file__):
            continue
        for lineno, line in enumerate(_read(path).splitlines(), start=1):
            if regex.search(line):
                rel = path.relative_to(REPO_ROOT)
                hits.append(f"  {rel}:{lineno}: {line.strip()}")
    assert not hits, (
        f"Found {len(hits)} occurrence(s) of stale pattern: {name}\n"
        f"Guidance: {guidance}\n\n" + "\n".join(hits)
    )


# ---------------------------------------------------------------------------
# Cross-reference integrity
#
# Citations look like `file.md § Section Heading`. When file.md exists in the
# repo, we verify that an `## Section Heading` (or `### …`) actually exists
# in that file. External-only files (e.g. CLAUDE.md sections, docs/adr/README)
# are also resolved from the repo root.
# ---------------------------------------------------------------------------

# Files whose section anchors are referenced but live in non-standard locations.
# Map citation prefix -> path on disk.
CITATION_FILE_MAP: dict[str, Path] = {
    "CLAUDE.md": CLAUDE_MD,
    "SECURITY.md": REPO_ROOT / "SECURITY.md",
    "docs/adr/README.md": DOCS_DIR / "adr" / "README.md",
    "docs/docs-guide.md": DOCS_DIR / "docs-guide.md",
    "docs/limitations.md": DOCS_DIR / "limitations.md",
}


# Citations to ignore. Some references are deliberately abstract (`<lang>.md`),
# point at external URLs, or are placeholders inside templates.
IGNORED_CITATION_FILES: set[str] = {
    "languages/<lang>.md",
    "languages/testing-<lang>.md",
    "templates/<lang>-template.md",
    "stories/<PREFIX>-NNN-slug.md",
    "stories/STORY-NNN-slug.md",
    "incidents/INC-YYYY-MM-DD-slug.md",
    "audits/AUDIT-NNN-scope.md",
    "audits/AUDIT-NNN-<scope>.md",
    "plans/PLAN-NNN-slug.md",
    "research/RESEARCH-NNN-slug.md",
    "reviews/REVIEW-NNN-<slug>.md",
    # templates/agent-template.md uses these placeholders to teach the
    # citation pattern without picking a specific KB file or operation.
    "knowledge-base/<file>.md",
}


CITATION_RE = re.compile(
    # Match `file.md § Heading`. The raw heading is normalised by
    # _trim_cited_section so this regex stays simple and maintainable.
    r"`?([A-Za-z0-9_./<>-]+\.md)`?\s+§\s+([^§\n]+)",
)

SECTION_BOUNDARY_CHARS = set("()+|*_,;:\"'")
SECTION_TRAILING_CHARS = "+-—.,;:!?)\"' \t"
HEADING_PREFIX_BOUNDARIES = (":", " ", "—", "-")


def _trim_cited_section(raw_section: str) -> str:
    """Trim prose and table separators after a cited section name."""
    chars: list[str] = []
    for index, char in enumerate(raw_section):
        if char in SECTION_BOUNDARY_CHARS or char == "—":
            break
        if char == "." and _period_ends_citation(raw_section, index):
            break
        chars.append(char)
    return "".join(chars).strip()


def _period_ends_citation(raw_section: str, index: int) -> bool:
    return index == len(raw_section) - 1 or raw_section[index + 1].isspace()


def _citation_matches(line: str) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    for match in CITATION_RE.finditer(line):
        cited_section = _trim_cited_section(match.group(2))
        if cited_section:
            matches.append((match.group(1), cited_section))
    return matches


def _resolve_cited_file(citation: str) -> Path | None:
    """Resolve a citation's file part (e.g. `testing.md`, `skills/git/SKILL.md`)
    to an absolute path inside the repo, or None if it cannot be resolved."""
    if citation in IGNORED_CITATION_FILES:
        return None
    if citation in CITATION_FILE_MAP:
        return CITATION_FILE_MAP[citation]
    # Bare KB filename like `testing.md`
    bare = KB_DIR / citation
    if bare.is_file():
        return bare
    # Path relative to repo root (skills/, agents/, templates/, docs/)
    rooted = REPO_ROOT / citation
    if rooted.is_file():
        return rooted
    # Languages subdir
    if "/" not in citation and citation.startswith("languages/"):
        return KB_DIR / citation
    return None


def _section_matches(cited: str, headings: set[str]) -> bool:
    """True when `cited` matches one of `headings`.

    Citations are lossy summaries — `§ Phase 1` may legitimately reference a
    heading like `## Phase 1: Investigate — Build a Feedback Loop`. We accept
    a match when the cited text is the exact heading OR a clean prefix of it
    (followed by `:` or `—` or end-of-string). We also progressively trim
    trailing words to handle citations like `§ Iron Law and 3-Fix Stop Rule`.
    """
    return any(
        _candidate_matches_headings(candidate, headings) for candidate in _section_candidates(cited)
    )


def _section_candidates(cited: str) -> list[str]:
    cleaned = _clean_section_text(cited)
    if not cleaned:
        return []

    words = cleaned.split()
    candidates = [cleaned]
    for word_count in range(len(words) - 1, 0, -1):
        candidate = _clean_section_text(" ".join(words[:word_count]))
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    return candidates


def _clean_section_text(text: str) -> str:
    return text.strip().lstrip("\"'").rstrip(SECTION_TRAILING_CHARS)


def _candidate_matches_headings(candidate: str, headings: set[str]) -> bool:
    return candidate in headings or any(_heading_has_clean_prefix(candidate, h) for h in headings)


def _heading_has_clean_prefix(candidate: str, heading: str) -> bool:
    if not heading.startswith(candidate):
        return False
    tail = heading[len(candidate) :]
    return not tail or tail[0] in HEADING_PREFIX_BOUNDARIES


def _section_headings(content: str) -> set[str]:
    """Return the set of `## …` and `### …` heading texts in a markdown file.

    Headings are stripped of trailing punctuation and compared case-insensitively
    by the caller so that "## Iron Law" matches a citation of "§ Iron Law".
    """
    headings: set[str] = set()
    for line in content.splitlines():
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if m:
            heading = m.group(1).strip()
            # Drop trailing parentheticals and emphasis markers for tolerant matching.
            heading = re.sub(r"\s*\([^)]*\)\s*$", "", heading)
            heading = heading.strip("*_` ")
            headings.add(heading.lower())
            # How-to Steps are numbered (`### 5. Use the Fast Lane …`); citations
            # use the heading text so they survive renumbering. Index both forms.
            unnumbered = re.sub(r"^\d+\.\s+", "", heading)
            if unnumbered != heading:
                headings.add(unnumbered.lower())
    return headings


# Citation budget — known broken `file.md § Section` references at the time
# this test was introduced. The point of the budget is to *prevent regressions*
# (new broken citations) without blocking CI on the long tail of pre-existing
# ones, which need targeted content fixes the test cannot make on its own.
#
# The number ratchets DOWN over time. Fix a citation, then update this number.
# It must NEVER ratchet up — adding broken citations is a hard failure.
CITATION_BUDGET = 0


def _broken_citations() -> list[str]:
    broken: list[str] = []
    for path in _markdown_files_to_check():
        for lineno, cited_file, cited_section in _citations_in_file(path):
            message = _broken_citation_message(path, lineno, cited_file, cited_section)
            if message:
                broken.append(message)
    return broken


def _citations_in_file(path: Path) -> list[tuple[int, str, str]]:
    citations: list[tuple[int, str, str]] = []
    for lineno, line in enumerate(_read(path).splitlines(), start=1):
        for cited_file, cited_section in _citation_matches(line):
            citations.append((lineno, cited_file, cited_section))
    return citations


def _broken_citation_message(
    path: Path,
    lineno: int,
    cited_file: str,
    cited_section: str,
) -> str | None:
    if cited_file in IGNORED_CITATION_FILES:
        return None

    target = _resolve_cited_file(cited_file)
    rel = path.relative_to(REPO_ROOT)
    if target is None:
        return f"  {rel}:{lineno}: cited file '{cited_file}' does not exist"

    target_headings = _section_headings(_read(target))
    normalised = cited_section.strip("*_` ").lower()
    if _section_matches(normalised, target_headings):
        return None
    return f"  {rel}:{lineno}: cited section '§ {cited_section}' not found in {cited_file}"


def test_citation_count_does_not_regress() -> None:
    """Total broken `file.md § Section` citations stays at or below CITATION_BUDGET.

    This is a ratcheting test: it permits a known number of pre-existing broken
    citations but fails the build if the count grows. Every PR either holds the
    line or improves it. Lower CITATION_BUDGET in this file when you fix some.
    """
    broken = _broken_citations()
    if len(broken) > CITATION_BUDGET:
        new_count = len(broken)
        msg = (
            f"Broken-citation count regressed: {new_count} > budget of {CITATION_BUDGET}.\n"
            f"Either fix the new broken citation(s) below, or — if all of these are\n"
            f"pre-existing — raise CITATION_BUDGET in tests/unit/test_kb_integrity.py.\n"
            f"(Raising the budget should be rare and reviewed; the goal is to ratchet down.)\n\n"
            + "\n".join(broken[:50])
            + (f"\n... and {len(broken) - 50} more" if len(broken) > 50 else "")
        )
        pytest.fail(msg)


def test_citation_budget_is_tight() -> None:
    """The budget is not larger than the actual count — keeps it ratcheting down.

    If the real count drops below the budget (someone fixed citations without
    updating the constant), the test fails with the new tighter number to set.

    Slack of up to 15 is tolerated so a single PR that batch-fixes many
    citations doesn't have to also chase the ratchet in the same change. A
    follow-up PR can then set the budget to the new, smaller actual.
    """
    broken = _broken_citations()
    actual = len(broken)
    slack = CITATION_BUDGET - actual
    assert slack <= 15, (
        f"CITATION_BUDGET ({CITATION_BUDGET}) is loose by {slack}. "
        f"Tighten it: set CITATION_BUDGET = {actual} in tests/unit/test_kb_integrity.py "
        f"so the next regression is caught."
    )


# ---------------------------------------------------------------------------
# Frontmatter completeness for KB files
# ---------------------------------------------------------------------------

REQUIRED_KB_FRONTMATTER = ("id", "tldr", "load_when", "canonical_for", "verified")


def test_every_root_kb_file_referenced_from_index() -> None:
    """Every root-level `knowledge-base/*.md` (excluding INDEX.md and CHEATSHEET.md
    themselves, README.md, and language/workspace subdirs) must be cited from
    `knowledge-base/INDEX.md`.

    INDEX.md is the routing table — agents discover KB files through it. A
    new file landing without an index entry is an orphan: agents will not
    load it from a `load_when:` keyword unless something points at it. The
    contract test catches that drift on push, not on first agent miss.
    """
    index_text = _read(KB_DIR / "INDEX.md")
    skip = {"INDEX.md", "CHEATSHEET.md", "README.md"}
    missing: list[str] = []
    for kb_file in sorted(KB_DIR.glob("*.md")):
        if kb_file.name in skip:
            continue
        if kb_file.name not in index_text:
            missing.append(kb_file.name)
    assert not missing, (
        "Root KB files not cited from knowledge-base/INDEX.md "
        "(every routable KB file must appear in the index):\n  " + "\n  ".join(missing)
    )


@pytest.mark.parametrize(
    "kb_file",
    [p for p in sorted(KB_DIR.rglob("*.md")) if p.name not in {"README.md"}],
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_kb_file_has_required_frontmatter(kb_file: Path) -> None:
    """Every KB file declares the routing fields the loader rule depends on."""
    content = _read(kb_file)
    assert content.startswith("---\n"), (
        f"{kb_file.relative_to(REPO_ROOT)}: missing YAML frontmatter — "
        f"required for the KB loading rule (CLAUDE.md § Knowledge Base)"
    )
    end = content.find("\n---", 4)
    assert end > 0, f"{kb_file.relative_to(REPO_ROOT)}: unterminated frontmatter block"
    frontmatter = content[4:end]
    keys = {line.split(":", 1)[0].strip() for line in frontmatter.splitlines() if ":" in line}
    missing = set(REQUIRED_KB_FRONTMATTER).difference(keys)
    assert not missing, (
        f"{kb_file.relative_to(REPO_ROOT)}: missing required frontmatter keys: {sorted(missing)}"
    )


# ---------------------------------------------------------------------------
# Cross-file duplication guard
#
# The INDEX/frontmatter contract tests keep *routing* in sync; this guard keeps
# *substance* single-homed. Duplicated rule text drifts: the coverage-threshold
# and smoke-signal contradictions fixed in 2026-07 both started as copies of a
# rule that later diverged in one home but not the other.
# ---------------------------------------------------------------------------

# Word-sequence length that counts as duplicated substance. Long enough that
# shared idioms don't trip it; short enough to catch a copied rule sentence.
_NGRAM_WORDS = 12

# Known deliberate parallels: pairs allowed to share n-grams because the text
# is an intentional template echo, not a rule that can drift.
_NGRAM_ALLOWED_PAIRS: set[tuple[str, str]] = {
    # Both files open with the same "Reference implementation" notice by design.
    (
        "knowledge-base/languages/python.md",
        "knowledge-base/languages/testing-python.md",
    ),
    # The three adapter skills share one rigorous schema (operations tables,
    # config precedence, untrusted-input sections) as a deliberate pattern.
    ("skills/host-adapter/SKILL.md", "skills/issue-fetch/SKILL.md"),
    ("skills/host-adapter/SKILL.md", "skills/notifier/SKILL.md"),
    ("skills/issue-fetch/SKILL.md", "skills/notifier/SKILL.md"),
}

# Lines exempt from n-gram extraction: blockquotes carry canonical prompt
# templates that agents must instantiate verbatim (pinned by
# test_approval_gate_contracts), and every agent opens its Tool Policy and
# Tier-aware ceremony sections with the same mandated leader sentence
# (pinned by the agent anatomy contracts) — contractual echoes, not drift.
_NGRAM_EXEMPT_LINE = re.compile(
    r"^\s*>"
    r"|Reply 'approved'"
    r"|tool-policy\.md` § Per-Agent Matrix"
    r"|Master table: `CLAUDE\.md` § Quality Tier"
)


def _guarded_corpus() -> list[Path]:
    """Every always- or per-invocation-loaded prose surface.

    commands/*.md shims are excluded: they are 7-line generated-style
    forwarders whose mutual similarity is the template, not a rule.
    """
    return sorted(
        [
            *KB_DIR.rglob("*.md"),
            *AGENTS_DIR.glob("*.agent.md"),
            *(REPO_ROOT / "skills").glob("*/SKILL.md"),
            REPO_ROOT / "CLAUDE.md",
        ]
    )


def _kb_word_ngrams(path: Path) -> set[str]:
    body = _read(path)
    if body.startswith("---\n"):
        parts = body.split("---", 2)
        body = parts[2] if len(parts) == 3 else body
    lines = [line for line in body.splitlines() if not _NGRAM_EXEMPT_LINE.search(line)]
    words = re.findall(r"[a-z0-9'`._-]+", "\n".join(lines).lower())
    return {" ".join(words[i : i + _NGRAM_WORDS]) for i in range(len(words) - _NGRAM_WORDS + 1)}


def test_kb_files_do_not_duplicate_rule_text() -> None:
    """No two loaded surfaces share a 12-word text run (minus allowlisted parallels).

    Corpus: knowledge-base/, agents/, skills/, and CLAUDE.md — everything an
    agent session pays tokens for. If this fails, keep one canonical statement
    and replace the other side with a `file.md § Section` pointer (loading
    rule: CLAUDE.md § Knowledge Base). Only extend _NGRAM_ALLOWED_PAIRS for
    deliberate template echoes.
    """
    seen: dict[str, Path] = {}
    offenders: dict[tuple[str, str], str] = {}
    for path in _guarded_corpus():
        rel = str(path.relative_to(REPO_ROOT))
        for gram in _kb_word_ngrams(path):
            other = seen.setdefault(gram, path)
            if other is not path:
                pair_key = tuple(sorted((str(other.relative_to(REPO_ROOT)), rel)))
                if pair_key not in _NGRAM_ALLOWED_PAIRS:
                    offenders.setdefault((pair_key[0], pair_key[1]), gram)
    assert not offenders, (
        "KB files share duplicated rule text (12+ identical words). "
        "Single-home the rule and cite it from the other file:\n"
        + "\n".join(f'  {a} <-> {b}: "{gram}"' for (a, b), gram in sorted(offenders.items()))
    )


# Only the CHEATSHEET may join the fixed per-session context. Every other KB
# file must be trigger-loaded; an `always` load_when silently grows the
# overhead every adopter pays on every turn (INDEX was demoted in 2026-07).
_ALWAYS_LOADED_KB_FILES = {"knowledge-base/CHEATSHEET.md"}


def test_only_cheatsheet_declares_load_when_always() -> None:
    """No KB file outside the allowlist may declare `load_when: always`."""
    offenders = []
    for path in sorted(KB_DIR.rglob("*.md")):
        rel = str(path.relative_to(REPO_ROOT))
        for line in _read(path).splitlines():
            if line.startswith("load_when:") and "always" in line.split(":", 1)[1]:
                if rel not in _ALWAYS_LOADED_KB_FILES:
                    offenders.append(f"  {rel}: {line.strip()}")
                break
    assert not offenders, (
        "KB files outside the always-loaded allowlist declare `load_when: always` "
        "(this grows the fixed per-session token surface):\n" + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# Agent ↔ command shim consistency
# ---------------------------------------------------------------------------


def test_every_agent_has_a_command_shim() -> None:
    """Each agents/<id>.agent.md has a matching commands/<id>.md slash-command shim."""
    agent_ids: set[str] = set()
    for agent_file in AGENTS_DIR.glob("*.agent.md"):
        content = _read(agent_file)
        m = re.search(r"^id:\s*(\S+)\s*$", content, re.MULTILINE)
        assert m, f"{agent_file.relative_to(REPO_ROOT)}: missing 'id:' frontmatter"
        agent_ids.add(m.group(1))

    command_ids = {p.stem for p in COMMANDS_DIR.glob("*.md")}

    missing_commands = agent_ids - command_ids
    assert not missing_commands, (
        f"Agents without a matching commands/<id>.md shim: {sorted(missing_commands)}.\n"
        f"Each agent must have a slash-command — see CLAUDE.md § Workflow."
    )


# ---------------------------------------------------------------------------
# Internal file references resolve
#
# Catches links like `templates/foo.md` or `skills/bar/SKILL.md` where the
# target was renamed or deleted. Distinct from the citation test above:
# this matches paths even when there is no `§ Section` suffix.
# ---------------------------------------------------------------------------

INTERNAL_PATH_RE = re.compile(
    r"`(templates/[A-Za-z0-9_./-]+\.(?:md|toml(?:\.example)?)|"
    r"skills/[A-Za-z0-9_./-]+|"
    r"agents/[A-Za-z0-9_./-]+\.md|"
    r"docs/[A-Za-z0-9_./-]+\.md|"
    r"knowledge-base/[A-Za-z0-9_./-]+\.md|"
    r"harness/[A-Za-z0-9_./.-]+)`",
)


# Paths inside backticks that are intentional placeholders, not real files.
IGNORED_INTERNAL_PATHS: set[str] = {
    "knowledge-base/languages/<lang>.md",
    "knowledge-base/languages/testing-<lang>.md",
    "knowledge-base/domain-language.md",  # seeded on first use, not in repo
    "knowledge-base/quality-gates.md",  # seeded on first use, not in repo
    "knowledge-base/feature-flag-registry.md",  # seeded on first use, not in repo
    "knowledge-base/INDEX.md",  # exists; tested separately above
    # Forward-references in RFC-0001 — proposed targets that land in
    # follow-up move stories. Removing each entry is part of the
    # accepting move story's slice.
    "knowledge-base/definition-of-done.md",
    # Proposed in RFC-0002 (docs/rfcs/0002-lessons-log.md); the seed file
    # lands with the implementation if accepted. Remove this entry then.
    "knowledge-base/lessons.md",
}

# Path patterns whose `NNNN` / `NNN` / `<scope>` segments are placeholder
# templates ("docs/adr/NNNN-title.md") rather than real files.
IGNORED_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"docs/adr/N{3,4}-"),
    re.compile(r"docs/runbooks/[A-Za-z0-9_.-]+\.md$"),  # adopter-seeded on first use
    re.compile(r"docs/onboarding\.md$"),  # seeded by docs-maintainer on first use
)


def test_internal_path_references_resolve() -> None:
    """Backtick-quoted repo paths refer to files that exist on disk."""
    broken = _broken_internal_path_references()
    assert not broken, (
        f"Found {len(broken)} broken internal path reference(s):\n"
        + "\n".join(broken[:50])
        + (f"\n... and {len(broken) - 50} more" if len(broken) > 50 else "")
    )


def _broken_internal_path_references() -> list[str]:
    broken: list[str] = []
    for path in _markdown_files_to_check():
        for lineno, ref in _internal_path_refs(path):
            if _internal_ref_is_broken(ref):
                rel = path.relative_to(REPO_ROOT)
                broken.append(f"  {rel}:{lineno}: '{ref}' does not exist on disk")
    return broken


def _internal_path_refs(path: Path) -> list[tuple[int, str]]:
    refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(_read(path).splitlines(), start=1):
        refs.extend((lineno, match.group(1)) for match in INTERNAL_PATH_RE.finditer(line))
    return refs


def _internal_ref_is_broken(ref: str) -> bool:
    ref_path = ref.rstrip("/")
    if _ignored_internal_ref(ref_path):
        return False
    return not (REPO_ROOT / ref_path).exists()


def _ignored_internal_ref(ref_path: str) -> bool:
    return (
        ref_path in IGNORED_INTERNAL_PATHS
        or any(pattern.search(ref_path) for pattern in IGNORED_PATH_PATTERNS)
        or "<" in ref_path
    )


def test_index_by_file_column_matches_frontmatter_load_when() -> None:
    """INDEX § By File "Load when" cells are single-sourced from frontmatter.

    The By File table previously hand-duplicated each KB file's
    `load_when:` frontmatter and the copies drifted silently. The cell is now
    the frontmatter value verbatim — edit the file's frontmatter, then copy
    it into the row. Rows for files without KB frontmatter (CLAUDE.md,
    README.md) are exempt.
    """
    index_text = _read(KB_DIR / "INDEX.md")
    start = index_text.find("## By File")
    stop = index_text.find("\n## ", start + 1)
    section = index_text[start:stop]
    row_re = re.compile(r"^\| `([^`]+)` \| \w[\w-]* \| (.+?) \|$", re.MULTILINE)

    failures: list[str] = []
    for name, cell in row_re.findall(section):
        path = KB_DIR / name
        if not path.is_file() or path.name == "README.md":
            continue
        content = _read(path)
        if not content.startswith("---\n"):
            continue
        end = content.find("\n---", 4)
        load_when = next(
            (
                line.split(":", 1)[1].strip()
                for line in content[4:end].splitlines()
                if line.startswith("load_when:")
            ),
            None,
        )
        if load_when is not None and cell != load_when:
            failures.append(f"{name}:\n    INDEX cell:  {cell}\n    frontmatter: {load_when}")

    assert not failures, (
        "INDEX § By File drifted from frontmatter load_when — frontmatter is "
        "the single source; update the row to match:\n  " + "\n  ".join(failures)
    )
