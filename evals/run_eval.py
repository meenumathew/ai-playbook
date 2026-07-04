"""Eval harness for ai-playbook agents — structural + LLM-as-judge.

Two validation modes:

1. **Structural (keyword presence):** fast, no API calls. Substring-matches
   keywords from each rubric item against the agent's output, with a guard
   against output that only repeats rubric keywords.
   This is a *pre-check*, not a semantic score: obvious rubric echoes fail,
   but only the LLM judge evaluates reasoning quality. Use structural checks
   to catch obvious gaps in CI; do not treat a passing structural run as
   evidence the agent reasoned correctly.

2. **LLM-as-judge:** uses Claude to semantically evaluate whether agent output
   satisfies each rubric criterion. Catches nuanced behavioural compliance.
   Requires ANTHROPIC_API_KEY environment variable.

Usage:
    # Structural validation (keyword matching — fast, no API key needed):
    python evals/run_eval.py validate <agent-name> <output-file>

    # LLM-as-judge validation (semantic — requires ANTHROPIC_API_KEY):
    python evals/run_eval.py judge <agent-name> <output-file>

    # Parse and display the rubric for an agent:
    python evals/run_eval.py rubric <agent-name>

    # Run all structural checks (no agent output needed):
    python evals/run_eval.py check-structure

    # Calibrate the structural validator with generated pass/fail cases:
    python evals/run_eval.py calibrate

    # Validate committed sample baselines with structural checks:
    python evals/run_eval.py validate-samples
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

EVALS_DIR = Path(__file__).parent
RUBRICS_DIR = EVALS_DIR / "rubrics"
SAMPLES_DIR = EVALS_DIR / "samples"
ADVERSARIAL_SAMPLES_DIR = SAMPLES_DIR / "adversarial"
NEGATIVE_SAMPLES_DIR = SAMPLES_DIR / "negative"
REPO_ROOT = EVALS_DIR.parent

sys.path.insert(0, str(REPO_ROOT / "src"))
from deploy_ai_playbook.discovery import standard_agent_names  # noqa: E402

AGENTS = standard_agent_names()

# Adversarial eval pairs — test agent resilience to malformed/hostile input
ADVERSARIAL_EVALS = [
    "story-refiner-adversarial",
    "xp-pair-programmer-adversarial",
    "slice-planner-adversarial",
    "docs-maintainer-adversarial",
    "diff-reviewer-adversarial",
    "code-inspector-adversarial",
    "release-captain-adversarial",
    "incident-responder-adversarial",
]


@dataclass
class RubricItem:
    """A single rubric item extracted from a rubric source."""

    text: str
    keywords: list[str] = field(default_factory=list)
    item_id: str | None = None
    evidence: str | None = None

    def check(self, output: str) -> bool:
        """Substring-check whether the rubric item's keywords appear in `output`.

        This is a presence check, not a semantic evaluation. `validate()` adds
        a narrow rubric-echo guard; use `judge_with_llm` for actual scoring.
        """
        output_lower = output.lower()
        if not self.keywords:
            # No explicit keywords on this rubric item — fall back to
            # distinctive words (>6 chars) from the rubric text itself.
            # Require at least half of them to appear; this avoids common
            # English words from matching almost any document.
            words = [w for w in self.text.lower().split() if len(w) > 6]
            if not words:
                return False
            matches = sum(1 for w in words if w in output_lower)
            return matches >= max(2, len(words) // 2)
        # Require at least half of explicit keywords. Schema rubrics often pair
        # a stable ID/summary phrase with concrete evidence terms; exact heading
        # phrases must not be the only way a representative answer passes.
        matches = sum(1 for kw in self.keywords if _keyword_matches_output(output_lower, kw))
        return matches >= max(1, len(self.keywords) // 2)

    def violates(self, output: str) -> bool:
        """Return True when a must-not item appears as an unnegated behavior.

        Structural must-not checks are intentionally cheap, but they should not
        punish outputs that explicitly refuse an anti-pattern, such as "do not
        use `gh pr create`". This keeps the pre-check useful without pretending
        to be a semantic judge.
        """
        output_lower = output.lower()
        unnegated_matches = sum(
            1 for keyword in self.keywords if _keyword_occurs_unnegated(output_lower, keyword)
        )
        return unnegated_matches >= max(1, len(self.keywords) * 0.6)


NEGATION_MARKERS = (
    "avoid",
    "avoids",
    "cannot",
    "can't",
    "do not",
    "does not",
    "don't",
    "must not",
    "never",
    "no",
    "not",
    "refuse",
    "refuses",
    "without",
    "won't",
)


def _keyword_occurs_unnegated(output_lower: str, keyword: str) -> bool:
    keyword_lower = keyword.lower()
    start = 0
    while True:
        index = output_lower.find(keyword_lower, start)
        if index == -1:
            return False
        context = output_lower[max(0, index - 160) : index]
        if not _has_negation_marker(context):
            return True
        start = index + len(keyword_lower)


def _has_negation_marker(context: str) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", context) for marker in NEGATION_MARKERS)


@dataclass
class Rubric:
    """Parsed eval rubric for one agent."""

    agent: str
    must_demonstrate: list[RubricItem] = field(default_factory=list)
    must_not: list[RubricItem] = field(default_factory=list)
    quality_signals: list[RubricItem] = field(default_factory=list)


DEFAULT_EVIDENCE_BY_SECTION = {
    "must_demonstrate": (
        "Judge must cite exact output evidence that satisfies this required behavior."
    ),
    "must_not": (
        "Judge must cite the output phrase that violates this prohibition, "
        "or state that none appears."
    ),
    "quality_signals": (
        "Judge must cite exact output evidence for this quality signal, or state why it is absent."
    ),
}


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from a rubric item text.

    Pulls out backtick-quoted terms, bold terms, and significant phrases.
    """
    keywords: list[str] = []

    # Backtick-quoted code/terms
    keywords.extend(re.findall(r"`([^`]+)`", text))

    # Bold terms
    for match in re.findall(r"\*\*([^*]+)\*\*", text):
        cleaned = match.strip(":")
        if len(cleaned) > 2:
            keywords.append(cleaned)

    # If no structured keywords found, use key noun phrases
    if not keywords:
        # Remove markdown formatting
        clean = re.sub(r"[*`#\[\]]", "", text)
        # Extract multi-word phrases that look meaningful
        words = clean.split()
        if len(words) >= 3:
            keywords.append(" ".join(words[:3]))

    return keywords


def parse_rubric(agent: str) -> Rubric:
    """Parse an eval rubric.

    Prefer schema-backed rubrics from `evals/rubrics/<agent>.json`; fall back
    to legacy markdown rubrics for custom or older evals.
    """
    schema_path = RUBRICS_DIR / f"{agent}.json"
    if schema_path.exists():
        return _parse_schema_rubric(agent, schema_path)

    return _parse_markdown_rubric(agent)


def _parse_markdown_rubric(agent: str) -> Rubric:
    """Parse a legacy markdown eval expected file into a structured rubric."""
    expected_path = EVALS_DIR / f"{agent}-expected.md"
    if not expected_path.exists():
        raise FileNotFoundError(f"No expected file for {agent}: {expected_path}")

    content = expected_path.read_text()
    rubric = Rubric(agent=agent)

    current_items: list[RubricItem] | None = None

    for line in content.splitlines():
        line = line.strip()

        # Detect section headers.
        #
        # Rubrics use severity buckets: Must Fix > Should Fix > Suggestions.
        # The harness collapses them into three categories:
        #   - must_demonstrate: blocker items (Must demonstrate / Must identify / Must Fix)
        #   - must_not:         anti-patterns (Must NOT)
        #   - quality_signals:  non-blocker items (Quality signals / Should Fix / Suggestions)
        #
        # Trailing parenthetical qualifiers like "## Should Fix (continued)" are
        # matched by `re.match` because it anchors to the start, not the end —
        # so a section can be split across multiple headings without dropping items.
        if re.match(r"## Must (demonstrate|identify|Fix)", line):
            current_items = rubric.must_demonstrate
            continue
        if re.match(r"## Must NOT", line):
            current_items = rubric.must_not
            continue
        if re.match(r"## (Quality signals|Should (Fix|consider|do)|Suggestions)", line):
            current_items = rubric.quality_signals
            continue
        if line.startswith("## "):
            current_items = None
            continue

        # Parse list items in current section
        if current_items is not None and re.match(r"^[-\d]+[.)]?\s", line):
            text = re.sub(r"^[-\d]+[.)]?\s*", "", line)
            if text:
                keywords = extract_keywords(text)
                current_items.append(RubricItem(text=text, keywords=keywords))

    return rubric


def _parse_schema_rubric(agent: str, schema_path: Path) -> Rubric:
    """Parse a schema-backed rubric.

    The schema is deliberately JSON, not YAML, so the eval harness stays free
    of parser dependencies and works in the regular CI environment.
    """
    try:
        raw_data = json.loads(schema_path.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"Malformed rubric schema {schema_path}: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError(f"Rubric schema {schema_path} must be a JSON object")

    declared_agent = _required_schema_string(raw_data, "agent", schema_path)
    if declared_agent != agent:
        raise ValueError(
            f"Rubric schema {schema_path} declares agent {declared_agent!r}, expected {agent!r}"
        )

    version = raw_data.get("version")
    if version != 1:
        raise ValueError(f"Rubric schema {schema_path} must declare version 1")

    rubric = Rubric(
        agent=agent,
        must_demonstrate=_schema_items(raw_data, "must_demonstrate", schema_path),
        must_not=_schema_items(raw_data, "must_not", schema_path),
        quality_signals=_schema_items(raw_data, "quality_signals", schema_path),
    )
    # Cross-section ID uniqueness — protects judge prompts from ambiguous IDs.
    # Per-section uniqueness is already enforced inside `_schema_items`.
    seen: dict[str, str] = {}
    for section_name, section_items in (
        ("must_demonstrate", rubric.must_demonstrate),
        ("must_not", rubric.must_not),
        ("quality_signals", rubric.quality_signals),
    ):
        for item in section_items:
            if item.item_id is None:
                continue
            previous_section = seen.get(item.item_id)
            if previous_section is not None:
                raise ValueError(
                    f"Rubric schema {schema_path} reuses id {item.item_id!r} in "
                    f"{previous_section!r} and {section_name!r}; ids must be unique across sections"
                )
            seen[item.item_id] = section_name
    return rubric


def _required_schema_string(data: dict, field_name: str, schema_path: Path) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Rubric schema {schema_path} must include string `{field_name}`")
    return value


def _schema_items(data: dict, section: str, schema_path: Path) -> list[RubricItem]:
    raw_items = data.get(section)
    if not isinstance(raw_items, list):
        raise ValueError(f"Rubric schema {schema_path} must include list `{section}`")

    items: list[RubricItem] = []
    seen_ids: set[str] = set()
    for index, raw_item in enumerate(raw_items):
        if not isinstance(raw_item, dict):
            raise ValueError(f"Rubric schema {schema_path} `{section}[{index}]` must be an object")
        item_id = _required_schema_string(raw_item, "id", schema_path)
        if item_id in seen_ids:
            raise ValueError(f"Rubric schema {schema_path} has duplicate id {item_id!r}")
        seen_ids.add(item_id)

        criterion = _required_schema_string(raw_item, "criterion", schema_path)
        evidence = raw_item.get("evidence")
        if evidence is None:
            evidence = DEFAULT_EVIDENCE_BY_SECTION[section]
        elif not isinstance(evidence, str) or not evidence.strip():
            raise ValueError(f"Rubric schema {schema_path} `{item_id}.evidence` must be a string")
        keywords = _schema_keywords(raw_item, criterion, schema_path, item_id)
        items.append(
            RubricItem(
                text=criterion,
                keywords=keywords,
                item_id=item_id,
                evidence=evidence,
            )
        )
    return items


def _schema_keywords(
    raw_item: dict,
    criterion: str,
    schema_path: Path,
    item_id: str,
) -> list[str]:
    raw_keywords = raw_item.get("keywords", [])
    if not isinstance(raw_keywords, list):
        raise ValueError(f"Rubric schema {schema_path} `{item_id}.keywords` must be a list")
    keywords: list[str] = []
    for keyword in raw_keywords:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ValueError(
                f"Rubric schema {schema_path} `{item_id}.keywords` must contain strings"
            )
        keywords.append(keyword)
    return keywords or extract_keywords(criterion)


def _rubric_prompt_text(agent: str) -> str:
    """Return the rubric text given to the semantic judge."""
    schema_path = RUBRICS_DIR / f"{agent}.json"
    if schema_path.exists():
        return _render_rubric_for_prompt(parse_rubric(agent))
    return (EVALS_DIR / f"{agent}-expected.md").read_text()


def _render_rubric_for_prompt(rubric: Rubric) -> str:
    sections = [f"# Eval Expected: {rubric.agent}"]
    sections.append(_render_rubric_section("Must demonstrate", rubric.must_demonstrate))
    sections.append(_render_rubric_section("Must NOT", rubric.must_not))
    sections.append(_render_rubric_section("Quality signals", rubric.quality_signals))
    return "\n\n".join(sections)


def _render_rubric_section(title: str, items: list[RubricItem]) -> str:
    lines = [f"## {title}"]
    for item in items:
        label = f"{item.item_id}: " if item.item_id else ""
        lines.append(f"- {label}{item.text}")
        if item.evidence:
            lines.append(f"  Evidence required: {item.evidence}")
    return "\n".join(lines)


def _item_result_text(item: RubricItem) -> str:
    if item.item_id:
        return f"[{item.item_id}] {item.text}"
    return item.text


def _keyword_matches_output(output_lower: str, keyword: str) -> bool:
    keyword_lower = keyword.lower()
    if keyword_lower in output_lower:
        return True

    tokens = _significant_keyword_tokens(keyword_lower)
    if not tokens:
        return False
    matches = sum(1 for token in tokens if _token_present(output_lower, token))
    return matches >= max(1, len(tokens) * 0.6)


def _significant_keyword_tokens(keyword_lower: str) -> list[str]:
    stop_words = {
        "and",
        "are",
        "before",
        "for",
        "from",
        "has",
        "into",
        "not",
        "the",
        "this",
        "with",
        "without",
    }
    tokens = re.findall(r"[a-z0-9_]+(?:\.[a-z0-9_]+)*", keyword_lower)
    return [token for token in tokens if len(token) > 2 and token not in stop_words]


def _token_present(output_lower: str, token: str) -> bool:
    if token in output_lower:
        return True
    if token.endswith("s") and len(token) > 3:
        singular = token[:-1]
        return bool(re.search(rf"\b{re.escape(singular)}\b", output_lower))
    return bool(re.search(rf"\b{re.escape(token)}s?\b", output_lower))


@dataclass
class ValidationResult:
    """Result of validating agent output against a rubric."""

    agent: str
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    quality_hits: list[str] = field(default_factory=list)
    quality_misses: list[str] = field(default_factory=list)
    rubric_echoes: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Keyword-presence rate as a percentage of must-demonstrate items.

        Not a quality score. See module docstring — echo output may still have
        a high keyword score while `ok` is false. Use `judge_with_llm` for
        semantic evaluation.
        """
        total = len(self.passed) + len(self.failed)
        if total == 0:
            return 0.0
        return len(self.passed) / total * 100

    @property
    def ok(self) -> bool:
        """True if no critical failures and no violations."""
        return len(self.failed) == 0 and len(self.violations) == 0 and len(self.rubric_echoes) == 0


def _split_front_matter(text: str) -> tuple[dict[str, str], str]:
    """Split an optional leading ``---`` front-matter block from a sample.

    Dependency-free (no PyYAML, matching the JSON-rubric choice): parses simple
    ``key: value`` lines only. Returns ``({}, text)`` when no block is present,
    so samples without front-matter are unaffected.
    """
    if not text.startswith("---"):
        return {}, text
    lines = text.splitlines(keepends=True)
    closing = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
    if closing is None:
        return {}, text
    meta: dict[str, str] = {}
    for raw in lines[1:closing]:
        if ":" in raw:
            key, _, value = raw.partition(":")
            meta[key.strip().lower()] = value.strip()
    body = "".join(lines[closing + 1 :]).lstrip("\n")
    return meta, body


def _strip_front_matter(text: str) -> str:
    return _split_front_matter(text)[1]


def validate(agent: str, output: str) -> ValidationResult:
    """Validate agent output against its rubric."""
    rubric = parse_rubric(agent)
    output = _strip_front_matter(output)
    result = ValidationResult(agent=agent)

    # Check must-demonstrate items
    for item in rubric.must_demonstrate:
        if item.check(output):
            result.passed.append(_item_result_text(item))
        else:
            result.failed.append(_item_result_text(item))

    # Check must-not items (these are anti-patterns — finding keywords is BAD)
    for item in rubric.must_not:
        if item.violates(output):
            result.violations.append(_item_result_text(item))

    # Check quality signals
    for item in rubric.quality_signals:
        if item.check(output):
            result.quality_hits.append(_item_result_text(item))
        else:
            result.quality_misses.append(_item_result_text(item))

    if _looks_like_rubric_echo(output, rubric):
        result.rubric_echoes.append(
            "Output repeats rubric keywords/items without independent evidence"
        )

    return result


def _normalize_for_echo_detection(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _looks_like_rubric_echo(output: str, rubric: Rubric) -> bool:
    """Catch shallow outputs that paste rubric keywords/items instead of evidence.

    This is intentionally narrow: structural validation is still a cheap
    pre-check, not a semantic judge. The guard prevents the known failure mode
    where joining required keywords produces a passing score.

    Each section is checked independently so that an output echoing only
    must_not keywords (or only quality_signals keywords) is still caught.
    """
    normalized_output = _normalize_for_echo_detection(output)
    if not normalized_output:
        return False

    for section_items in (rubric.must_demonstrate, rubric.must_not, rubric.quality_signals):
        section_keywords = [
            keyword for item in section_items for keyword in item.keywords if keyword
        ]
        keyword_echo = _normalize_for_echo_detection(" ".join(section_keywords))
        if keyword_echo and normalized_output == keyword_echo:
            return True

    all_items = rubric.must_demonstrate + rubric.must_not + rubric.quality_signals
    echoed_items = [
        item for item in all_items if _normalize_for_echo_detection(item.text) in normalized_output
    ]
    return len(echoed_items) >= max(3, len(all_items) // 2)


def print_rubric(agent: str) -> None:
    """Print the parsed rubric for an agent."""
    rubric = parse_rubric(agent)
    print(f"\n{'=' * 60}")
    print(f"Rubric: {rubric.agent}")
    print(f"{'=' * 60}")

    if rubric.must_demonstrate:
        print(f"\nMust demonstrate ({len(rubric.must_demonstrate)}):")
        for item in rubric.must_demonstrate:
            kw = ", ".join(item.keywords[:5]) if item.keywords else "(no keywords)"
            prefix = f"[{item.item_id}] " if item.item_id else ""
            print(f"  ✓ {prefix}{item.text[:80]}...")
            print(f"    Keywords: {kw}")
            if item.evidence:
                print(f"    Evidence: {item.evidence}")

    if rubric.must_not:
        print(f"\nMust NOT ({len(rubric.must_not)}):")
        for item in rubric.must_not:
            prefix = f"[{item.item_id}] " if item.item_id else ""
            print(f"  ✗ {prefix}{item.text[:80]}")
            if item.evidence:
                print(f"    Evidence: {item.evidence}")

    if rubric.quality_signals:
        print(f"\nQuality signals ({len(rubric.quality_signals)}):")
        for item in rubric.quality_signals:
            prefix = f"[{item.item_id}] " if item.item_id else ""
            print(f"  ◇ {prefix}{item.text[:80]}")
            if item.evidence:
                print(f"    Evidence: {item.evidence}")


def print_validation(result: ValidationResult) -> None:
    """Print validation results."""
    print(f"\n{'=' * 60}")
    print(f"Structural validation: {result.agent}")
    print(f"Keyword presence: {result.score:.0f}% — {'PASS' if result.ok else 'FAIL'}")
    print("(structural check only — run `judge` for semantic evaluation)")
    print(f"{'=' * 60}")

    _print_result_items("✓ Passed", result.passed, "✓")
    _print_result_items("✗ Failed", result.failed, "✗")
    _print_result_items("⚠ Violations", result.violations, "⚠")
    _print_result_items("⚠ Rubric echo", result.rubric_echoes, "⚠")
    _print_result_items("◇ Quality signals present", result.quality_hits, "◇")
    _print_result_items("◇ Quality signals missing", result.quality_misses, "○")


def _print_result_items(title: str, items: list[str], marker: str) -> None:
    if not items:
        return
    print(f"\n{title} ({len(items)}):")
    for text in items:
        print(f"  {marker} {text[:80]}")


def check_structure() -> bool:
    """Verify all eval files exist and parse correctly."""
    print("\nStructural checks:")
    all_ok = True

    # Check standard evals
    for agent in AGENTS:
        input_path = EVALS_DIR / f"{agent}-input.md"
        expected_path = EVALS_DIR / f"{agent}-expected.md"

        if not input_path.exists():
            print(f"  ✗ {agent}: missing input file")
            all_ok = False
            continue
        if not expected_path.exists():
            print(f"  ✗ {agent}: missing expected file")
            all_ok = False
            continue

        try:
            rubric = parse_rubric(agent)
            total = (
                len(rubric.must_demonstrate) + len(rubric.must_not) + len(rubric.quality_signals)
            )
            print(
                f"  ✓ {agent}: {len(rubric.must_demonstrate)} must-do, "
                f"{len(rubric.must_not)} must-not, "
                f"{len(rubric.quality_signals)} quality ({total} total)"
            )
        except Exception as e:
            print(f"  ✗ {agent}: parse error — {e}")
            all_ok = False

    # Check adversarial evals
    for name in ADVERSARIAL_EVALS:
        input_path = EVALS_DIR / f"{name}-input.md"
        expected_path = EVALS_DIR / f"{name}-expected.md"

        if not input_path.exists():
            print(f"  ✗ {name}: missing adversarial input file")
            all_ok = False
            continue
        if not expected_path.exists():
            print(f"  ✗ {name}: missing adversarial expected file")
            all_ok = False
            continue

        try:
            rubric = parse_rubric(name)
            total = (
                len(rubric.must_demonstrate) + len(rubric.must_not) + len(rubric.quality_signals)
            )
            print(
                f"  ✓ {name} (adversarial): {len(rubric.must_demonstrate)} must-do, "
                f"{len(rubric.must_not)} must-not, "
                f"{len(rubric.quality_signals)} quality ({total} total)"
            )
        except Exception as e:
            print(f"  ✗ {name}: parse error — {e}")
            all_ok = False

    return all_ok


def calibrate() -> bool:
    """Verify the structural validator can pass good cases and fail bad cases.

    This is calibration for the cheap structural pre-check, not proof of agent
    reasoning quality. The cases are synthesised from each rubric's own keywords
    (good = keywords embedded as independent evidence; bad = a raw keyword echo),
    so a green run proves the validator's two code paths work — not that any real
    agent output is good. The LLM judge remains the semantic quality gate.
    """
    print("\nStructural calibration:")
    all_ok = True
    for agent in _all_eval_names():
        try:
            good_result, bad_result = _run_calibration_pair(agent)
        except Exception as exc:
            print(f"  ✗ {agent}: calibration error — {exc}")
            all_ok = False
            continue

        good_ok = good_result.ok
        bad_failed = not bad_result.ok
        if good_ok and bad_failed:
            print(
                f"  ✓ {agent}: good case passed ({good_result.score:.0f}%), "
                f"bad case failed ({bad_result.score:.0f}%)"
            )
            continue

        all_ok = False
        print(
            f"  ✗ {agent}: expected good=pass/bad=fail, got "
            f"good={'pass' if good_ok else 'fail'} ({good_result.score:.0f}%), "
            f"bad={'pass' if bad_result.ok else 'fail'} ({bad_result.score:.0f}%)"
        )
    return all_ok


def validate_samples() -> bool:
    """Validate committed eval sample baselines with the structural pre-check."""
    print("\nCommitted sample validation:")
    all_ok = True
    expected_agents = set(AGENTS)
    sample_paths = sorted(path for path in SAMPLES_DIR.glob("*.md") if path.name != "README.md")
    found_agents = {path.stem for path in sample_paths}

    for agent in AGENTS:
        if agent not in found_agents:
            print(f"  ✗ {agent}: missing sample evals/samples/{agent}.md")
            all_ok = False

    for agent in sorted(found_agents - expected_agents):
        print(f"  ✗ {agent}: sample has no matching standard agent")
        all_ok = False

    for agent in AGENTS:
        if agent not in found_agents:
            continue
        sample_path = SAMPLES_DIR / f"{agent}.md"
        meta, _body = _split_front_matter(sample_path.read_text())
        provenance = meta.get("provenance")
        result = validate(agent, sample_path.read_text())
        if result.ok:
            label = provenance or "unmarked"
            print(
                f"  ✓ {agent}: sample passes structural validation ({result.score:.0f}%) [{label}]"
            )
            # Provenance is honesty metadata, not a gate. A `curated` or unmarked
            # baseline is a hand-written placeholder, not captured agent output —
            # so a green structural run on it proves rubric/baseline agreement,
            # not that the live agent behaves this way. Warn, do not fail.
            if provenance != "captured":
                print(
                    f"      note: baseline is {label} — not captured agent output; "
                    "see samples/README.md § Scope before trusting it as behaviour evidence"
                )
            continue

        all_ok = False
        print(f"  ✗ {agent}: sample fails structural validation ({result.score:.0f}%)")
        _print_sample_failures(result)

    adversarial_ok = _validate_adversarial_samples()
    negative_ok = _validate_negative_samples()
    return all_ok and adversarial_ok and negative_ok


def _validate_adversarial_samples() -> bool:
    """Adversarial baselines are positive examples of hostile-input handling.

    They live under `samples/adversarial/<name>.md`, must map to an
    adversarial eval pair, and must pass the structural pre-check like any
    other baseline. The LLM judge scores whatever exists here.
    """
    ok = True
    for path in sorted(ADVERSARIAL_SAMPLES_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        name = path.stem
        if name not in ADVERSARIAL_EVALS:
            print(f"  ✗ {name}: adversarial sample has no matching adversarial eval pair")
            ok = False
            continue
        result = validate(name, path.read_text())
        if result.ok:
            print(
                f"  ✓ {name}: adversarial sample passes structural validation ({result.score:.0f}%)"
            )
        else:
            ok = False
            print(f"  ✗ {name}: adversarial sample fails structural validation")
            _print_sample_failures(result)
    return ok


def _validate_negative_samples() -> bool:
    """Negative controls are deliberately-flawed outputs the judge must FAIL.

    Structural validation is NOT a gate here — the controls are semantically
    bad, not necessarily keyword-poor. This check only catches orphans: a
    control whose stem matches no rubric would crash the eval-drift loop.
    The LLM judge asserts these files FAIL; a pass there means judge
    leniency drift or rubric erosion.
    """
    ok = True
    for path in sorted(NEGATIVE_SAMPLES_DIR.glob("*.md")):
        if path.name == "README.md":
            continue
        name = path.stem
        if name not in AGENTS and name not in ADVERSARIAL_EVALS:
            print(f"  ✗ {name}: negative control has no matching rubric")
            ok = False
            continue
        print(f"  ✓ {name}: negative control present (the LLM judge must FAIL it)")
    return ok


def _print_sample_failures(result: ValidationResult) -> None:
    for label, values in (
        ("failed", result.failed),
        ("violations", result.violations),
        ("rubric echoes", result.rubric_echoes),
    ):
        if not values:
            continue
        joined = "; ".join(value[:120] for value in values)
        print(f"    {label}: {joined}")


def _all_eval_names() -> list[str]:
    return [*AGENTS, *ADVERSARIAL_EVALS]


def _run_calibration_pair(agent: str) -> tuple[ValidationResult, ValidationResult]:
    rubric = parse_rubric(agent)
    good_output = _calibration_good_output(agent, rubric)
    bad_output = _calibration_bad_output(rubric)
    return validate(agent, good_output), validate(agent, bad_output)


def _calibration_good_output(agent: str, rubric: Rubric) -> str:
    must_not_keywords = _must_not_keywords(rubric)
    lines = [
        f"# Structural Calibration Good Case: {agent}",
        "This fixture gives independent evidence for each required behavior.",
    ]
    for index, item in enumerate(rubric.must_demonstrate, start=1):
        keyword_text = "; ".join(
            _calibration_keyword_phrase(keyword, must_not_keywords) for keyword in item.keywords
        )
        lines.append(
            f"- Required behavior {index}: concrete scenario evidence includes {keyword_text}."
        )
    return "\n".join(lines)


def _must_not_keywords(rubric: Rubric) -> set[str]:
    values: set[str] = set()
    for item in rubric.must_not:
        values.add(item.text.lower())
        values.update(keyword.lower() for keyword in item.keywords)
    return values


def _calibration_keyword_phrase(keyword: str, must_not_keywords: set[str]) -> str:
    keyword_lower = keyword.lower()
    if any(
        keyword_lower in must_not_keyword or must_not_keyword in keyword_lower
        for must_not_keyword in must_not_keywords
    ):
        return f"refuses {keyword}"
    return keyword


def _calibration_bad_output(rubric: Rubric) -> str:
    """Return the known-bad rubric-echo case for a rubric.

    The output intentionally contains only the required keywords, which should
    produce high keyword presence but fail the echo guard.
    """
    must_keywords = [
        keyword for item in rubric.must_demonstrate for keyword in item.keywords if keyword
    ]
    return " ".join(must_keywords)


def judge_with_llm(agent: str, output: str) -> ValidationResult:
    """Validate agent output using Claude as a semantic judge.

    Requires ANTHROPIC_API_KEY environment variable.
    """
    try:
        import anthropic
    except ImportError:
        print("Error: 'anthropic' package required for judge mode.")
        print("Install: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    rubric = parse_rubric(agent)
    output = _strip_front_matter(output)
    expected_content = _render_rubric_for_prompt(rubric)

    prompt = f"""You are evaluating an AI agent's output against a rubric.

## Agent: {agent}

## Rubric (expected behavior):
{expected_content}

## Actual agent output:
{output}

## Your task:
For each criterion in "Must demonstrate", "Must NOT", and "Quality signals",
evaluate whether the agent output satisfies it. Every criterion has a stable
ID. Call the `record_judgement` tool exactly once with one judgement per
rubric ID, preserving the IDs exactly.

Be strict but fair. Judge semantic compliance, not literal keyword presence.
If the agent adapted the rubric criteria to the actual codebase (different file
names), that counts as passing if the intent is met."""

    # Tool-use forces structured output — Claude must populate this schema or
    # the API rejects the call. Replaces fragile regex JSON extraction.
    judgement_tool = {
        "name": "record_judgement",
        "description": "Record the evaluation of agent output against the rubric.",
        "input_schema": {
            "type": "object",
            "properties": {
                "must_demonstrate": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "criterion": {"type": "string"},
                            "pass": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["id", "criterion", "pass", "reason"],
                    },
                },
                "must_not": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "criterion": {"type": "string"},
                            "violated": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["id", "criterion", "violated", "reason"],
                    },
                },
                "quality_signals": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "criterion": {"type": "string"},
                            "present": {"type": "boolean"},
                            "reason": {"type": "string"},
                        },
                        "required": ["id", "criterion", "present", "reason"],
                    },
                },
            },
            "required": ["must_demonstrate", "must_not", "quality_signals"],
        },
    }

    client = anthropic.Anthropic(api_key=api_key)
    # temperature=0 — deterministic scoring; same input must produce same verdict.
    # Without this, the same rubric/output pair flickers between pass/fail across runs
    # because of judge sampling.
    #
    # The judge model is pinned to the most specific stable id Anthropic
    # publishes for it. Sonnet 4.6 ships as the alias `claude-sonnet-4-6` only —
    # it has no date-suffixed release id — so the alias IS the most specific
    # stable identifier available and is what we pin. (The date 20250514 belongs
    # to Sonnet 4.0, not 4.6; the previous `claude-sonnet-4-6-20250514` default
    # did not exist and returned 404.) Models that do carry a dated id — e.g.
    # Sonnet 4.5, `claude-sonnet-4-5-20250929` — should pin the dated form.
    # A version-pinned id keeps the eval-drift run honest: a verdict
    # change is signal (the agent regressed), not noise from a judge rotating.
    #
    # Override via EVAL_JUDGE_MODEL when intentionally rotating to a newer
    # judge; rotation cadence and acceptance criteria are documented in
    # `evals/rubrics/README.md` § Updating the Judge Model.
    response = client.messages.create(
        model=os.environ.get("EVAL_JUDGE_MODEL", "claude-sonnet-4-6"),
        max_tokens=4096,
        temperature=0,
        tools=[judgement_tool],
        tool_choice={"type": "tool", "name": "record_judgement"},
        messages=[{"role": "user", "content": prompt}],
    )

    # With forced tool use, the response always contains exactly one tool_use block.
    tool_use = next(
        (block for block in response.content if getattr(block, "type", None) == "tool_use"),
        None,
    )
    if tool_use is None:
        print(
            "Error: Judge did not call the record_judgement tool.\n"
            f"Stop reason: {response.stop_reason}"
        )
        sys.exit(1)
    try:
        judgement = _validate_judgement_payload(tool_use.input, rubric)
    except ValueError as exc:
        print(f"Error: Judge returned invalid record_judgement payload: {exc}")
        sys.exit(1)

    result = ValidationResult(agent=agent)

    for item in judgement["must_demonstrate"]:
        text = _judgement_result_text(item)
        if item["pass"]:
            result.passed.append(text)
        else:
            result.failed.append(text)

    for item in judgement["must_not"]:
        text = _judgement_result_text(item)
        if item["violated"]:
            result.violations.append(text)

    for item in judgement["quality_signals"]:
        text = _judgement_result_text(item)
        if item["present"]:
            result.quality_hits.append(text)
        else:
            result.quality_misses.append(text)

    return result


def _judgement_result_text(item: dict) -> str:
    return f"[{item['id']}] {item['criterion']} — {item['reason']}"


def _validate_judgement_payload(payload: object, rubric: Rubric | None = None) -> dict:
    """Validate the judge tool payload before trusting it as a verdict."""
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    expected_ids = _expected_judgement_ids(rubric) if rubric is not None else {}

    _validate_judgement_section(
        payload,
        section="must_demonstrate",
        bool_field="pass",
        label="must-demonstrate",
        expected_ids=expected_ids.get("must_demonstrate"),
    )
    _validate_judgement_section(
        payload,
        section="must_not",
        bool_field="violated",
        label="must-not",
        expected_ids=expected_ids.get("must_not"),
    )
    _validate_judgement_section(
        payload,
        section="quality_signals",
        bool_field="present",
        label="quality-signal",
        expected_ids=expected_ids.get("quality_signals"),
    )
    return payload


def _expected_judgement_ids(rubric: Rubric) -> dict[str, list[str]]:
    return {
        "must_demonstrate": _section_item_ids(rubric.must_demonstrate, "must_demonstrate"),
        "must_not": _section_item_ids(rubric.must_not, "must_not"),
        "quality_signals": _section_item_ids(rubric.quality_signals, "quality_signals"),
    }


def _section_item_ids(items: list[RubricItem], section: str) -> list[str]:
    item_ids: list[str] = []
    for index, item in enumerate(items):
        if not item.item_id:
            raise ValueError(f"rubric `{section}[{index}]` is missing a stable id")
        item_ids.append(item.item_id)
    return item_ids


def _validate_judgement_section(
    payload: dict,
    section: str,
    bool_field: str,
    label: str,
    expected_ids: list[str] | None = None,
) -> None:
    if section not in payload:
        raise ValueError(f"missing required section `{section}`")
    items = payload[section]
    if not isinstance(items, list):
        raise ValueError(f"`{section}` must be a list")
    seen_ids: set[str] = set()
    expected_id_set = set(expected_ids or [])
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{label} item {index} must be an object")
        if expected_ids is not None:
            item_id = _require_string_field(item, section, index, "id")
            if item_id in seen_ids:
                raise ValueError(f"`{section}` contains duplicate id `{item_id}`")
            if item_id not in expected_id_set:
                raise ValueError(f"`{section}` contains unknown id `{item_id}`")
            seen_ids.add(item_id)
        _require_string_field(item, section, index, "criterion")
        _require_string_field(item, section, index, "reason")
        if not isinstance(item.get(bool_field), bool):
            raise ValueError(f"`{section}[{index}].{bool_field}` must be bool")
    if expected_ids is not None:
        missing_ids = [item_id for item_id in expected_ids if item_id not in seen_ids]
        if missing_ids:
            raise ValueError(f"`{section}` missing judgements for ids: {', '.join(missing_ids)}")


def _require_string_field(item: dict, section: str, index: int, field_name: str) -> str:
    value = item.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{section}[{index}].{field_name}` must be string")
    return value


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(1)

    command, command_args = args[0], args[1:]
    handlers: dict[str, Callable[[list[str]], int]] = {
        "calibrate": _handle_calibrate,
        "check-structure": _handle_check_structure,
        "validate-samples": _handle_validate_samples,
        "list-agents": _handle_list_agents,
        "rubric": _handle_rubric,
        "validate": _handle_validate,
        "judge": _handle_judge,
    }
    handler = handlers.get(command)
    if handler is None:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)
    sys.exit(handler(command_args))


def _handle_check_structure(_args: list[str]) -> int:
    return 0 if check_structure() else 1


def _handle_calibrate(_args: list[str]) -> int:
    return 0 if calibrate() else 1


def _handle_validate_samples(_args: list[str]) -> int:
    return 0 if validate_samples() else 1


def _handle_list_agents(_args: list[str]) -> int:
    for agent in AGENTS:
        print(agent)
    return 0


def _handle_rubric(args: list[str]) -> int:
    if len(args) < 1:
        print("Usage: run_eval.py rubric <agent-name>")
        return 1
    print_rubric(args[0])
    return 0


def _handle_validate(args: list[str]) -> int:
    agent, output = _read_agent_output(
        args, "Usage: run_eval.py validate <agent-name> <output-file>"
    )
    if agent is None or output is None:
        return 1
    result = validate(agent, output)
    print_validation(result)
    return 0 if result.ok else 1


def _handle_judge(args: list[str]) -> int:
    usage = "Usage: run_eval.py judge <agent-name> <output-file>"
    agent, output = _read_agent_output(
        args, usage, extra_help="Requires ANTHROPIC_API_KEY environment variable."
    )
    if agent is None or output is None:
        return 1
    result = judge_with_llm(agent, output)
    print_validation(result)
    return 0 if result.ok else 1


def _read_agent_output(
    args: list[str],
    usage: str,
    extra_help: str | None = None,
) -> tuple[str | None, str | None]:
    if len(args) < 2:
        print(usage)
        if extra_help:
            print(extra_help)
        return None, None
    output_path = Path(args[1])
    if not output_path.exists():
        print(f"Output file not found: {output_path}")
        return None, None
    return args[0], output_path.read_text()


if __name__ == "__main__":
    main()
