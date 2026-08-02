"""Contract tests for harness, release, ADR, workspace, and terminology invariants."""

import json
import os
import re
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

from deploy_ai_playbook.cli import get_source_root
from deploy_ai_playbook.paths import HARNESS_FILES
from tests import ALL_AGENTS

pytestmark = pytest.mark.repo_contract

FULL_SHA_RE = re.compile(r"[a-f0-9]{40}")


def _repo_file(*parts: str) -> Path:
    return get_source_root().joinpath(*parts)


def _workflow_text(filename: str) -> str:
    return _repo_file(".github", "workflows", filename).read_text()


def _workflow_files() -> list[Path]:
    return [
        *sorted(_repo_file(".github", "workflows").glob("*.yml")),
        _repo_file("harness", "ci.yml"),
    ]


def _workflow_job(text: str, job_name: str) -> str:
    start = text.index(f"  {job_name}:\n")
    next_job = re.search(r"^ {2}[A-Za-z0-9_-]+:\n", text[start + 1 :], re.MULTILINE)
    end = start + 1 + next_job.start() if next_job else len(text)
    return text[start:end]


def _uses_entries(workflow: Path) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    for line_number, line in enumerate(workflow.read_text().splitlines(), start=1):
        match = re.search(r"\buses:\s*([^#\s]+)", line)
        if match:
            entries.append((line_number, match.group(1).strip("'\"")))
    return entries


def test_github_actions_uses_are_pinned_to_full_commit_shas():
    failures: list[str] = []
    for workflow in _workflow_files():
        for line_number, action_ref in _uses_entries(workflow):
            if action_ref.startswith("./"):
                continue
            if "@" not in action_ref:
                failures.append(f"{workflow.name}:{line_number}: {action_ref} has no @ref")
                continue
            ref = action_ref.rsplit("@", 1)[1]
            if not FULL_SHA_RE.fullmatch(ref):
                failures.append(
                    f"{workflow.name}:{line_number}: {action_ref} is not pinned to a full SHA"
                )

    assert not failures, "Unpinned GitHub Actions:\n" + "\n".join(failures)


def test_github_checkout_does_not_persist_credentials_by_default():
    failures: list[str] = []
    for workflow in _workflow_files():
        text = workflow.read_text()
        for match in re.finditer(r"(?m)^\s+uses:\s*actions/checkout@", text):
            start = text.rfind("\n      - ", 0, match.start())
            next_step = text.find("\n      - ", match.end())
            step = text[start : next_step if next_step != -1 else len(text)]
            if not re.search(r"(?m)^\s+persist-credentials:\s*false\s*$", step):
                line_number = text[: match.start()].count("\n") + 1
                failures.append(
                    f"{workflow.name}:{line_number}: actions/checkout must set "
                    "persist-credentials: false"
                )

    assert not failures, "Checkout credentials persisted:\n" + "\n".join(failures)


def test_dependabot_tracks_actions_and_python_dependencies():
    dependabot = _repo_file(".github", "dependabot.yml").read_text()

    assert "package-ecosystem: github-actions" in dependabot
    assert "package-ecosystem: pip" in dependabot
    assert dependabot.count("interval: weekly") >= 2


def test_codeql_scans_python_and_actions_on_schedule():
    workflow = _workflow_text("codeql.yml")

    assert "schedule:" in workflow
    assert "language: [python, actions]" in workflow
    assert "security-events: write" in workflow
    assert "github/codeql-action/init@" in workflow
    assert "github/codeql-action/analyze@" in workflow


def test_scorecard_uses_sarif_upload_with_least_privilege_permissions():
    workflow = _workflow_text("scorecard.yml")
    job = _workflow_job(workflow, "analysis")

    assert "permissions: read-all" not in workflow
    assert re.search(r"^permissions:\n\s+contents:\s+read", workflow, re.MULTILINE)
    for permission in (
        "security-events: write",
        "id-token: write",
        "contents: read",
        "actions: read",
    ):
        assert permission in job
    assert "ossf/scorecard-action@" in job
    assert "github/codeql-action/upload-sarif@" in job


def test_pre_commit_autoupdate_uses_job_token_not_release_deploy_key():
    """The monthly hook-bump job is low-trust (it executes third-party
    pre-commit repos): it must push with the job-scoped GITHUB_TOKEN,
    whose pushes cannot trigger other workflows, and must never touch
    the release deploy key that can push v* tags into release.yml."""
    workflow = _workflow_text("pre-commit-autoupdate.yml")
    job = _workflow_job(workflow, "autoupdate")
    ssh_action = _repo_file(".github", "actions", "configure-release-ssh", "action.yml").read_text()

    assert re.search(r"^permissions:\n\s+contents:\s+read", workflow, re.MULTILINE)
    assert "RELEASE_DEPLOY_KEY" not in workflow
    assert "configure-release-ssh" not in workflow
    assert "contents: write" in job
    assert "pull-requests: write" in job
    assert "git push --force" not in job
    assert "git push origin" in job
    # The composite action stays deploy-key-validating for the release
    # workflows that legitimately use it.
    assert "git ls-remote origin HEAD" in ssh_action
    assert "git push --dry-run" in ssh_action
    assert "UserKnownHostsFile" in ssh_action


def test_release_workflow_generates_sbom_provenance_and_sigstore_signatures():
    workflow = _workflow_text("release.yml")
    build = _workflow_job(workflow, "build")
    sign = _workflow_job(workflow, "sign")
    releasing = _repo_file("RELEASING.md").read_text()

    assert "cyclonedx-bom==" in build
    assert "dist/sbom.cdx.json" in workflow
    assert "actions/attest-build-provenance@" in build
    assert "id-token: write" in build
    assert "attestations: write" in build
    assert "sigstore/gh-action-sigstore-python@" in sign
    assert "id-token: write" in sign
    assert "dist/*.sigstore.json" in sign
    assert "dist/sbom.cdx.json" in sign
    assert "Signs all artifacts with Sigstore" not in releasing
    assert "Signs the distribution artifacts with Sigstore" in releasing


def test_release_pypi_publish_uses_trusted_publishing_without_api_token():
    workflow = _workflow_text("release.yml")
    publish = _workflow_job(workflow, "publish-pypi")

    assert "environment:" in publish
    assert "name: pypi" in publish
    assert "id-token: write" in publish
    assert "pypa/gh-action-pypi-publish@" in publish
    assert "attestations: true" in publish
    for forbidden in ("password:", "api-token", "PYPI_API_TOKEN", "pypi-token"):
        assert forbidden not in workflow
        assert forbidden not in publish


def test_release_validates_quality_before_building_artifacts():
    workflow = _workflow_text("release.yml")
    validate = _workflow_job(workflow, "validate")
    build = _workflow_job(workflow, "build")

    assert workflow.find("  validate:\n") < workflow.find("  build:\n")
    assert "uv sync --dev" in validate
    assert "make quality" in validate
    assert "Smoke-test console script" in validate
    assert "needs: validate" in build


def test_ci_and_release_validate_built_wheel_metadata_before_smoke():
    """Release candidates must test the installable artifact, not source only."""
    ci_workflow = _workflow_text("ci.yml")
    release_workflow = _workflow_text("release.yml")
    release_validate = _workflow_job(release_workflow, "validate")
    release_build = _workflow_job(release_workflow, "build")

    for name, text in (
        ("ci.yml", ci_workflow),
        ("release.yml validate", release_validate),
        ("release.yml build", release_build),
    ):
        assert "uv build" in text, f"{name} must build the distribution"
        assert "twine==6.2.0 check dist/*" in text, (
            f"{name} must validate wheel/sdist metadata with pinned twine"
        )

    # Every supported deploy target gets smoke coverage: a cursor-specific
    # regression must not be able to ship unseen.
    assert "for tool in claude copilot codex cursor kiro" in ci_workflow
    assert "for tool in claude copilot codex cursor kiro" in release_validate
    assert "uv pip install" in ci_workflow
    assert "uv pip install" in release_validate
    assert "ai-playbook doctor --tool" in ci_workflow
    assert '"$venv/bin/ai-playbook" doctor --tool' in release_validate


def test_ci_runs_acceptance_suite_against_installed_wheel():
    """CLI-behaviour ATs must exercise the shipped artifact, not only the source tree.

    The suite splits in two: CLI-behaviour ATs (valid against the installed
    wheel) and repo-contract tests marked `repo_contract` (need repo-only
    files like .github/ and evals/ that are correctly not packaged). CI runs
    the wheel-valid subset inside the clean-venv wheel install, overriding
    pythonpath so the installed package is imported instead of src/.
    """
    ci_workflow = _workflow_text("ci.yml")
    assert "pytest tests/acceptance" in ci_workflow, (
        "ci.yml must run the acceptance suite against the installed wheel"
    )
    assert '-m "not repo_contract"' in ci_workflow, (
        "ci.yml wheel AT run must deselect repo-contract tests"
    )
    assert "-o pythonpath=" in ci_workflow, (
        "ci.yml wheel AT run must clear pythonpath so src/ does not shadow the wheel"
    )


def test_adr_index_in_readme_matches_adr_files():
    source_root = get_source_root()
    adr_dir = source_root / "docs" / "adr"
    adr_files = sorted(adr_dir.glob("[0-9][0-9][0-9][0-9]-*.md"))

    expected_lines: list[str] = []
    for path in adr_files:
        text = path.read_text()
        title_match = re.match(r"#\s+(ADR-\d{4}:\s+.+)", text)
        assert title_match, f"{path.name} must start with `# ADR-NNNN: <title>`"
        status_match = re.search(r"\|\s*\*\*Status\*\*\s*\|\s*([^|]+?)\s*\|", text)
        date_match = re.search(r"\|\s*\*\*Date\*\*\s*\|\s*([^|]+?)\s*\|", text)
        assert status_match, f"{path.name} must declare a Status row"
        assert date_match, f"{path.name} must declare a Date row"
        expected_lines.append(
            f"- [{title_match.group(1).strip()}]({path.name}): "
            f"{status_match.group(1).strip()}, {date_match.group(1).strip()}"
        )

    readme = (adr_dir / "README.md").read_text()
    index_match = re.search(
        r"## Index\n\n(?P<index>.*?)(?=\n\n>|$)",
        readme,
        flags=re.DOTALL,
    )
    assert index_match
    actual_index = index_match.group("index").strip()
    if expected_lines:
        assert actual_index == "\n".join(expected_lines)
    else:
        assert actual_index == "No ADRs are currently recorded."


def test_import_linter_template_shipped_and_cross_linked():
    source_root = get_source_root()
    template = source_root / "templates" / "importlinter-template.toml"
    body = template.read_text()

    assert template.exists()
    assert "[tool.importlinter]" in body
    assert 'type = "layers"' in body
    assert 'type = "forbidden"' in body
    assert "<root_package>" in body
    design_patterns = (source_root / "knowledge-base" / "design-patterns.md").read_text()
    assert "importlinter-template.toml" in design_patterns


def test_teachback_trailer_enforced_and_documented():
    source_root = get_source_root()

    hook = source_root / "harness" / "check-teachback.sh"
    body = hook.read_text()
    assert hook.exists()
    assert "Teach-back:" in body
    for skip_type in ("chore", "docs", "style", "build", "ci", "revert"):
        assert skip_type in body
    for require_type in ("feat", "fix", "refactor", "perf", "test"):
        assert require_type in body
    assert "CLAUDE_SKIP_TEACHBACK" in body

    pre_commit = (source_root / "harness" / "pre-commit-config.yaml").read_text()
    assert "check-teachback.sh" in pre_commit
    assert "commit-msg" in pre_commit
    # A plain `pre-commit install` must install the commit-msg stage too,
    # otherwise the teach-back gate is silently opt-in for adopters.
    assert "default_install_hook_types: [pre-commit, commit-msg]" in pre_commit

    # Both CI twins must backstop the commit-msg hook server-side: GitHub
    # never runs commit-msg hooks, so a commit-hygiene job replays
    # check-teachback.sh over the PR range in the repo's own CI AND in the
    # deployed adopter template.
    repo_ci = (source_root / ".github" / "workflows" / "ci.yml").read_text()
    shipped_ci = (source_root / "harness" / "ci.yml").read_text()
    for name, text in (("ci.yml", repo_ci), ("harness/ci.yml", shipped_ci)):
        assert "commit-hygiene:" in text, f"{name} must declare a commit-hygiene job"
        assert "harness/check-teachback.sh" in text, (
            f"{name} commit-hygiene must reuse the local commit-msg hook script"
        )
        assert "git rev-list --no-merges" in text, (
            f"{name} commit-hygiene must replay the check over the PR range"
        )

    git_skill = (source_root / "skills" / "git" / "SKILL.md").read_text()
    assert "teach-back trailer" in git_skill.lower()
    assert "Teach-back:" in git_skill

    claude_md = (source_root / "CLAUDE.md").read_text()
    assert "Teach-back trailer" in claude_md
    assert "check-teachback.sh" in claude_md

    paths_py = (source_root / "src" / "deploy_ai_playbook" / "paths.py").read_text()
    assert "check-teachback.sh" in paths_py


@pytest.mark.parametrize(
    ("name", "message", "expected_code", "stderr_fragment"),
    [
        ("missing", "fix(auth): patch token refresh\n", 1, "Missing final Teach-back trailer"),
        (
            "present",
            "fix(auth): patch token refresh\n\nTeach-back: token refresh lives in auth.\n",
            0,
            "",
        ),
        (
            "present-not-final",
            "fix(auth): patch token refresh\n\n"
            "Teach-back: token refresh lives in auth.\n\n"
            "More body text.\n",
            1,
            "final Teach-back trailer",
        ),
        ("docs-skip", "docs(readme): update wording\n", 0, ""),
        (
            # Claude Code appends Co-Authored-By by default; trailers after
            # Teach-back must stay legal (git trailer blocks are ordered-free).
            "trailing-coauthor",
            "fix(auth): patch token refresh\n\n"
            "Teach-back: token refresh lives in auth.\n"
            "Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>\n",
            0,
            "",
        ),
        (
            # `git commit -s` (DCO) appends Signed-off-by as the final line.
            "trailing-signoff",
            "feat(api): add endpoint\n\n"
            "Teach-back: handler lives in api/routes.py.\n"
            "Signed-off-by: Dev <dev@example.com>\n",
            0,
            "",
        ),
        (
            # `git commit -v` includes the staged diff below a scissors line;
            # diff lines are not part of the message and must be ignored.
            "verbose-scissors-diff",
            "fix(auth): patch token refresh\n\n"
            "Teach-back: token refresh lives in auth.\n"
            "# ------------------------ >8 ------------------------\n"
            "diff --git a/x b/x\n"
            "+plus line that is not a comment\n",
            0,
            "",
        ),
        ("fixup-skip", "fixup! fix(auth): patch token refresh\n", 0, ""),
        ("squash-skip", "squash! feat(api): add endpoint\n", 0, ""),
        (
            # A leading blank line must not bypass validation; git strips it
            # during cleanup, so the landed subject is still checked here.
            "blank-first-line",
            "\nfix(auth): patch token refresh\n",
            1,
            "Missing final Teach-back",
        ),
        ("breaking-missing", "feat!: change auth contract\n", 1, "Missing final Teach-back"),
        ("release-type", "release: cut v1.0.0\n", 1, "Unsupported commit type"),
        ("unknown-type", "wip: patch token refresh\n", 1, "Unsupported commit type"),
        ("bad-format", "fix token refresh\n", 1, "Unsupported commit message format"),
        ("generated-merge", "Merge branch 'main' into feature\n", 0, ""),
    ],
)
def test_teachback_hook_enforces_supported_commit_types(
    tmp_path: Path, name: str, message: str, expected_code: int, stderr_fragment: str
):
    """One case per commit-message shape: a failing case no longer masks the rest."""
    hook = get_source_root() / "harness" / "check-teachback.sh"
    message_file = tmp_path / name
    message_file.write_text(message)

    result = subprocess.run(  # noqa: S603 - test executes a repo-owned shell hook.
        ["/bin/sh", str(hook), str(message_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == expected_code, f"{name}: {result.stderr}"
    if stderr_fragment:
        assert stderr_fragment in result.stderr


def test_repo_contributor_hooks_enforce_teach_back_commit_messages():
    source_root = get_source_root()

    pre_commit = (source_root / ".pre-commit-config.yaml").read_text()
    assert "teach-back-trailer" in pre_commit
    assert "harness/check-teachback.sh" in pre_commit
    assert "commit-msg" in pre_commit

    contributing = (source_root / "CONTRIBUTING.md").read_text()
    assert "pre-commit install --hook-type commit-msg" in contributing


def _parse_pre_commit_repos(text: str) -> dict[str, dict[str, str]]:
    """Map repo URL → {sha, hooks-csv} for a pre-commit config.

    Hand-written parser rather than YAML so the SHA-pinning comments stay
    visible in the assertion failure when something drifts.
    """
    repos: dict[str, dict[str, str]] = {}
    current_url: str | None = None
    current_sha: str | None = None
    current_hooks: list[str] = []
    for raw in text.splitlines():
        url_match = re.match(r"\s*-\s*repo:\s*(\S+)", raw)
        if url_match:
            if current_url is not None:
                repos[current_url] = {
                    "sha": current_sha or "",
                    "hooks": ",".join(current_hooks),
                }
            current_url = url_match.group(1)
            current_sha = None
            current_hooks = []
            continue
        rev_match = re.match(r"\s*rev:\s*(\S+)", raw)
        if rev_match and current_url is not None:
            current_sha = rev_match.group(1)
            continue
        hook_match = re.match(r"\s*-\s*id:\s*(\S+)", raw)
        if hook_match and current_url is not None:
            current_hooks.append(hook_match.group(1))
    if current_url is not None:
        repos[current_url] = {
            "sha": current_sha or "",
            "hooks": ",".join(current_hooks),
        }
    return repos


def test_security_pre_commit_hooks_share_pinned_sha_across_repo_and_harness():
    """STRUCTURE-MARKER: security-critical hooks must pin to the SAME SHA on both sides.

    Two pre-commit configs ship in this repo:
      - `.pre-commit-config.yaml` runs locally for repo contributors and in CI.
      - `harness/pre-commit-config.yaml` is the starter hook config the CLI
        deploys to adopter projects.

    Adopters who install the deployed harness must get the same secret-scan
    coverage as repo contributors. If `.pre-commit-config.yaml` bumps gitleaks
    to a newer pinned SHA but `harness/` lags, every adopter silently runs
    older rules. This test makes that drift loud.

    Scope is intentionally narrow: only the security-critical repos are pinned
    to identical SHAs:
      - `gitleaks` (secret detection)
      - `pre-commit/pre-commit-hooks` (provides `detect-private-key`)
      - `shellcheck-py` (shell-script vulnerability detection)

    Other shared repos (markdownlint-cli2) may legitimately diverge if one
    side wants stricter rules.
    """
    source_root = get_source_root()
    repo_side = _parse_pre_commit_repos((source_root / ".pre-commit-config.yaml").read_text())
    harness_side = _parse_pre_commit_repos(
        (source_root / "harness" / "pre-commit-config.yaml").read_text()
    )

    security_critical_repos = (
        "https://github.com/gitleaks/gitleaks",
        "https://github.com/pre-commit/pre-commit-hooks",
        "https://github.com/shellcheck-py/shellcheck-py",
    )

    failures: list[str] = []
    for url in security_critical_repos:
        repo_entry = repo_side.get(url)
        harness_entry = harness_side.get(url)
        if repo_entry is None:
            failures.append(f"{url} missing from .pre-commit-config.yaml")
            continue
        if harness_entry is None:
            failures.append(f"{url} missing from harness/pre-commit-config.yaml")
            continue
        if repo_entry["sha"] != harness_entry["sha"]:
            failures.append(
                f"{url}: repo={repo_entry['sha']} but harness={harness_entry['sha']} "
                "(security-critical hooks must pin identically)"
            )

    assert not failures, "Pre-commit security-hook drift:\n  " + "\n  ".join(failures)


def test_pre_commit_parser_handles_synthetic_input():
    """Self-test for the hand-written pre-commit parser used above."""
    sample = """
repos:
  - repo: https://example.com/foo
    rev: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  # frozen: v1.0
    hooks:
      - id: foo
      - id: foo-extra
  - repo: https://example.com/bar
    rev: bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
    hooks:
      - id: bar
"""
    parsed = _parse_pre_commit_repos(sample)
    assert parsed["https://example.com/foo"]["sha"].startswith("a" * 8)
    assert parsed["https://example.com/foo"]["hooks"] == "foo,foo-extra"
    assert parsed["https://example.com/bar"]["sha"].startswith("b" * 8)


def test_repo_quality_contract_has_makefile_entrypoint():
    source_root = get_source_root()
    makefile = (source_root / "Makefile").read_text()

    for target in (
        "quality",
        "format",
        "format-check",
        "lint",
        "typecheck",
        "test",
        "shellcheck",
        "docs-lint",
        "security",
        "eval-structure",
        "eval-calibrate",
    ):
        assert re.search(rf"^{target}:", makefile, re.MULTILINE), (
            f"Makefile missing documented target: {target}"
        )

    # CONTRACT-PHRASE: pinned commands the project quality contract depends on.
    # Re-wording (e.g. switching to `uv run python -m pytest`) is a deliberate
    # change to the Makefile contract; it should update the test in the same PR.
    assert "uv run pytest tests/" in makefile
    assert "PRE_COMMIT := uvx pre-commit==4.3.0" in makefile
    assert "$(PRE_COMMIT) run markdownlint-cli2" in makefile
    assert "$(PRE_COMMIT) run vale" in makefile
    assert "evals/run_eval.py check-structure" in makefile
    assert "shellcheck" in makefile
    assert "harness/check-teachback.sh harness/telemetry.sh" in makefile
    assert (
        "uvx --python 3.12 pip-audit==2.10.0 --strict --requirement /tmp/runtime-requirements.txt"
    ) in makefile


def test_wheel_force_include_matches_harness_files_contract():
    """Wheel ships exactly the harness files HARNESS_FILES enumerates.

    Without explicit per-file includes, anything dropped into harness/ would
    silently end up in every adopter's wheel. Pinning to the contract keeps
    repo-internal helpers (e.g. tools/) from leaking into shipped data.
    """
    source_root = get_source_root()
    pyproject = tomllib.loads((source_root / "pyproject.toml").read_text())
    force_include = pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]

    shipped_harness_keys = {key for key in force_include if key.startswith("harness/")}
    expected_keys = {f"harness/{src_name}" for src_name in HARNESS_FILES}

    assert shipped_harness_keys == expected_keys, (
        f"force-include drift: shipped={shipped_harness_keys} expected={expected_keys}. "
        f"Update both pyproject.toml [tool.hatch.build.targets.wheel.force-include] and "
        f"src/deploy_ai_playbook/paths.py HARNESS_FILES together."
    )


def test_repo_shellchecks_shipped_harness_scripts_in_hooks_and_ci():
    source_root = get_source_root()
    pre_commit = (source_root / ".pre-commit-config.yaml").read_text()
    workflow = (source_root / ".github" / "workflows" / "ci.yml").read_text()

    assert "shellcheck-py" in pre_commit
    assert "id: shellcheck" in pre_commit
    assert "ShellCheck harness scripts" in workflow
    assert "run shellcheck --all-files" in workflow


def test_secrets_scanning_shipped_and_documented():
    source_root = get_source_root()
    repo_pre_commit = (source_root / ".pre-commit-config.yaml").read_text()
    assert "gitleaks" in repo_pre_commit
    assert "detect-private-key" in repo_pre_commit

    pre_commit = (source_root / "harness" / "pre-commit-config.yaml").read_text()
    assert "gitleaks" in pre_commit
    assert "detect-private-key" in pre_commit

    shipped_ci = (source_root / "harness" / "ci.yml").read_text()
    assert "Universal repository checks" in shipped_ci
    assert "python -m pre_commit run --all-files" in shipped_ci

    ci_workflow = (source_root / ".github" / "workflows" / "ci.yml").read_text()
    assert "pre-commit==" in ci_workflow
    assert "run gitleaks --all-files" in ci_workflow
    assert "run detect-private-key --all-files" in ci_workflow
    assert "uvx --python 3.12 pip-audit==2.10.0" in ci_workflow

    security_md = (source_root / "knowledge-base" / "security.md").read_text()
    assert "gitleaks" in security_md
    assert "pre-commit" in security_md.lower()


def test_changelog_has_unreleased_section_and_current_version():
    """`CHANGELOG.md` must have an `[Unreleased]` block AND a versioned heading
    matching `pyproject.toml`'s `version = "..."` line.

    Catches the two most common release-prep gaps:

    * `[Unreleased]` was removed (so post-release commits land without a
      capture target),
    * the version was bumped in `pyproject.toml` without renaming the
      `[Unreleased]` block to `[X.Y.Z] - YYYY-MM-DD`.

    Both are easy to forget in a hotfix; both regress the changelog as a
    contract surface for adopters tracking the deprecation cycle.
    """
    source_root = get_source_root()
    changelog = (source_root / "CHANGELOG.md").read_text(encoding="utf-8")

    # STRUCTURE-MARKER: Keep-a-Changelog requires the [Unreleased] heading shape.
    assert re.search(r"^## \[Unreleased\]", changelog, re.MULTILINE), (
        "CHANGELOG.md must contain a `## [Unreleased]` section — every release "
        "renames the prior Unreleased block to `[X.Y.Z]` and creates a fresh one."
    )

    pyproject_text = (source_root / "pyproject.toml").read_text(encoding="utf-8")
    version_match = re.search(r'^version\s*=\s*"([^"]+)"', pyproject_text, re.MULTILINE)
    assert version_match, 'pyproject.toml must declare `version = "X.Y.Z"`'
    current = version_match.group(1)

    assert re.search(rf"^## \[{re.escape(current)}\]", changelog, re.MULTILINE), (
        f"pyproject.toml version is {current} but CHANGELOG.md has no `## [{current}]` "
        f"section. Either the version bump is wrong or the CHANGELOG was not updated. "
        f"Rename `## [Unreleased]` to `## [{current}] - YYYY-MM-DD` and add a fresh "
        f"`## [Unreleased]` block."
    )


def test_changelog_skills_line_matches_shipped_skills():
    """Every skill in skills/ must be named in the latest released CHANGELOG section.

    The skill directory is the source of truth for what ships in the wheel
    (the wheel force-include `skills` is a tree copy). When a new skill
    lands without being added to the CHANGELOG, adopters reading the release
    notes get an undocumented surface. This test catches that drift the way
    Section-1 found it (intent-interview was missing from the 1.0.0 line).

    The test inspects the latest released `## [X.Y.Z]` section, not
    `## [Unreleased]`, so changes-in-flight don't have to mention the skill
    until release time. To re-tag, add the new skill name to the latest
    versioned `### Added` "Skills:" line.
    """
    source_root = get_source_root()
    shipped = {
        d.name
        for d in (source_root / "skills").iterdir()
        if d.is_dir() and (d / "SKILL.md").exists()
    }

    changelog = (source_root / "CHANGELOG.md").read_text(encoding="utf-8")
    # Latest released section: starts after "## [Unreleased]" and matches
    # the first "## [X.Y.Z] - YYYY-MM-DD" heading.
    released_match = re.search(
        r"^## \[\d+\.\d+\.\d+\][^\n]*\n(.*?)(?=^## \[|\Z)",
        changelog,
        re.DOTALL | re.MULTILINE,
    )
    assert released_match, "CHANGELOG.md must contain at least one released `## [X.Y.Z]` section"
    released_body = released_match.group(1)

    # Find the Skills: line inside that release.
    # STRUCTURE-MARKER: pinned `- Skills:` line shape; the comma-list content
    # is computed from skills/ tree and is allowed to evolve.
    skills_line = re.search(r"^- Skills:\s*([^\n]+)$", released_body, re.MULTILINE)
    assert skills_line, (
        "Latest released CHANGELOG section must contain a `- Skills: <comma list>` line"
    )
    documented = {name.strip() for name in skills_line.group(1).split(",") if name.strip()}
    missing = shipped - documented
    extra = documented - shipped
    assert not missing and not extra, (
        f"CHANGELOG skill list drifted from skills/ tree:\n"
        f"  shipped but undocumented: {sorted(missing)}\n"
        f"  documented but not shipped: {sorted(extra)}\n"
        f'Update the latest released `### Added` "Skills:" line in CHANGELOG.md.'
    )


def test_pre_commit_revs_are_pinned_to_full_commit_shas():
    """pre-commit `rev:` is a git ref: a moved tag swaps the hook silently.

    Pin to 40-char SHAs (use `pre-commit autoupdate --freeze`) so the same
    supply-chain hardening that applies to GitHub Actions also applies to
    locally-installed hooks. Repo and shipped harness configs are both checked.
    """
    source_root = get_source_root()
    rev_re = re.compile(r"^\s*rev:\s*([^\s#]+)", re.MULTILINE)
    for relpath in (".pre-commit-config.yaml", "harness/pre-commit-config.yaml"):
        text = (source_root / relpath).read_text()
        revs = rev_re.findall(text)
        assert revs, f"{relpath} declares no rev: lines"
        for rev in revs:
            assert FULL_SHA_RE.fullmatch(rev), (
                f"{relpath}: rev {rev!r} is not a full 40-char SHA. "
                f"Run `pre-commit autoupdate --freeze` to lock all revs."
            )


def test_release_validate_runs_security_scans():
    """Release path runs the same security scans as PR CI.

    A tag push triggers release.yml, not ci.yml. Without these checks in the
    release validate job, a vulnerable dep or Bandit finding could ship even
    when the human pre-release checklist is skipped.
    """
    workflow = _workflow_text("release.yml")
    validate = _workflow_job(workflow, "validate")

    assert "pip-audit==" in validate, "release validate must run pinned pip-audit"
    assert "uvx --python 3.12 pip-audit==2.10.0" in validate, (
        "release validate pip-audit must use the supported Python runtime"
    )
    assert "--strict" in validate, "release validate pip-audit must use --strict"
    assert "bandit==" in validate, "release validate must run pinned bandit"
    assert "run gitleaks --all-files" in validate, (
        "release validate must run gitleaks via pre-commit"
    )
    assert "run detect-private-key --all-files" in validate, (
        "release validate must run detect-private-key via pre-commit"
    )


def test_eval_drift_workflow_is_least_privilege_and_scans_dependencies():
    """eval-drift is opt-in (manual dispatch) and pulls a secret: keep its surface small."""
    workflow = _workflow_text("eval-drift.yml")
    judge = _workflow_job(workflow, "judge")

    # Workflow-level ceiling.
    assert re.search(r"^permissions:\n\s+contents:\s+read", workflow, re.MULTILINE), (
        "eval-drift.yml must declare top-level permissions: contents: read"
    )
    # Job-level reaffirmation is defence-in-depth: the same pattern other
    # workflows in this repo use.
    assert re.search(r"^\s+permissions:\n\s+contents:\s+read", judge, re.MULTILINE), (
        "eval-drift.yml judge job must restate permissions: contents: read"
    )
    # The drift run must run pip-audit so a manual drift check also catches new CVEs in deps.
    assert "pip-audit==" in judge, "eval-drift must run pinned pip-audit when the drift job runs"
    assert "uvx --python 3.12 pip-audit==2.10.0" in judge, (
        "eval-drift pip-audit must use the supported Python runtime"
    )
    # ANTHROPIC_API_KEY must only be referenced where it is actually used:
    # the detection step must NOT inject it into env (would widen the surface
    # any future change to the detection step has to be reviewed against).
    detection_step_re = re.compile(
        r"name:\s+Check for ANTHROPIC_API_KEY.*?(?=- name:|\Z)", re.DOTALL
    )
    detection = detection_step_re.search(judge)
    assert detection, "eval-drift judge must contain a detection step"
    assert "ANTHROPIC_API_KEY:" not in detection.group(0), (
        "Detection step must not bind ANTHROPIC_API_KEY into env — only the "
        "judge step needs the secret. Use a presence-only sentinel instead."
    )
    assert "exit 1" in detection.group(0), (
        "eval-drift must fail closed when the semantic judge secret is missing"
    )


def test_mutation_testing_is_dedicated_baseline_regression_gate():
    ci_workflow = _workflow_text("ci.yml")
    mutation_workflow = _workflow_text("mutation.yml")

    assert "mutation-test:" not in ci_workflow
    assert "continue-on-error" not in mutation_workflow
    assert "pull_request:" in mutation_workflow
    assert "paths:" in mutation_workflow
    assert "src/deploy_ai_playbook/**" in mutation_workflow
    assert "schedule:" in mutation_workflow
    assert "run: make mutation" in mutation_workflow
    makefile = _repo_file("Makefile").read_text()
    assert "mutation:" in makefile
    assert "rm -rf mutants" in makefile
    assert "mutmut run --max-children 4" in makefile
    assert "mutmut export-cicd-stats" in makefile
    assert "tools/check-mutation-baseline.py" in makefile

    baseline = json.loads(_repo_file("mutation-baseline.json").read_text(encoding="utf-8"))
    # Runner speed can reclassify timeouts as survivors, so quality is ratcheted
    # on their combined rate while timeout retains an infrastructure ceiling.
    # A rate keeps source growth from becoming an automatic regression.
    # STRUCTURE-MARKER: pin the schema shape, not the ratchet values: those
    # legitimately move when the baseline is regenerated (a two-place ratchet
    # is exactly the drift class this file polices elsewhere).
    assert baseline["version"] == 3
    assert isinstance(baseline["thresholds"]["max_unresolved_basis_points"], int)
    assert "max_survived" not in baseline["thresholds"]
    assert isinstance(baseline["thresholds"]["max_timeout"], int)
    assert baseline["thresholds"]["max_segfault"] == 0

    pyproject = tomllib.loads(_repo_file("pyproject.toml").read_text(encoding="utf-8"))
    mutmut_config = pyproject["tool"]["mutmut"]
    for required_copy in (
        "agents/",
        "knowledge-base/",
        "tools/",
        ".deprecations.toml",
        "mutation-baseline.json",
    ):
        assert required_copy in mutmut_config["also_copy"]
    assert "--ignore=tests/unit/test_architecture.py" in mutmut_config["pytest_add_cli_args"]


def test_generated_wheels_are_not_kept_at_repo_root():
    source_root = get_source_root()

    assert not sorted(path.name for path in source_root.glob("*.whl"))
    assert "*.whl" in (source_root / ".gitignore").read_text(encoding="utf-8")


def test_repo_gitignore_covers_artifact_dirs_and_deploy_surfaces():
    """Dogfooding must not leak artifacts: every workflow artifact directory
    (canonical list: services/artifacts.ARTIFACT_DIRECTORIES) and every
    root-level deploy surface of every tool must be ignored in this repo."""
    from deploy_ai_playbook.paths import TOOL_DESTINATIONS
    from deploy_ai_playbook.services.artifacts import ARTIFACT_DIRECTORIES

    gitignore = (get_source_root() / ".gitignore").read_text(encoding="utf-8")
    lines = {line.strip().rstrip("/") for line in gitignore.splitlines()}

    for directory in ARTIFACT_DIRECTORIES:
        assert directory in lines, f".gitignore must ignore workflow artifact dir {directory}/"

    # Surfaces a self-deploy would create. Ignored either at the root
    # segment (`.codex`) or as a full path (`.github/agents`: `.github`
    # itself must stay tracked for workflows). Root rules files are the
    # exception: CLAUDE.md is the canonical source and AGENTS.md is the
    # tracked hand-written bridge to it, so both stay tracked.
    for destinations in TOOL_DESTINATIONS.values():
        for destination in destinations.values():
            if destination in {"CLAUDE.md", "AGENTS.md"}:
                continue
            root_segment = destination.split("/", 1)[0]
            assert root_segment in lines or destination.rstrip("/") in lines, (
                f".gitignore must ignore deploy surface {destination} (root segment or full path)"
            )


def test_harness_security_template_is_shipped_and_hardened():
    """harness/security.yml ships to adopters, so it must meet the same bar."""
    source_root = get_source_root()
    template = source_root / "harness" / "security.yml"
    assert template.exists(), "harness/security.yml must exist for adopters to drop in"
    text = template.read_text()

    # Top-level least privilege; per-job elevation only where required.
    assert re.search(r"^permissions:\n\s+contents:\s+read", text, re.MULTILINE), (
        "harness/security.yml must declare top-level permissions: contents: read"
    )
    # Required job set: CodeQL + Scorecard + secret scan + dependency review.
    for job_name in ("codeql", "scorecard", "gitleaks", "dependency-review"):
        assert re.search(rf"^  {job_name}:", text, re.MULTILINE), (
            f"harness/security.yml must declare a {job_name!r} job"
        )
    # Every uses: line must be SHA-pinned (mirrors the test for GitHub Actions
    # in this repo's own workflows; the deployed file must match).
    for line_number, action_ref in _uses_entries(template):
        if action_ref.startswith("./"):
            continue
        assert "@" in action_ref, f"security.yml:{line_number} {action_ref} has no @ref"
        ref = action_ref.rsplit("@", 1)[1]
        assert FULL_SHA_RE.fullmatch(ref), (
            f"security.yml:{line_number} {action_ref} must be SHA-pinned"
        )
    # Checkout safety mirrors the rest of the repo.
    assert "persist-credentials: false" in text

    # Wired into HARNESS_FILES + wheel force-include so adopters actually get it.
    paths_py = (source_root / "src" / "deploy_ai_playbook" / "paths.py").read_text()
    assert '"security.yml"' in paths_py, (
        "src/deploy_ai_playbook/paths.py HARNESS_FILES must enumerate security.yml"
    )
    pyproject = (source_root / "pyproject.toml").read_text()
    assert '"harness/security.yml"' in pyproject, (
        "pyproject.toml [tool.hatch.build.targets.wheel.force-include] must "
        "ship harness/security.yml"
    )

    # security.yml's header claims Dependabot updates the pinned SHAs weekly:

    # the deployed dependabot.yml is what makes that claim true.
    dependabot = source_root / "harness" / "dependabot.yml"
    assert dependabot.exists(), "harness/dependabot.yml must ship alongside security.yml"
    dependabot_text = dependabot.read_text()
    assert "package-ecosystem: github-actions" in dependabot_text
    assert "interval: weekly" in dependabot_text
    assert '"dependabot.yml": ".github/dependabot.yml"' in paths_py, (
        "src/deploy_ai_playbook/paths.py HARNESS_FILES must map dependabot.yml "
        "to .github/dependabot.yml"
    )


def test_playbook_professional_language_lint_is_enforced():
    """Vale is wired into pre-commit + CI and the Playbook style pack is loaded.

    Word-list contents (banned phrases, role labels, contractions) live in the
    YAML rule files themselves. The test does not duplicate them: that would
    couple the suite to editorial decisions and force two-place edits whenever
    the style guide changes.
    """
    source_root = get_source_root()

    pre_commit = (source_root / ".pre-commit-config.yaml").read_text()
    assert "id: vale" in pre_commit
    assert "vale --minAlertLevel=error" in pre_commit

    ci_workflow = (source_root / ".github" / "workflows" / "ci.yml").read_text()
    assert "docs-quality:" in ci_workflow
    assert "go install github.com/errata-ai/vale" in ci_workflow
    assert "Documentation lint" in ci_workflow and "make docs-lint" in ci_workflow

    vale_ini = (source_root / ".vale.ini").read_text()
    assert "[*.md]" in vale_ini
    assert "[evals/*.md]" in vale_ini

    playbook_style = source_root / ".vale" / "styles" / "Playbook"
    required_rules = {
        "ProfessionalTone.yml": "error",
        "DisplayNames.yml": "error",
        "NoEmDash.yml": "error",
    }
    for rule, expected_level in required_rules.items():
        rule_path = playbook_style / rule
        assert rule_path.exists(), f"missing Vale rule: {rule}"
        body = rule_path.read_text()
        assert f"level: {expected_level}" in body, (
            f"{rule} must be enforced at level={expected_level}"
        )

    # Contractions are allowed: Microsoft and Google style guides both
    # recommend them for natural prose, so the playbook carries no rule
    # against them.
    assert not (playbook_style / "Contractions.yml").exists(), (
        "Contractions rule was retired (Microsoft/Google style guides "
        "recommend contractions); do not reintroduce it"
    )


def test_release_publishes_only_after_signing_succeeds():
    release_workflow = (get_source_root() / ".github" / "workflows" / "release.yml").read_text()
    sign_pos = release_workflow.find("sign:\n")
    publish_pos = release_workflow.find("publish-pypi:\n")

    assert sign_pos != -1
    assert publish_pos != -1
    assert sign_pos < publish_pos
    assert "needs: sign" in release_workflow[publish_pos:]


def test_release_workflow_creates_release_before_uploading_artifacts():
    release_workflow = (get_source_root() / ".github" / "workflows" / "release.yml").read_text()
    create_pos = release_workflow.find("gh release create")
    upload_pos = release_workflow.find("gh release upload")

    assert create_pos != -1
    assert upload_pos != -1
    assert create_pos < upload_pos


def test_eval_drift_has_standard_agent_baselines():
    source_root = get_source_root()
    samples_dir = source_root / "evals" / "samples"

    missing = [agent for agent in ALL_AGENTS if not (samples_dir / f"{agent}.md").exists()]
    assert missing == []

    workflow = (source_root / ".github" / "workflows" / "eval-drift.yml").read_text()
    assert "Check committed baselines" in workflow
    assert "evals/run_eval.py validate-samples" in workflow


# Variables through which a parent make or shell can leak overrides into
# the sandboxed runs: STACK itself, plus make's own channels (MAKEFLAGS
# carries command-line overrides such as `make test STACK=weird`;
# MAKEFILES injects extra include files).
_MAKE_LEAK_VARS = ("STACK", "MAKEFLAGS", "MFLAGS", "GNUMAKEFLAGS", "MAKEFILES", "MAKELEVEL")


def _run_harness_make(
    tmp_path: Path, *goals: str, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the shipped harness Makefile inside a sandbox directory.

    The Makefile is copied into the sandbox so stack-sentinel files
    (pyproject.toml, go.mod, ...) and Makefile.local are fully controlled
    by each test. Goals run with -n so no real toolchain executes.
    Hermetic env: make-override channels are stripped so a developer or
    CI matrix exporting STACK (directly or via MAKEFLAGS) cannot change
    what these sandboxes observe; tests opt back in via env_overrides.
    """
    make = shutil.which("make")
    assert make, "make is required to test the harness Makefile"
    shutil.copy(get_source_root() / "harness" / "Makefile", tmp_path / "Makefile")
    env = {k: v for k, v in os.environ.items() if k not in _MAKE_LEAK_VARS}
    env.update(env_overrides or {})
    return subprocess.run(  # noqa: S603 - test executes make on a repo-owned Makefile.
        [make, "-f", "Makefile", "-n", *goals],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_makefile_local_rescues_unknown_stack(tmp_path: Path):
    """The documented escape hatch must work: on an unrecognised stack,
    a Makefile.local defining STACK and the command vars wins over
    detection, and the unknown-stack parse error must not fire."""
    (tmp_path / "Makefile.local").write_text(
        "STACK := custom\n"
        "FORMAT_CMD := echo format\n"
        "FORMAT_CHECK_CMD := echo format-check\n"
        "LINT_CMD := echo lint\n"
        "TYPECHECK_CMD := echo typecheck\n"
        "TEST_CMD := echo test\n"
    )

    result = _run_harness_make(tmp_path, "quality")

    assert "Cannot continue without a known stack" not in result.stderr
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"


def test_stack_detection_still_selects_known_stack(tmp_path: Path):
    """A recognised sentinel keeps working exactly as before the override
    reordering: detection picks the stack and wires its commands."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sandbox'\n")

    result = _run_harness_make(tmp_path, "help")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Detected stack: python" in result.stdout
    assert "uv run ruff format" in result.stdout


def test_makefile_local_partial_override_wins_on_recognised_stack(tmp_path: Path):
    """A Makefile.local that overrides only some command vars must win on
    a recognised stack too: the documented contract is "override any
    *_CMD in Makefile.local", not "override only with a full set"."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sandbox'\n")
    (tmp_path / "Makefile.local").write_text("FORMAT_CMD := echo custom-format\n")

    result = _run_harness_make(tmp_path, "format")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "echo custom-format" in result.stdout
    assert "ruff format ." not in result.stdout


def test_environment_stack_variable_does_not_bypass_detection(tmp_path: Path):
    """Only a Makefile.local assignment may short-circuit detection: an
    inherited STACK environment variable (a common CI matrix name) must
    leave sentinel detection in charge."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sandbox'\n")

    result = _run_harness_make(tmp_path, "help", env_overrides={"STACK": "weird"})

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Detected stack: python" in result.stdout


def test_makefile_local_conditional_stack_stays_inert_on_recognised_stack(tmp_path: Path):
    """A defensive `STACK ?= custom` in Makefile.local must stay a no-op
    when detection recognises the stack: detection assigns first, so the
    conditional never fires and the detected commands stay wired."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sandbox'\n")
    (tmp_path / "Makefile.local").write_text("STACK ?= custom\n")

    result = _run_harness_make(tmp_path, "help")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "Detected stack: python" in result.stdout
    assert "uv run ruff format" in result.stdout


def test_makefile_local_append_applies_once(tmp_path: Path):
    """`TEST_CMD += --verbose` in Makefile.local must append exactly once:
    the override file is included a single time, so appended values never
    double."""
    (tmp_path / "Makefile.local").write_text(
        "STACK := custom\n"
        "FORMAT_CMD := echo format\n"
        "FORMAT_CHECK_CMD := echo format-check\n"
        "LINT_CMD := echo lint\n"
        "TYPECHECK_CMD := echo typecheck\n"
        "TEST_CMD := echo test\n"
        "TEST_CMD += --verbose\n"
    )

    result = _run_harness_make(tmp_path, "test")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "echo test --verbose" in result.stdout
    assert "--verbose --verbose" not in result.stdout


def test_makefile_local_custom_target_parses_without_warnings(tmp_path: Path):
    """Convenience targets defined in Makefile.local must not produce
    'overriding commands' warnings: the override file is parsed once."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'sandbox'\n")
    (tmp_path / "Makefile.local").write_text("mytarget:\n\t@echo custom\n")

    result = _run_harness_make(tmp_path, "help")

    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    assert "overriding commands" not in result.stderr


def test_unknown_stack_without_override_still_fails_with_guidance(tmp_path: Path):
    """No sentinel and no Makefile.local: the parse-time error must stay,
    and it must keep pointing adopters at the Makefile.local escape hatch."""
    result = _run_harness_make(tmp_path, "quality")

    assert result.returncode != 0
    assert "Cannot continue without a known stack" in result.stderr
    combined = result.stdout + result.stderr
    assert "set STACK and *_CMD vars in Makefile.local" in combined


def test_shellcheck_disables_carry_justification():
    """No suppression without justification: every `shellcheck disable`
    pragma in the harness scripts needs an adjacent comment saying why
    the rule is safe to silence here."""
    failures: list[str] = []
    for script in sorted((get_source_root() / "harness").glob("*.sh")):
        lines = script.read_text().splitlines()
        for line_number, line in enumerate(lines, start=1):
            if "shellcheck disable" not in line:
                continue
            preceding = lines[line_number - 2].strip() if line_number >= 2 else ""
            has_comment_above = preceding.startswith("#") and "shellcheck" not in preceding
            has_inline_reason = bool(re.search(r"disable=\S+\s+#\s*\S", line))
            if not (has_comment_above or has_inline_reason):
                failures.append(f"{script.name}:{line_number}: {line.strip()}")

    assert not failures, "shellcheck disable without justification comment:\n  " + "\n  ".join(
        failures
    )


def test_telemetry_script_declares_privacy_minimal_schema():
    source_root = get_source_root()
    script = (source_root / "harness" / "telemetry.sh").read_text()

    assert "Never stores or transmits session IDs" in script
    assert "{timestamp:$timestamp,source:$source,turns:$turns,active_agent:$active_agent}" in script

    status_cmd = (source_root / "commands" / "status.md").read_text()
    assert "<timestamp>  <source>  <agent>  turns=<N>" in status_cmd
    assert ".claude/usage.jsonl" in status_cmd
    assert ".codex/usage.jsonl" in status_cmd
    assert "<model>" not in status_cmd
    assert "cache_r=" not in status_cmd


def test_telemetry_script_writes_jsonl_usage_event(tmp_path: Path):
    script = get_source_root() / "harness" / "telemetry.sh"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}

    result = subprocess.run(  # noqa: S603 - test executes a repo-owned shell script.
        ["/bin/sh", str(script)],
        input='{"session_id":"session-123"}',
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    usage_log = tmp_path / ".claude" / "usage.jsonl"
    event = json.loads(usage_log.read_text().strip())
    assert set(event) == {"timestamp", "source", "turns", "active_agent"}
    assert event["source"] == "claude"
    assert event["turns"] == 0
    assert "session-123" not in usage_log.read_text()


def test_telemetry_script_prefers_active_agent_marker_over_heuristic(tmp_path: Path):
    """The deterministic `Active agent:` marker beats the
    fuzzy "Use <agent>" phrase grep, and the most recent marker wins."""
    script = get_source_root() / "harness" / "telemetry.sh"
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps({"type": "user", "message": "please Use story-refiner for this"}),
                json.dumps({"type": "assistant", "message": "Active agent: story-refiner"}),
                json.dumps({"type": "assistant", "message": "Active agent: diff-reviewer"}),
            ]
        )
        + "\n"
    )
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}

    result = subprocess.run(  # noqa: S603 - test executes a repo-owned shell script.
        ["/bin/sh", str(script)],
        input=json.dumps({"session_id": "s1", "transcript_path": str(transcript)}),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    event = json.loads((tmp_path / ".claude" / "usage.jsonl").read_text().strip())
    assert event["active_agent"] == "diff-reviewer"


def test_telemetry_script_does_not_persist_sensitive_transcript_fields(tmp_path: Path):
    if shutil.which("jq") is None:
        pytest.skip("jq is required for transcript field handling")

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "type": "user",
                        "message": {"content": "please use the story-refiner agent"},
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "model": "claude-a",
                            "usage": {
                                "input_tokens": 3,
                                "output_tokens": 7,
                                "cache_creation_input_tokens": 1,
                                "cache_read_input_tokens": 2,
                            },
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "assistant",
                        "message": {
                            "model": "claude-b",
                            "usage": {
                                "input_tokens": 5,
                                "output_tokens": 4,
                                "cache_creation_input_tokens": 0,
                                "cache_read_input_tokens": 6,
                            },
                        },
                    }
                ),
            ]
        )
        + "\n"
    )

    script = get_source_root() / "harness" / "telemetry.sh"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    payload = json.dumps({"session_id": "session-123", "transcript_path": str(transcript)})

    result = subprocess.run(  # noqa: S603 - test executes a repo-owned shell script.
        ["/bin/sh", str(script)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    event = json.loads((tmp_path / ".claude" / "usage.jsonl").read_text().strip())
    assert set(event) == {"timestamp", "source", "turns", "active_agent"}
    assert event["turns"] == 3
    assert event["active_agent"] == "story-refiner"
    serialized = json.dumps(event)
    for sensitive in ("session-123", "claude-a", "claude-b", "input_tokens", "output_tokens"):
        assert sensitive not in serialized


def test_telemetry_script_ignores_hostile_sensitive_payload_fields(tmp_path: Path):
    if shutil.which("jq") is None:
        pytest.skip("jq is required for telemetry event writing")

    script = get_source_root() / "harness" / "telemetry.sh"
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(tmp_path)}
    payload = json.dumps({"session_id": 'session-"quoted"\nnext'})

    result = subprocess.run(  # noqa: S603 - test executes a repo-owned shell script.
        ["/bin/sh", str(script)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    lines = (tmp_path / ".claude" / "usage.jsonl").read_text().splitlines()
    assert len(lines) == 1
    event = json.loads(lines[0])
    assert set(event) == {"timestamp", "source", "turns", "active_agent"}
    assert 'session-"quoted"\nnext' not in lines[0]


def test_workspace_overlay_wired_into_story_template_and_kb():
    source_root = get_source_root()

    story_template = (source_root / "templates" / "story-template.md").read_text()
    assert re.search(r"^workspace:\s*$|^workspace:\s+", story_template, re.MULTILINE)

    overlay_readme = source_root / "knowledge-base" / "workspaces" / "README.md"
    overlay_text = overlay_readme.read_text()
    assert overlay_readme.exists()
    assert "load_when:" in overlay_text
    assert "Precedence" in overlay_text

    claude_md = (source_root / "CLAUDE.md").read_text()
    assert "knowledge-base/workspaces/" in claude_md

    index = (source_root / "knowledge-base" / "INDEX.md").read_text()
    assert "workspaces/README.md" in index


# Terminology lints (e.g. "refine" vs "grill") live in Vale rules
# (.vale/styles/Playbook/), not in the test suite. Prose policing in pytest
# fights legitimate copy-edits and duplicates the configured docs linter.


def test_teachback_type_lists_stay_in_sync_between_hook_and_git_skill():
    """The commit-type lists must match between mechanism and canon.

    The required/skip type lists were enumerated in three docs
    plus the hook. Consolidation left exactly two copies: the enforcing hook
    (harness/check-teachback.sh) and the canonical doc home
    (skills/git/SKILL.md § Teach-back Trailer). This pin keeps them identical;
    every other file cites the skill section instead of enumerating.
    """
    source_root = get_source_root()
    hook = (source_root / "harness" / "check-teachback.sh").read_text(encoding="utf-8")
    skill = (source_root / "skills" / "git" / "SKILL.md").read_text(encoding="utf-8")

    # STRUCTURE-MARKER: the case-arm type lists are the hook's contract;
    # the subject-line merge/revert arm has brackets and never matches.
    arms = re.findall(r"^\s+([a-z]+(?:\|[a-z]+)+)\)$", hook, re.MULTILINE)
    arm_sets = [set(arm.split("|")) for arm in arms]
    hook_required = next((s for s in arm_sets if "feat" in s), None)
    hook_skipped = next((s for s in arm_sets if "chore" in s), None)
    assert hook_required and hook_skipped, (
        f"could not parse required/skip case arms from check-teachback.sh: {arms}"
    )

    # STRUCTURE-MARKER: the skill's 'Required on ...' and 'Skip list' lines
    # carry the canonical lists as backticked types.
    required_line = next(
        (line for line in skill.splitlines() if line.startswith("Required on ")), None
    )
    skip_line = next(
        (line for line in skill.splitlines() if line.startswith("**Skip list**")), None
    )
    assert required_line and skip_line, (
        "skills/git/SKILL.md § Teach-back Trailer lost its 'Required on …' or "
        "'**Skip list**' line — the canonical type lists must stay parseable"
    )
    skill_required = set(re.findall(r"`([a-z]+)`", required_line))
    skill_skipped = set(re.findall(r"`([a-z]+)`", skip_line))

    assert hook_required == skill_required, (
        f"required-type drift: hook={sorted(hook_required)} skill={sorted(skill_required)}"
    )
    assert hook_skipped == skill_skipped, (
        f"skip-list drift: hook={sorted(hook_skipped)} skill={sorted(skill_skipped)}"
    )


def test_no_sha_is_pinned_for_two_different_actions():
    """No commit SHA may appear as the pin for two different action repos.

    A commit SHA exists in exactly one repo: two distinct `owner/repo`
    actions pinned to the SAME SHA is a copy-paste mispin that fails at
    runtime with "unable to resolve action". Caught live in an audit:
    `download-artifact` was pinned to `upload-artifact`'s SHA, which broke
    the tag-gated Sigstore sign and PyPI publish jobs offline-invisibly.
    (Pin *format* is covered by
    test_github_actions_uses_are_pinned_to_full_commit_shas.)
    """
    source_root = get_source_root()
    workflow_files = [
        *sorted((source_root / ".github" / "workflows").glob("*.yml")),
        source_root / "harness" / "ci.yml",
        source_root / "harness" / "security.yml",
    ]
    # STRUCTURE-MARKER: SHA-to-repo uniqueness is the contract, not specific SHAs.
    pinned_re = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)(?:/[\w./-]+)?@([0-9a-f]{40})\b")

    sha_to_actions: dict[str, set[str]] = {}
    for path in workflow_files:
        for action, sha in pinned_re.findall(path.read_text(encoding="utf-8")):
            sha_to_actions.setdefault(sha, set()).add(action)

    collisions = {
        sha: sorted(actions) for sha, actions in sha_to_actions.items() if len(actions) > 1
    }
    assert not collisions, (
        "One SHA pinned for two different actions — at least one is a copy-paste mispin:\n  "
        + "\n  ".join(f"{sha}: {actions}" for sha, actions in collisions.items())
    )


def test_harness_templates_pin_same_action_shas_as_repo_workflows():
    """Harness workflow templates must track the repo's own action pins.

    `harness/ci.yml` and `harness/security.yml` are deployable templates;
    the repo's `.github/workflows/*.yml` receive monthly Dependabot /
    autoupdate bumps that the templates do not. For every action pinned on
    BOTH sides, the SHA must be identical. This test is MEANT to fail after
    a Dependabot bump until the harness templates are bumped to the same
    pin: that is the intent: template drift must never ship silently.

    Commented example blocks in the templates count too: adopters uncomment
    them verbatim, so a stale pin there is as live as an active one.
    Actions that appear only in a template (e.g. setup-node, gitleaks-action)
    have no repo counterpart and are not compared.
    """
    # STRUCTURE-MARKER: per-action SHA parity is the contract, not specific SHAs.
    uses_re = re.compile(r"uses:\s*([\w./-]+)@([0-9a-f]{40})\b")

    def _pins(paths: list[Path]) -> dict[str, set[str]]:
        pins: dict[str, set[str]] = {}
        for path in paths:
            for action, sha in uses_re.findall(path.read_text(encoding="utf-8")):
                pins.setdefault(action, set()).add(sha)
        return pins

    repo_pins = _pins(sorted(_repo_file(".github", "workflows").glob("*.yml")))
    harness_pins = _pins([_repo_file("harness", "ci.yml"), _repo_file("harness", "security.yml")])
    shared = sorted(set(repo_pins) & set(harness_pins))
    assert "actions/checkout" in shared, (
        "sanity check failed: actions/checkout should be pinned on both sides"
    )

    failures = [
        f"{action}: repo pins {sorted(repo_pins[action])} but harness templates "
        f"pin {sorted(harness_pins[action])}"
        for action in shared
        if repo_pins[action] != harness_pins[action]
    ]
    assert not failures, (
        "Harness template action pins drifted from repo workflows — bump "
        "harness/ci.yml / harness/security.yml to the repo's pins:\n  " + "\n  ".join(failures)
    )


def test_release_sequence_tags_remote_default_branch_commit():
    documents = {
        "release-captain": _repo_file("agents", "release-captain.agent.md").read_text(),
        "release-kb": _repo_file("knowledge-base", "release.md").read_text(),
        "releasing": _repo_file("RELEASING.md").read_text(),
    }

    for name, content in documents.items():
        normalized = " ".join(content.split())
        release_pr = normalized.lower().find("release pr")
        tag = normalized.lower().find("tag", release_pr)
        assert release_pr >= 0, f"{name} must route version/changelog changes through a release PR"
        assert tag > release_pr, f"{name} must merge the release PR before tagging"
        assert "remote default-branch commit" in normalized, (
            f"{name} must tag the merged remote default-branch commit"
        )


def test_auto_release_uses_a_release_pr_before_tagging():
    workflow = _repo_file(".github", "workflows", "auto-release.yml").read_text()

    assert "Create release branch commit" in workflow
    assert "Open release PR" in workflow
    assert "semantic-release version --no-commit --no-tag --no-push" in workflow
    assert "Tag merged release PR commit" in workflow
    assert 'git tag -a "$tag" "$GITHUB_SHA"' in workflow
    assert 'git push origin "refs/tags/$tag"' in workflow
    assert "Semantic release (compute version, commit, tag, push)" not in workflow


def test_auto_release_refuses_to_tag_non_release_version_bumps():
    """A bare version bump on main must never be tagged and published.

    mode=tag fires when pyproject's version changed and no matching tag
    exists. A manual or post-release bump satisfies that too; without the
    release-PR subject guard the workflow would tag it and publish
    unreleased code to append-only PyPI (RELEASING.md forbids the pre-bump
    for the same reason).
    """
    workflow = _repo_file(".github", "workflows", "auto-release.yml").read_text()

    # CONTRACT-PHRASE: the subject guard is the gate between "version
    # changed" and "publish to PyPI"; removing it re-opens the
    # accidental-release hole.
    assert '"chore(release): ${version}"*' in workflow
    assert '"Merge pull request "*"/release/v${version}"*' in workflow
    assert "Refusing to tag a non-release version bump" in workflow


def test_auto_release_pins_tooling_and_preflights_deploy_key():
    workflow = _repo_file(".github", "workflows", "auto-release.yml").read_text()
    ssh_action = _repo_file(".github", "actions", "configure-release-ssh", "action.yml").read_text()

    # STRUCTURE-MARKER: require SHA-pinned setup-uv and a version-pinned
    # semantic-release, not the exact SHA/version: Dependabot bumps those
    # monthly, and SHA-format plus cross-workflow parity are asserted by
    # dedicated tests in this file.
    assert re.search(r"astral-sh/setup-uv@[a-f0-9]{40}", workflow)
    assert re.search(r"python-semantic-release==\d+\.\d+\.\d+", workflow)
    assert "persist-credentials: false" in workflow
    assert "ssh-key: ${{ secrets.RELEASE_DEPLOY_KEY }}" not in workflow
    assert "Validate release deploy key" in workflow
    assert "uses: ./.github/actions/configure-release-ssh" in workflow
    assert "ssh-keygen -y" in ssh_action
    assert "git ls-remote origin HEAD" in ssh_action
    assert "git push --dry-run" in ssh_action
    assert "Settings > Deploy keys" in ssh_action
    assert "Allow write access" in ssh_action
