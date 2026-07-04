"""Unit tests for materializing model tiers into deployed agent frontmatter."""

from deploy_ai_playbook.config import ModelTierConfig
from deploy_ai_playbook.services.deploy import (
    claude_model_tier_mapping,
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
