"""Unit tests for materializing model tiers into deployed agent frontmatter."""

import tomllib

from deploy_ai_playbook.config import ModelTierConfig
from deploy_ai_playbook.services.deploy import (
    _slug,
    claude_model_tier_mapping,
    codex_agent_toml,
    materialize_model_tier,
)

AGENT_CONTENT = """---
name: Sample Agent
model: advisor
id: sample-agent
---

# Sample Agent

Frontmatter declares `model: advisor` or `model: executor`; prose stays.
model: advisor
"""


class TestMaterializeModelTier:
    def test_materialize_rewrites_advisor_line_in_frontmatter(self) -> None:
        result = materialize_model_tier(AGENT_CONTENT, {"advisor": "opus"})

        assert "\nmodel: opus\n" in result
        assert result.startswith("---\nname: Sample Agent\nmodel: opus\nid: sample-agent\n---\n")

    def test_materialize_rewrites_executor_line_in_frontmatter(self) -> None:
        content = AGENT_CONTENT.replace("model: advisor", "model: executor", 1)

        result = materialize_model_tier(content, {"executor": "haiku"})

        assert "model: haiku\nid: sample-agent" in result

    def test_materialize_leaves_prose_mentions_unchanged(self) -> None:
        result = materialize_model_tier(AGENT_CONTENT, {"advisor": "opus"})

        body = result.split("---", 2)[2]
        assert "`model: advisor` or `model: executor`" in body
        assert "\nmodel: advisor\n" in body

    def test_materialize_without_frontmatter_returns_content_unchanged(self) -> None:
        content = "# No frontmatter\n\nmodel: advisor\n"

        assert materialize_model_tier(content, {"advisor": "opus"}) == content

    def test_materialize_with_empty_mapping_returns_content_unchanged(self) -> None:
        assert materialize_model_tier(AGENT_CONTENT, {}) == AGENT_CONTENT

    def test_materialize_with_unmapped_tier_returns_content_unchanged(self) -> None:
        assert materialize_model_tier(AGENT_CONTENT, {"executor": "haiku"}) == AGENT_CONTENT

    def test_materialize_rewrites_before_unterminated_frontmatter_ends(self) -> None:
        content = "---\nmodel: advisor\nname: no closing fence\n"

        result = materialize_model_tier(content, {"advisor": "opus"})

        assert result == "---\nmodel: opus\nname: no closing fence\n"

    def test_materialize_ignores_non_tier_model_values(self) -> None:
        content = AGENT_CONTENT.replace("model: advisor", "model: opus", 1)

        result = materialize_model_tier(content, {"advisor": "sonnet", "executor": "haiku"})

        assert "model: opus\nid: sample-agent" in result


class TestClaudeModelTierMapping:
    def test_mapping_accepts_claude_keywords(self) -> None:
        config = ModelTierConfig(advisor="opus", executor="haiku")

        mapping, skipped = claude_model_tier_mapping(config)

        assert mapping == {"advisor": "opus", "executor": "haiku"}
        assert skipped == {}

    def test_mapping_accepts_full_claude_model_ids(self) -> None:
        config = ModelTierConfig(advisor="claude-opus-4-8", executor="claude-haiku-4-5-20251001")

        mapping, skipped = claude_model_tier_mapping(config)

        assert mapping == {
            "advisor": "claude-opus-4-8",
            "executor": "claude-haiku-4-5-20251001",
        }
        assert skipped == {}

    def test_mapping_accepts_inherit_keyword(self) -> None:
        config = ModelTierConfig(advisor="inherit", executor="sonnet")

        mapping, _skipped = claude_model_tier_mapping(config)

        assert mapping == {"advisor": "inherit", "executor": "sonnet"}

    def test_mapping_skips_non_claude_values(self) -> None:
        config = ModelTierConfig(advisor="opus", executor="ollama:qwen3:32b")

        mapping, skipped = claude_model_tier_mapping(config)

        assert mapping == {"advisor": "opus"}
        assert skipped == {"executor": "ollama:qwen3:32b"}

    def test_mapping_with_no_config_is_empty(self) -> None:
        mapping, skipped = claude_model_tier_mapping(None)

        assert mapping == {}
        assert skipped == {}

    def test_mapping_omits_unset_tiers(self) -> None:
        config = ModelTierConfig(advisor="opus", executor=None)

        mapping, skipped = claude_model_tier_mapping(config)

        assert mapping == {"advisor": "opus"}
        assert skipped == {}


def test_codex_agent_toml_escapes_non_bmp_characters_as_valid_toml() -> None:
    content = "---\nid: x\ndescription: has emoji \U0001f600 here\n---\nbody\n"

    output = codex_agent_toml(content)

    parsed = tomllib.loads(output)
    assert "\U0001f600" in parsed["description"]


def test_codex_agent_toml_keeps_the_whole_document_when_frontmatter_is_unclosed() -> None:
    """An opening fence with no closing fence is not frontmatter: keep the body.

    The split raises ValueError, and the fallback must return the document
    untouched. Treating the unterminated fence as metadata would deploy an
    agent whose instructions had been swallowed.
    """
    content = "---\nid: reviewer\nstill inside the fence\n"

    parsed = tomllib.loads(codex_agent_toml(content))

    assert parsed["name"] == "agent"
    assert parsed["developer_instructions"] == content


def test_codex_agent_toml_ignores_blank_comment_and_valueless_frontmatter_lines() -> None:
    content = "---\n\n# a comment\nid: reviewer\nnot-a-key-value-pair\n---\nbody\n"

    parsed = tomllib.loads(codex_agent_toml(content))

    assert parsed["name"] == "reviewer"
    assert parsed["developer_instructions"] == "Source agent metadata:\nid: reviewer\n\nbody\n"


def test_slug_normalizes_names_to_kebab_case() -> None:
    assert _slug("Django Model Reviewer") == "django-model-reviewer"


def test_slug_collapses_symbol_runs_and_trims_edge_hyphens() -> None:
    assert _slug("  Weird__Name!! ") == "weird-name"


def test_slug_keeps_digits_and_existing_hyphens() -> None:
    assert _slug("db2-migrator") == "db2-migrator"


def test_slug_falls_back_when_nothing_survives() -> None:
    assert _slug("!!!") == "agent"


def test_mapping_rejects_claude_prefixed_frontmatter_injection() -> None:
    """A `claude-*` value carrying newlines would be interpolated into every
    deployed agent's frontmatter, silently adding keys (e.g. `tools:`).
    Only a plain model-ID shape may pass through."""
    hostile = "claude-x\ntools: [Bash]\nmodel: opus"
    config = ModelTierConfig(advisor=hostile, executor=None)

    mapping, skipped = claude_model_tier_mapping(config)

    assert mapping == {}
    assert skipped == {"advisor": hostile}


def test_mapping_rejects_claude_prefixed_value_with_spaces() -> None:
    config = ModelTierConfig(advisor="claude-x something", executor=None)

    mapping, skipped = claude_model_tier_mapping(config)

    assert mapping == {}
    assert skipped == {"advisor": "claude-x something"}
