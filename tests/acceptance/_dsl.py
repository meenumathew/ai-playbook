"""Domain-action helpers for the acceptance tests.

Each helper wraps one CLI action with optional keyword parameters and
defaults, so a test states only the values its behaviour depends on
(`knowledge-base/testing.md` § Acceptance Test Infrastructure). Plain
functions on purpose: no classes, no fixtures, no cleverness: the moment
this module needs inheritance or config, it has outgrown its job.

Helpers return the raw `CliRunner` result; assertions stay in the tests.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from typer.testing import CliRunner

if TYPE_CHECKING:
    from click.testing import Result

from deploy_ai_playbook.cli import app
from deploy_ai_playbook.paths import Tool
from deploy_ai_playbook.targets import get_target_adapter

runner = CliRunner()


def deploy(
    target: Path,
    *,
    agents: str = "all",
    tool: str = "claude",
    dry_run: bool = False,
    mcp: bool = True,
    harness: bool = True,
    harness_force: bool = False,
    rules: bool = True,
    prune: bool = False,
    yes: bool = False,
    language: str | None = None,
    input: str | None = None,
) -> Result:
    """Run `ai-playbook deploy` against `target`; defaults mirror the CLI's."""
    args = ["deploy", "--agent", agents, "--tool", tool]
    if dry_run:
        args.append("--dry-run")
    if not mcp:
        args.append("--no-mcp")
    if not harness:
        args.append("--no-harness")
    if harness_force:
        args.append("--harness-force")
    if not rules:
        args.append("--no-rules")
    if prune:
        args.append("--prune")
    if yes:
        args.append("--yes")
    if language is not None:
        args.extend(["--language", language])
    args.extend(["-t", str(target)])
    return runner.invoke(app, args, input=input)


def doctor(
    target: Path,
    *,
    tool: str = "claude",
    agents: str | None = None,
    as_json: bool = False,
    strict: bool = False,
    prune: bool = False,
) -> Result:
    """Run `ai-playbook doctor` against `target`."""
    args = ["doctor", "--tool", tool]
    if agents is not None:
        args.extend(["--agent", agents])
    if as_json:
        args.append("--json")
    if strict:
        args.append("--strict")
    if prune:
        args.append("--prune")
    args.extend(["-t", str(target)])
    return runner.invoke(app, args)


def diff(
    target: Path,
    *,
    tool: str = "claude",
    agents: str | None = None,
    as_json: bool = False,
    exit_code: bool = False,
) -> Result:
    """Run `ai-playbook diff` against `target`."""
    args = ["diff", "--tool", tool]
    if agents is not None:
        args.extend(["--agent", agents])
    if as_json:
        args.append("--json")
    if exit_code:
        args.append("--exit-code")
    args.extend(["-t", str(target)])
    return runner.invoke(app, args)


def status(target: Path, *, tool: str = "claude", as_json: bool = False) -> Result:
    """Run `ai-playbook status` against `target`."""
    args = ["status", "--tool", tool]
    if as_json:
        args.append("--json")
    args.extend(["-t", str(target)])
    return runner.invoke(app, args)


def enable(agent: str, target: Path, *, tool: str = "claude") -> Result:
    """Run `ai-playbook enable <agent>` against `target`."""
    return runner.invoke(app, ["enable", agent, "--tool", tool, "-t", str(target)])


def disable(agent: str, target: Path, *, tool: str = "claude") -> Result:
    """Run `ai-playbook disable <agent>` against `target`."""
    return runner.invoke(app, ["disable", agent, "--tool", tool, "-t", str(target)])


def agents_dir(target: Path, tool: str | Tool = "claude") -> Path:
    """The deployed agents directory for `tool` under `target`."""
    return target / get_target_adapter(Tool(tool)).destination("agents")


def assert_agent_deployed(target: Path, agent: str, tool: str | Tool = "claude") -> None:
    adapter = get_target_adapter(Tool(tool))
    path = agents_dir(target, tool) / adapter.agent_output_name(f"{agent}.agent.md")
    assert path.exists(), f"{agent} not deployed for {tool}: missing {path}"


def assert_agent_not_deployed(target: Path, agent: str, tool: str | Tool = "claude") -> None:
    adapter = get_target_adapter(Tool(tool))
    path = agents_dir(target, tool) / adapter.agent_output_name(f"{agent}.agent.md")
    assert not path.exists(), f"{agent} unexpectedly deployed for {tool}: {path}"
