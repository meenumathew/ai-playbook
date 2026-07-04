"""Unit tests for `.ai-playbook.toml` pack config reader."""

from __future__ import annotations

from pathlib import Path
from typing import NoReturn

import pytest

import deploy_ai_playbook.config as config
from deploy_ai_playbook.config import (
    PACK_METADATA_FILE,
    ConfigError,
    load_model_tier_config,
    load_pack_config,
    load_quality_tier_config,
)


def test_load_pack_config_returns_empty_list_when_no_toml_file(tmp_path: Path) -> None:
    """A project without `.ai-playbook.toml` has no packs — return an empty list."""
    assert load_pack_config(tmp_path) == []


def test_load_model_tier_config_returns_none_when_no_toml_file(tmp_path: Path) -> None:
    assert load_model_tier_config(tmp_path) is None


def test_load_model_tier_config_returns_none_when_table_missing(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text("packs = []\n")

    assert load_model_tier_config(tmp_path) is None


def test_load_model_tier_config_reads_advisor_and_executor(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = "Claude Opus"\nexecutor = "Claude Sonnet"\n'
    )

    model_tiers = load_model_tier_config(tmp_path)

    assert model_tiers is not None
    assert model_tiers.advisor == "Claude Opus"
    assert model_tiers.executor == "Claude Sonnet"


def test_load_model_tier_config_allows_partial_mapping(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('[model_tiers]\nadvisor = "Claude Opus"\n')

    model_tiers = load_model_tier_config(tmp_path)

    assert model_tiers is not None
    assert model_tiers.advisor == "Claude Opus"
    assert model_tiers.executor is None


def test_load_model_tier_config_rejects_non_table_mapping(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('model_tiers = "Claude"\n')

    with pytest.raises(ConfigError):
        load_model_tier_config(tmp_path)


def test_load_model_tier_config_rejects_empty_tier_value(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[model_tiers]\nadvisor = ""\nexecutor = "Claude Sonnet"\n'
    )

    with pytest.raises(ConfigError):
        load_model_tier_config(tmp_path)


def test_load_quality_tier_config_returns_empty_when_no_toml_file(tmp_path: Path) -> None:
    quality_tiers = load_quality_tier_config(tmp_path)

    assert quality_tiers.agent_overrides == {}


def test_load_quality_tier_config_reads_agent_overrides(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[quality_tiers.agents]\nxp-pair-programmer = "production"\ndocs-maintainer = "prototype"\n'
    )

    quality_tiers = load_quality_tier_config(tmp_path)

    assert quality_tiers.agent_overrides == {
        "xp-pair-programmer": "production",
        "docs-maintainer": "prototype",
    }


def test_load_quality_tier_config_normalizes_tier_values(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[quality_tiers.agents]\nxp-pair-programmer = "Production"\n'
    )

    quality_tiers = load_quality_tier_config(tmp_path)

    assert quality_tiers.agent_overrides == {"xp-pair-programmer": "production"}


def test_load_quality_tier_config_rejects_invalid_tier_value(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text(
        '[quality_tiers.agents]\nxp-pair-programmer = "strict"\n'
    )

    with pytest.raises(ConfigError):
        load_quality_tier_config(tmp_path)


def test_load_quality_tier_config_rejects_non_table_quality_tiers(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('quality_tiers = "production"\n')

    with pytest.raises(ConfigError):
        load_quality_tier_config(tmp_path)


def test_load_quality_tier_config_rejects_non_table_agents(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('quality_tiers = { agents = "production" }\n')

    with pytest.raises(ConfigError):
        load_quality_tier_config(tmp_path)


def test_load_quality_tier_config_rejects_empty_agent_name(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text('[quality_tiers.agents]\n"" = "production"\n')

    with pytest.raises(ConfigError):
        load_quality_tier_config(tmp_path)


def test_load_quality_tier_config_rejects_non_string_tier_value(tmp_path: Path) -> None:
    (tmp_path / ".ai-playbook.toml").write_text("[quality_tiers.agents]\nxp-pair-programmer = 1\n")

    with pytest.raises(ConfigError):
        load_quality_tier_config(tmp_path)


def test_load_pack_config_reads_packs_field_in_order(tmp_path: Path) -> None:
    """`packs` list order is preserved — last-pack-wins precedence depends on it."""
    (tmp_path / ".ai-playbook").mkdir()
    (tmp_path / ".ai-playbook" / "packs").mkdir()
    for name in ("django", "internal", "project-a"):
        (tmp_path / ".ai-playbook" / "packs" / name).mkdir()
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/django", ".ai-playbook/packs/internal", '
        '".ai-playbook/packs/project-a"]\n'
    )

    sources = load_pack_config(tmp_path)

    assert [s.origin for s in sources] == [
        "pack:django",
        "pack:internal",
        "pack:project-a",
    ]


def test_load_pack_config_resolves_paths_relative_to_project_root(tmp_path: Path) -> None:
    """Pack paths in the config are resolved against the project root, not the cwd."""
    pack_dir = tmp_path / "custom" / "pack-location"
    pack_dir.mkdir(parents=True)
    (tmp_path / ".ai-playbook.toml").write_text('packs = ["custom/pack-location"]\n')

    sources = load_pack_config(tmp_path)

    assert len(sources) == 1
    assert sources[0].root == pack_dir
    assert sources[0].root.is_absolute()


def test_load_pack_config_reads_pack_metadata(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "django"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text(
        'name = "django"\n'
        'version = "1.2.3"\n'
        'min_playbook_version = "1.0.0"\n'
        'max_playbook_version = "1.9.0"\n'
    )
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/django"]\n')

    sources = load_pack_config(tmp_path)

    assert sources[0].origin == "pack:django"
    metadata = sources[0].metadata
    assert metadata is not None
    assert metadata.name == "django"
    assert metadata.version == "1.2.3"
    assert metadata.min_playbook_version == "1.0.0"
    assert metadata.max_playbook_version == "1.9.0"


def test_load_pack_config_rejects_incompatible_pack(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "future"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text(
        'name = "future"\nversion = "1.0.0"\nmin_playbook_version = "999.0.0"\n'
    )
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/future"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_invalid_pack_metadata_version(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "invalid"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text('name = "invalid"\nversion = "not-semver"\n')
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/invalid"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_duplicate_resolved_pack_roots(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/internal", ".ai-playbook/packs/../packs/internal"]\n'
    )

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_duplicate_pack_names(tmp_path: Path) -> None:
    first_pack = tmp_path / ".ai-playbook" / "packs" / "first"
    second_pack = tmp_path / ".ai-playbook" / "packs" / "second"
    first_pack.mkdir(parents=True)
    second_pack.mkdir(parents=True)
    for pack_dir in (first_pack, second_pack):
        (pack_dir / PACK_METADATA_FILE).write_text('name = "shared"\nversion = "1.0.0"\n')
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/first", ".ai-playbook/packs/second"]\n'
    )

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_malformed_pack_metadata(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text("name = [unterminated\n")
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/internal"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_invalid_pack_metadata_name(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text('name = ""\nversion = "1.0.0"\n')
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/internal"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_non_string_pack_metadata_version(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text('name = "internal"\nversion = 1\n')
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/internal"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_pack_with_expired_compatibility(tmp_path: Path) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "old"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text(
        'name = "old"\nversion = "1.0.0"\nmax_playbook_version = "0.0.1"\n'
    )
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/old"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_skips_compatibility_when_playbook_version_is_unparseable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "future"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text(
        'name = "future"\nversion = "1.0.0"\nmin_playbook_version = "999.0.0"\n'
    )
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/future"]\n')
    monkeypatch.setattr(config, "current_playbook_version", lambda: "local-dev")

    metadata = load_pack_config(tmp_path)[0].metadata
    assert metadata is not None
    assert metadata.name == "future"


def test_load_pack_config_handles_missing_package_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_package_not_found(_: str) -> NoReturn:
        raise config.PackageNotFoundError

    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (pack_dir / PACK_METADATA_FILE).write_text('name = "internal"\nversion = "1.0.0"\n')
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/internal"]\n')
    monkeypatch.setattr(config, "version", raise_package_not_found)

    metadata = load_pack_config(tmp_path)[0].metadata
    assert metadata is not None
    assert metadata.version == "1.0.0"


def test_current_playbook_version_reads_local_pyproject_when_package_metadata_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def raise_package_not_found(_: str) -> NoReturn:
        raise config.PackageNotFoundError

    monkeypatch.setattr(config, "version", raise_package_not_found)

    assert config.current_playbook_version() == "1.0.0"


def test_load_pack_config_raises_on_malformed_toml(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Malformed TOML must fail loudly without printing from the config layer."""
    (tmp_path / ".ai-playbook.toml").write_text("packs = [unterminated\n")

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_load_pack_config_raises_on_missing_pack_dir(tmp_path: Path) -> None:
    """A pack path that does not exist on disk must fail loudly — typo detection."""
    (tmp_path / ".ai-playbook.toml").write_text('packs = [".ai-playbook/packs/does-not-exist"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_non_list_packs(tmp_path: Path) -> None:
    """`packs` must be a list so typos don't degrade into character-by-character paths."""
    (tmp_path / ".ai-playbook.toml").write_text('packs = ".ai-playbook/packs/internal"\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_non_string_pack_entries(tmp_path: Path) -> None:
    """Every pack entry must be a path string."""
    (tmp_path / ".ai-playbook.toml").write_text("packs = [123]\n")

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_duplicate_pack_paths(tmp_path: Path) -> None:
    """Duplicate pack paths make override order noisy without adding behaviour."""
    pack_dir = tmp_path / ".ai-playbook" / "packs" / "internal"
    pack_dir.mkdir(parents=True)
    (tmp_path / ".ai-playbook.toml").write_text(
        'packs = [".ai-playbook/packs/internal", ".ai-playbook/packs/internal"]\n'
    )

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_empty_pack_paths(tmp_path: Path) -> None:
    """An empty path would resolve to the project root, which is never a pack."""
    (tmp_path / ".ai-playbook.toml").write_text('packs = [""]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_absolute_pack_paths(tmp_path: Path) -> None:
    """Pack paths are project-relative by contract."""
    pack_dir = tmp_path / "pack"
    pack_dir.mkdir()
    (tmp_path / ".ai-playbook.toml").write_text(f'packs = ["{pack_dir}"]\n')

    with pytest.raises(ConfigError):
        load_pack_config(tmp_path)


def test_load_pack_config_rejects_paths_outside_project_root(tmp_path: Path) -> None:
    """Relative pack paths must not escape the adopter project root."""
    outside = tmp_path.parent / f"{tmp_path.name}-outside-pack"
    outside.mkdir()
    (tmp_path / ".ai-playbook.toml").write_text(f'packs = ["../{outside.name}"]\n')

    try:
        with pytest.raises(ConfigError):
            load_pack_config(tmp_path)
    finally:
        outside.rmdir()


# ---------------------------------------------------------------------------
# load_issue_tracker_provider
# ---------------------------------------------------------------------------


def test_load_issue_tracker_provider_returns_none_without_config(tmp_path):
    from deploy_ai_playbook.config import load_issue_tracker_provider

    assert load_issue_tracker_provider(tmp_path) is None


def test_load_issue_tracker_provider_returns_none_without_table(tmp_path):
    from deploy_ai_playbook.config import load_issue_tracker_provider

    (tmp_path / ".ai-playbook.toml").write_text('[model_tiers]\nadvisor = "m"\n')

    assert load_issue_tracker_provider(tmp_path) is None


def test_load_issue_tracker_provider_normalizes_case(tmp_path):
    from deploy_ai_playbook.config import load_issue_tracker_provider

    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = "Jira"\n')

    assert load_issue_tracker_provider(tmp_path) == "jira"


def test_load_issue_tracker_provider_rejects_non_table(tmp_path):
    from deploy_ai_playbook.config import ConfigError, load_issue_tracker_provider

    (tmp_path / ".ai-playbook.toml").write_text('issue-tracker = "jira"\n')

    with pytest.raises(ConfigError):
        load_issue_tracker_provider(tmp_path)


def test_load_issue_tracker_provider_rejects_empty_string(tmp_path):
    from deploy_ai_playbook.config import ConfigError, load_issue_tracker_provider

    (tmp_path / ".ai-playbook.toml").write_text('[issue-tracker]\nprovider = ""\n')

    with pytest.raises(ConfigError):
        load_issue_tracker_provider(tmp_path)
