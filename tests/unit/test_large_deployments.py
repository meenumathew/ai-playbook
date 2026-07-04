"""Large-fixture integration tests for discovery, prune, and doctor paths.

These verify behavioral correctness on deployments far larger than the shipped
playbook (80 agents, 160 KB files). They measure no timings and set no
performance thresholds — they are not benchmarks.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from deploy_ai_playbook.backup import write_version_file
from deploy_ai_playbook.config import Source
from deploy_ai_playbook.discovery import discover_layered
from deploy_ai_playbook.doctor import DoctorService
from deploy_ai_playbook.fs import expected_deployed_files, prune_orphaned_files
from deploy_ai_playbook.paths import HARNESS_FILES, Tool
from deploy_ai_playbook.targets import get_target_adapter

AGENT_COUNT = 80
KNOWLEDGE_BASE_COUNT = 160
SKILL_COUNT = 45
TEMPLATE_COUNT = 35
COMMAND_COUNT = 80
PACK_AGENT_COUNT = 20
PACK_KNOWLEDGE_BASE_COUNT = 30
PACK_OVERRIDE_COUNT = 10
ORPHAN_AGENT_COUNT = 25
ORPHAN_KNOWLEDGE_BASE_COUNT = 25
STALE_KNOWLEDGE_BASE_COUNT = 7


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _seed_large_core(root: Path) -> None:
    for index in range(AGENT_COUNT):
        _write_text(root / "agents" / f"agent-{index:03}.agent.md", f"# Agent {index:03}\n")
    for index in range(KNOWLEDGE_BASE_COUNT):
        _write_text(
            root / "knowledge-base" / f"section-{index % 8}" / f"topic-{index:03}.md",
            f"# Topic {index:03}\n",
        )
    for index in range(SKILL_COUNT):
        _write_text(root / "skills" / f"tool-{index:03}" / "SKILL.md", f"# Tool {index:03}\n")
    for index in range(TEMPLATE_COUNT):
        _write_text(root / "templates" / f"template-{index:03}.md", f"# Template {index:03}\n")
    for index in range(COMMAND_COUNT):
        _write_text(root / "commands" / f"agent-{index:03}.md", "Run with $ARGUMENTS\n")
    _write_text(root / "CLAUDE.md", "# Rules\n")


def _seed_large_pack(root: Path) -> None:
    for index in range(PACK_AGENT_COUNT):
        _write_text(
            root / "agents" / f"pack-agent-{index:03}.agent.md",
            f"# Pack Agent {index:03}\n",
        )
    for index in range(PACK_OVERRIDE_COUNT):
        _write_text(
            root / "agents" / f"agent-{index:03}.agent.md",
            f"# Pack Override {index:03}\n",
        )
    for index in range(PACK_KNOWLEDGE_BASE_COUNT):
        _write_text(
            root / "knowledge-base" / "pack" / f"topic-{index:03}.md",
            f"# Pack Topic {index:03}\n",
        )


def _mirror_core_deployment(source_root: Path, project_root: Path, tool: Tool) -> None:
    target = get_target_adapter(tool)
    for overlay in ("agents", "knowledge-base", "skills", "templates"):
        shutil.copytree(source_root / overlay, project_root / target.destination(overlay))
    shutil.copy2(source_root / "CLAUDE.md", project_root / target.destination("rules"))
    write_version_file(project_root, source_root, tool, dry_run=False)
    for runtime_dir in ("stories", "plans", "research", "audits", "reviews", "incidents"):
        (project_root / runtime_dir).mkdir()
    for deployed_path in HARNESS_FILES.values():
        _write_text(project_root / deployed_path, "# deployed harness\n")


def test_discover_layered_handles_large_pack_overlay(tmp_path: Path) -> None:
    core = tmp_path / "core"
    pack_root = tmp_path / "packs" / "large"
    _seed_large_core(core)
    _seed_large_pack(pack_root)

    result = discover_layered(core, packs=[Source(origin="pack:large", root=pack_root)])

    core_file_count = AGENT_COUNT + KNOWLEDGE_BASE_COUNT + SKILL_COUNT + TEMPLATE_COUNT
    pack_only_count = PACK_AGENT_COUNT + PACK_KNOWLEDGE_BASE_COUNT
    assert len(result.files) == core_file_count + pack_only_count
    assert len(result.overrides) == PACK_OVERRIDE_COUNT
    by_relative = {entry.relative: entry for entry in result.files}
    assert by_relative[Path("agents/agent-000.agent.md")].origin == "pack:large"
    assert Path("agents/pack-agent-019.agent.md") in by_relative
    assert Path("knowledge-base/pack/topic-029.md") in by_relative


def test_prune_orphaned_files_handles_large_deployment(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    project_root = tmp_path / "project"
    _seed_large_core(source_root)
    target = get_target_adapter(Tool.claude)
    discovered_files = discover_layered(source_root, packs=[]).files

    for deployed_subdir, expected_files in expected_deployed_files(
        source_root, Tool.claude, discovered_files
    ).items():
        for relative in expected_files:
            _write_text(project_root / deployed_subdir / relative, f"deployed {relative}\n")

    orphan_paths = [
        project_root / target.destination("agents") / f"orphan-{index:03}.agent.md"
        for index in range(ORPHAN_AGENT_COUNT)
    ]
    orphan_paths.extend(
        project_root / target.destination("knowledge-base") / f"orphan-{index:03}.md"
        for index in range(ORPHAN_KNOWLEDGE_BASE_COUNT)
    )
    for orphan_path in orphan_paths:
        _write_text(orphan_path, "# orphan\n")
    disabled_path = project_root / target.destination("agents") / "agent-000.agent.md.disabled"
    _write_text(disabled_path, "# disabled\n")

    results = prune_orphaned_files(
        project_root, source_root, Tool.claude, dry_run=False, discovered_files=discovered_files
    )

    assert len(results) == ORPHAN_AGENT_COUNT + ORPHAN_KNOWLEDGE_BASE_COUNT
    assert all(not orphan_path.exists() for orphan_path in orphan_paths)
    assert disabled_path.exists()
    assert (project_root / target.destination("agents") / "agent-000.agent.md").exists()


def test_doctor_service_reports_large_fixture_stale_counts(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    project_root = tmp_path / "project"
    _seed_large_core(source_root)
    _mirror_core_deployment(source_root, project_root, Tool.claude)

    target = get_target_adapter(Tool.claude)
    deployed_kb_files = sorted((project_root / target.destination("knowledge-base")).rglob("*.md"))
    for deployed_file in deployed_kb_files[:STALE_KNOWLEDGE_BASE_COUNT]:
        deployed_file.write_text("# stale\n")

    report = DoctorService().check(
        source_root=source_root,
        project_root=project_root,
        tool=Tool.claude,
    )

    assert report.issues == []
    assert (
        f"[cyan]knowledge-base[/cyan] has {STALE_KNOWLEDGE_BASE_COUNT} stale/missing file(s)"
        in report.warnings
    )
