"""Unit tests for static context-surface measurement."""

from pathlib import Path

import pytest

from deploy_ai_playbook.discovery import DeployableFile
from deploy_ai_playbook.services.context_report import (
    ContextReportError,
    build_context_report,
)


def _entry(root: Path, relative: str, content: str, origin: str = "core") -> DeployableFile:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return DeployableFile(origin=origin, relative=Path(relative), src_path=path)


def _fixed_surfaces(root: Path) -> list[DeployableFile]:
    (root / "CLAUDE.md").write_text("rules", encoding="utf-8")
    return [_entry(root, "knowledge-base/CHEATSHEET.md", "cheatsheet")]


def test_context_report_rejects_preload_path_escape(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(
        _entry(
            tmp_path,
            "agents/reviewer.agent.md",
            "---\npreload: ../secret.md\n---\n# Reviewer\n",
        )
    )

    with pytest.raises(ContextReportError, match="unsafe preload path"):
        build_context_report(tmp_path, files, ["reviewer"])


def test_context_report_fails_when_declared_preload_is_missing(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(
        _entry(
            tmp_path,
            "agents/reviewer.agent.md",
            "---\npreload: missing.md\n---\n# Reviewer\n",
        )
    )

    with pytest.raises(ContextReportError, match="missing declared context surface"):
        build_context_report(tmp_path, files, ["reviewer"])


def test_context_report_uses_layered_kb_override(tmp_path):
    files = _fixed_surfaces(tmp_path)
    core_kb = _entry(tmp_path, "core/review.md", "short")
    pack_kb = _entry(tmp_path, "pack/review.md", "pack override", origin="pack:team")
    files.extend(
        [
            DeployableFile(
                origin="core",
                relative=Path("knowledge-base/review.md"),
                src_path=core_kb.src_path,
            ),
            DeployableFile(
                origin="pack:team",
                relative=Path("knowledge-base/review.md"),
                src_path=pack_kb.src_path,
            ),
            _entry(
                tmp_path,
                "agents/reviewer.agent.md",
                "---\npreload: review.md § Review Rules\n---\n# Reviewer\n",
            ),
        ]
    )

    report = build_context_report(tmp_path, files, ["reviewer"])

    assert report.agents[0].preloads[0].characters == len("pack override")


def test_context_report_rejects_unknown_agent_and_lists_available(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(_entry(tmp_path, "agents/reviewer.agent.md", "# Reviewer\n"))

    with pytest.raises(ContextReportError, match=r"unknown agent 'planner'.*reviewer"):
        build_context_report(tmp_path, files, ["planner"])


def test_context_report_treats_agent_without_frontmatter_as_preload_free(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(_entry(tmp_path, "agents/reviewer.agent.md", "# Reviewer\nNo frontmatter.\n"))

    report = build_context_report(tmp_path, files, ["reviewer"])

    assert report.agents[0].preloads == ()


def test_context_report_rejects_unclosed_frontmatter(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(
        _entry(tmp_path, "agents/reviewer.agent.md", "---\npreload: review.md\n# Reviewer\n")
    )

    with pytest.raises(ContextReportError, match="unclosed YAML frontmatter"):
        build_context_report(tmp_path, files, ["reviewer"])


def test_context_report_treats_frontmatter_without_preload_key_as_preload_free(tmp_path):
    files = _fixed_surfaces(tmp_path)
    files.append(
        _entry(tmp_path, "agents/reviewer.agent.md", "---\nid: reviewer\n---\n# Reviewer\n")
    )

    report = build_context_report(tmp_path, files, ["reviewer"])

    assert report.agents[0].preloads == ()


def test_context_report_reports_a_surface_it_cannot_decode(tmp_path):
    """A non-UTF-8 rules file fails the measurement instead of crashing it.

    Characters are the unit of measurement, so an undecodable file has no
    size: reporting a total that silently omitted it would understate the
    context an agent actually loads.
    """
    files = _fixed_surfaces(tmp_path)
    (tmp_path / "CLAUDE.md").write_bytes(b"\xff\xfe rules")
    files.append(_entry(tmp_path, "agents/reviewer.agent.md", "# Reviewer\n"))

    with pytest.raises(ContextReportError, match=r"cannot read context surface CLAUDE\.md"):
        build_context_report(tmp_path, files, ["reviewer"])


def test_context_report_skips_empty_items_in_a_preload_list(tmp_path):
    """A trailing comma or stray separator must not be measured as a surface."""
    files = _fixed_surfaces(tmp_path)
    files.append(_entry(tmp_path, "knowledge-base/review.md", "review rules"))
    files.append(
        _entry(
            tmp_path,
            "agents/reviewer.agent.md",
            "---\npreload: review.md, , \n---\n# Reviewer\n",
        )
    )

    report = build_context_report(tmp_path, files, ["reviewer"])

    assert [surface.path for surface in report.agents[0].preloads] == ["knowledge-base/review.md"]
