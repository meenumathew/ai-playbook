"""Property-based fuzz tests for the parsing and path-safety boundaries.

These are the fuzz targets `docs/limitations.md` § Security named: arbitrary
input must never escape the documented error contract. Config parsing may
reject input only via `ConfigError` or the CLI's `typer.Exit`; path safety must
contain every write inside the project root. `derandomize=True` keeps CI runs reproducible —
the same examples run every time, so a failure is always replayable.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import click
import typer
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from deploy_ai_playbook.config import ConfigError, load_pack_config
from deploy_ai_playbook.fs import generated_command_shim
from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.safety import UnsafeDestinationError, assert_safe_destination
from deploy_ai_playbook.targets import COMMAND_ARGUMENTS_PLACEHOLDER, get_target_adapter

FUZZ_SETTINGS = settings(
    max_examples=75,
    derandomize=True,
    suppress_health_check=[HealthCheck.too_slow],
)

# Text without surrogates — surrogates fail at file-write time in the test
# harness itself, before the code under test ever runs.
_writable_text = st.text(alphabet=st.characters(exclude_categories=("Cs",)), max_size=300)

# Path-ish segments: printable ASCII including traversal characters.
_path_segment = st.text(
    alphabet=st.characters(min_codepoint=33, max_codepoint=126),
    min_size=1,
    max_size=20,
)


@FUZZ_SETTINGS
@given(content=_writable_text)
def test_load_pack_config_rejects_arbitrary_config_only_via_config_error(content: str) -> None:
    """Malformed `.ai-playbook.toml` content must never raise an unhandled
    exception type — the library contract is a clean `ConfigError`."""
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)
        (project_root / ".ai-playbook.toml").write_text(content, encoding="utf-8")
        try:
            result = load_pack_config(project_root)
        except (ConfigError, typer.Exit, click.exceptions.Exit):
            return
        assert isinstance(result, list)


@FUZZ_SETTINGS
@given(segments=st.lists(_path_segment, min_size=1, max_size=4))
def test_load_pack_config_never_yields_pack_root_outside_project(segments: list[str]) -> None:
    """Whatever path string a config declares, an accepted pack root always
    resolves inside the project root — traversal is rejected, not resolved."""
    pack_entry = "/".join(segments)
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp).resolve()
        config = f'packs = ["{pack_entry}"]\n'
        (project_root / ".ai-playbook.toml").write_text(config, encoding="utf-8")
        try:
            sources = load_pack_config(project_root)
        except (ConfigError, typer.Exit, click.exceptions.Exit):
            return
        for source in sources:
            resolved = source.root.resolve()
            assert resolved.is_relative_to(project_root), (
                f"pack entry {pack_entry!r} escaped the project root: {resolved}"
            )


@FUZZ_SETTINGS
@given(segments=st.lists(_path_segment, min_size=1, max_size=4))
def test_assert_safe_destination_contains_writes_or_raises(segments: list[str]) -> None:
    """Any destination that does not resolve under the safe root must raise;
    in-root destinations (no symlinks involved) must pass."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp).resolve()
        candidate = root.joinpath(*segments)
        try:
            assert_safe_destination(candidate, root)
        except UnsafeDestinationError:
            # Raising is only correct when the path actually escapes.
            assert not candidate.absolute().resolve().is_relative_to(root)
            return
        # Accepted: the lexical path must sit inside the root.
        assert str(candidate.absolute()).startswith(str(root))


@FUZZ_SETTINGS
@given(
    agent_name=st.text(
        alphabet=st.characters(min_codepoint=ord("a"), max_codepoint=ord("z")),
        min_size=1,
        max_size=40,
    )
)
def test_generated_shim_round_trips_through_every_command_target(agent_name: str) -> None:
    """Generated shims carry exactly one arguments placeholder, and every
    command-supporting tool's transform consumes it."""
    shim = generated_command_shim(agent_name)
    assert shim.count(COMMAND_ARGUMENTS_PLACEHOLDER) == 1
    for tool in (Tool.claude, Tool.copilot):
        target = get_target_adapter(tool)
        output_name, content = target.transform_command(f"{agent_name}.md", shim)
        assert output_name.startswith(agent_name)
        placeholder = target.command_argument_placeholder or COMMAND_ARGUMENTS_PLACEHOLDER
        assert placeholder in content
        if placeholder != COMMAND_ARGUMENTS_PLACEHOLDER:
            assert COMMAND_ARGUMENTS_PLACEHOLDER not in content
