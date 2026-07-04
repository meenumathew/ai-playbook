"""Unit tests for layered discovery (core + packs)."""

from __future__ import annotations

from pathlib import Path

from deploy_ai_playbook.config import Source
from deploy_ai_playbook.discovery import LayeredDiscovery, Override, discover_layered


def _make_core(tmp_path: Path) -> Path:
    """Create a minimal core source root with one agent."""
    core = tmp_path / "core"
    (core / "agents").mkdir(parents=True)
    (core / "agents" / "story-refiner.agent.md").write_text("# core story-refiner\n")
    return core


def test_discover_layered_returns_core_only_when_no_packs(tmp_path: Path) -> None:
    """With no packs, discover_layered yields the core files with origin='core'."""
    core = _make_core(tmp_path)

    result = discover_layered(core, packs=[])

    assert isinstance(result, LayeredDiscovery)
    assert len(result.files) == 1
    assert result.files[0].origin == "core"
    assert result.files[0].relative == Path("agents/story-refiner.agent.md")
    assert result.files[0].src_path == core / "agents" / "story-refiner.agent.md"
    assert result.overrides == []


def test_discover_layered_includes_pack_files(tmp_path: Path) -> None:
    """A pack adding a new agent file appears alongside core, with origin='pack:django'."""
    core = _make_core(tmp_path)
    pack_root = tmp_path / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    (pack_root / "agents" / "django-model-reviewer.agent.md").write_text(
        "# django-model-reviewer\n"
    )
    pack = Source(origin="pack:django", root=pack_root)

    result = discover_layered(core, packs=[pack])

    by_relative = {f.relative: f for f in result.files}
    assert by_relative[Path("agents/story-refiner.agent.md")].origin == "core"
    assert by_relative[Path("agents/django-model-reviewer.agent.md")].origin == "pack:django"
    assert result.overrides == []  # no shared relative path → no overrides


def test_discover_layered_pack_overrides_core_with_same_relative_path(tmp_path: Path) -> None:
    """When a pack file shares a relative path with core, the pack file wins after merge."""
    core = _make_core(tmp_path)
    pack_root = tmp_path / "packs" / "internal"
    (pack_root / "agents").mkdir(parents=True)
    pack_override = pack_root / "agents" / "story-refiner.agent.md"
    pack_override.write_text("# internal override of story-refiner\n")
    pack = Source(origin="pack:internal", root=pack_root)

    result = discover_layered(core, packs=[pack])

    matching = [f for f in result.files if f.relative == Path("agents/story-refiner.agent.md")]
    assert len(matching) == 1, f"expected exactly one winner, got {len(matching)}"
    assert matching[0].origin == "pack:internal"
    assert matching[0].src_path == pack_override


def test_discover_layered_last_pack_wins_on_cross_pack_conflict(tmp_path: Path) -> None:
    """Two packs both override the same core file — the last pack in the list wins."""
    core = _make_core(tmp_path)

    pack_a_root = tmp_path / "packs" / "django"
    (pack_a_root / "agents").mkdir(parents=True)
    (pack_a_root / "agents" / "story-refiner.agent.md").write_text("# pack-a override\n")

    pack_b_root = tmp_path / "packs" / "project-a"
    (pack_b_root / "agents").mkdir(parents=True)
    pack_b_file = pack_b_root / "agents" / "story-refiner.agent.md"
    pack_b_file.write_text("# pack-b override\n")

    pack_a = Source(origin="pack:django", root=pack_a_root)
    pack_b = Source(origin="pack:project-a", root=pack_b_root)

    result = discover_layered(core, packs=[pack_a, pack_b])

    matching = [f for f in result.files if f.relative == Path("agents/story-refiner.agent.md")]
    assert len(matching) == 1
    assert matching[0].origin == "pack:project-a"
    assert matching[0].src_path == pack_b_file


def test_discover_layered_emits_override_records(tmp_path: Path) -> None:
    """Each pack-overrides-something case produces an Override record callers can warn on."""
    core = _make_core(tmp_path)

    pack_a_root = tmp_path / "packs" / "django"
    (pack_a_root / "agents").mkdir(parents=True)
    (pack_a_root / "agents" / "story-refiner.agent.md").write_text("# pack-a override\n")

    pack_b_root = tmp_path / "packs" / "project-a"
    (pack_b_root / "agents").mkdir(parents=True)
    (pack_b_root / "agents" / "story-refiner.agent.md").write_text("# pack-b override\n")

    pack_a = Source(origin="pack:django", root=pack_a_root)
    pack_b = Source(origin="pack:project-a", root=pack_b_root)

    result = discover_layered(core, packs=[pack_a, pack_b])

    # Two overrides should be recorded:
    #   1. pack:django overrode core
    #   2. pack:project-a overrode pack:django
    assert len(result.overrides) == 2
    assert result.overrides[0] == Override(
        relative=Path("agents/story-refiner.agent.md"),
        previous_origin="core",
        new_origin="pack:django",
    )
    assert result.overrides[1] == Override(
        relative=Path("agents/story-refiner.agent.md"),
        previous_origin="pack:django",
        new_origin="pack:project-a",
    )


def test_discover_layered_skips_hidden_files_and_disabled_files(tmp_path: Path) -> None:
    """Parity with existing _iter_visible_files: hidden (.foo) files are skipped.

    Note: '.disabled' suffix files live in *deployed* directories, not source.
    Source roots should never contain them, but a stray hidden file (.DS_Store,
    .gitkeep) must not break discovery or appear in the deployed set.
    """
    core = _make_core(tmp_path)
    (core / "agents" / ".DS_Store").write_text("garbage\n")
    (core / "agents" / ".gitkeep").write_text("")

    pack_root = tmp_path / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    (pack_root / "agents" / ".hidden-pack-file").write_text("garbage\n")
    (pack_root / "agents" / "django-pack.agent.md").write_text("# pack\n")
    pack = Source(origin="pack:django", root=pack_root)

    result = discover_layered(core, packs=[pack])

    relatives = {f.relative for f in result.files}
    # Hidden files MUST NOT appear:
    assert Path("agents/.DS_Store") not in relatives
    assert Path("agents/.gitkeep") not in relatives
    assert Path("agents/.hidden-pack-file") not in relatives
    # Real files DO appear:
    assert Path("agents/story-refiner.agent.md") in relatives
    assert Path("agents/django-pack.agent.md") in relatives


def test_discover_layered_skips_pack_symlink_files(tmp_path: Path) -> None:
    """Pack discovery must not copy file content through symlinks.

    Pack paths are constrained to the project root, but a symlink inside a pack
    can point outside that root. Discovery should ignore the symlink rather than
    treating it as a normal markdown file.
    """
    core = _make_core(tmp_path)
    secret_file = tmp_path / "outside-secret.md"
    secret_file.write_text("token = should-not-be-deployed\n")

    pack_root = tmp_path / "packs" / "internal"
    pack_agents = pack_root / "agents"
    pack_agents.mkdir(parents=True)
    symlink_file = pack_agents / "leaked.agent.md"
    symlink_file.symlink_to(secret_file)
    (pack_agents / "real.agent.md").write_text("# real pack file\n")
    pack = Source(origin="pack:internal", root=pack_root)

    result = discover_layered(core, packs=[pack])
    relatives = {entry.relative for entry in result.files}

    assert Path("agents/leaked.agent.md") not in relatives
    assert Path("agents/real.agent.md") in relatives


def test_expected_deployed_files_includes_pack_relative_paths(tmp_path: Path) -> None:
    """expected_deployed_files() with discovered_files contains pack relatives.

    The agents-deployed-set must include any pack-only agent paths so that
    prune does not flag them as orphans. This is the unit-level guarantee
    behind AC 4.
    """
    from deploy_ai_playbook.fs import expected_deployed_files
    from deploy_ai_playbook.paths import Tool

    core = _make_core(tmp_path)
    pack_root = tmp_path / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    (pack_root / "agents" / "django-pack.agent.md").write_text("# pack\n")
    pack = Source(origin="pack:django", root=pack_root)

    result = discover_layered(core, packs=[pack])
    expected = expected_deployed_files(core, Tool.claude, discovered_files=result.files)

    assert Path("django-pack.agent.md") in expected[".claude/agents"]
    assert Path("story-refiner.agent.md") in expected[".claude/agents"]


def test_compute_source_fingerprint_includes_pack_files(tmp_path: Path) -> None:
    """Fingerprint changes when pack content changes.

    Adopters need this so `doctor` flags fingerprint mismatch when a pack
    file is edited — i.e. version tracking covers pack content, not just
    core. Without this, pack drift would be invisible.
    """
    from deploy_ai_playbook.fs import compute_source_fingerprint

    core = _make_core(tmp_path)
    pack_root = tmp_path / "packs" / "django"
    (pack_root / "agents").mkdir(parents=True)
    pack_file = pack_root / "agents" / "django-pack.agent.md"
    pack_file.write_text("# original pack content\n")
    pack = Source(origin="pack:django", root=pack_root)

    result_v1 = discover_layered(core, packs=[pack])
    fp_v1 = compute_source_fingerprint(core, discovered_files=result_v1.files)

    # Mutate pack file:
    pack_file.write_text("# CHANGED pack content\n")
    result_v2 = discover_layered(core, packs=[pack])
    fp_v2 = compute_source_fingerprint(core, discovered_files=result_v2.files)

    assert fp_v1 != fp_v2, "fingerprint must change when pack content changes"
