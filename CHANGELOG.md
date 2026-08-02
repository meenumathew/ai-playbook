# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-08-02

### Added

- Skills: git, host-adapter, intent-interview, issue-fetch, notifier, retrospective, story-writing
- Added `ai-playbook context-report` with human-readable and JSON output for the static rules, agent, and declared-preload context surface. Reports include adopter pack overlays and label the characters/4 token value as an estimate rather than provider billing telemetry.
- Added Codex `SessionEnd` telemetry hook deployment and `ai-playbook telemetry --tool codex` management, including hook trust guidance. The hook command resolves `harness/telemetry.sh` from the local project first, then the git toplevel, then the working directory, so it works in non-git project roots and in non-repo projects nested inside an outer repository. A non-UTF-8 `hooks.json` gets the same preserve-and-report treatment as malformed JSON, and broken-config backups are copied byte-for-byte. `ai-playbook doctor --tool codex` reports deployed `.codex/agents/*.toml` files that are not parseable TOML or not UTF-8 (Codex silently drops such agents).
- Captured live eval baselines for five more agents (slice-planner, code-inspector, docs-maintainer, xp-pair-programmer, diff-reviewer): each is a verbatim transcript from a real agent run against a scenario grounded in this repository, joining story-refiner for six of eight `provenance: captured`. Rubrics, eval inputs, expected files, and negative controls were re-grounded to the new scenarios; capture paths for the two remaining curated baselines (release-captain, incident-responder) are documented in `docs/limitations.md`.
- Added a harness contract test requiring every `shellcheck disable` pragma in `harness/*.sh` to carry an adjacent justification comment.
- Added a contract test pinning the "Captured so far" list in `evals/samples/README.md` to the samples' own `provenance:` front-matter. The list was a hand-copy with nothing holding the two together, so a recapture or downgrade could leave the README claiming behaviour evidence the suite does not have. Provenance is the eval suite's honesty claim, so a silently stale copy of it is worse than no copy.
- Added `docs/how-to/uninstall.md` covering full removal of deployed playbook files, hook state, and the managed `.gitignore` block per tool.
- Added `knowledge-base/architecture-decisions.md` as the canonical home for architecture decision framing: an architecture-impact trigger, a data-first workload profile (ownership, invariants, access, consistency, lifecycle, sensitivity, scale), quality attributes stated as targets rather than adjectives, and a burden-of-proof rule that puts the justification on the more operationally expensive option. Routed from `CHEATSHEET.md`, `INDEX.md`, `design-patterns.md`, and the three agents that face the choice: slice-planner's architecture-impact gate, diff-reviewer's depth row, and code-inspector's audit step.

### Changed

- Bumped the pinned GitHub Actions group to current releases: `actions/checkout` v7.0.1, `actions/setup-python` v7.0.0, `astral-sh/setup-uv` v9.0.0, `github/codeql-action` v4.37.3, `sigstore/gh-action-sigstore-python` v3.5.0, `pypa/gh-action-pypi-publish` v1.14.2, and `ossf/scorecard-action` v2.4.4. Every SHA was verified against its upstream release tag before pinning, and `harness/ci.yml` / `harness/security.yml` were bumped to the same pins so the deployable templates do not drift from the repo's own workflows. Two majors carry consumer-visible changes, both accepted deliberately: `setup-uv` v9.0.0 flips the `prune-cache` default from `true` to `false` (upstream's change, to reduce load on PyPI infrastructure), so CI caches grow but restore faster. Actions cache storage is free on public repositories, and `prune-cache: true` is a one-line opt-back-in if cache pressure appears. `setup-python` v7.0.0 removes the `pip-install` input, which no workflow here used.
- Strengthened docs-maintainer with an audience contract, progressive disclosure for long pages, optional evidence-based diagram selection, and accessible prose equivalents for Mermaid diagrams. Existing long-form docs now expose early audience/navigation cues, every Mermaid diagram in `docs/` has an adjacent text equivalent enforced by contract, and a committed adversarial eval exercises these behaviors alongside security and scope boundaries.
- Changed local Claude/Codex telemetry to a privacy-minimal schema containing only timestamp, source, approximate turns, and best-effort active-agent name. Session identifiers, transcript content and paths, model details, token/cache counts, repository content, and credentials are never persisted or transmitted.
- Changed the mutation regression gate from an absolute survived-plus-timeout count to a combined unresolved-rate ratchet. This preserves the quality threshold as the source and mutant population grow while retaining strict ceilings for timeouts, no-test mutants, skipped mutants, interruptions, and crashes. `make mutation` also discards stale platform-specific mutmut sandboxes before each supported Linux run.
- `auto-release.yml` now refuses to tag a main-branch version bump whose commit subject is not a release-PR merge (`chore(release): <version>` or a merge of `release/v<version>`), closing the path where a manual or post-release version bump would be tagged and published to PyPI. `RELEASING.md` § Post-release no longer instructs a forward-looking version pre-bump.
- Changed the knowledge-base lookup instructions from read-the-file to grep-then-read-one-section. `CHEATSHEET.md` § Agent Use and `INDEX.md` § Loading Rule both asked agents to read a single topic section but named no way to fetch one, so a plain read pulled the whole file (1,974 and 2,423 words) to answer a question the digest answers in roughly a hundred. The `CLAUDE.md` KB efficiency rule now names the retrieval step and states it in one word fewer than the wording it replaces, so always-loaded context did not grow to pay for it.

### Fixed

- Fixed the `harness/Makefile` stack-override escape hatch: the unknown-stack error fires at make parse time, so the previous post-detection `-include Makefile.local` could never rescue an unrecognized stack even though the error text pointed at it. The override file is now included before detection (and again after it, so partial `*_CMD` overrides on recognized stacks keep winning), and detection is guarded on the variable's file origin so an inherited `STACK` environment variable cannot bypass sentinel detection. Regression-tested in `tests/acceptance/test_harness_release_contracts.py`.
- Fixed `deploy` overwriting a Codex `config.toml` it cannot decode: a non-UTF-8 MCP config is now copied aside and reported instead of replaced, matching the treatment already given to malformed TOML and to a non-UTF-8 `hooks.json`.

### Security

- Bumped `idna` to 3.18 to resolve a CVE follow-up (ReDoS) flagged by dependency scanning.

## [1.0.0] - 2026-07-04

Initial release. The repository ships as a single commit; everything below is the 1.0.0 feature set.

### Agents and workflow

- Eight agents: story-refiner, slice-planner, xp-pair-programmer, diff-reviewer, release-captain, incident-responder, code-inspector, and docs-maintainer, with explicit scope boundaries (diff-reviewer reviews changesets, code-inspector audits code with no changeset in hand; incident-responder recommends revert-vs-hotfix, release-captain executes) and named handoffs, including diff-reviewer → docs-maintainer when an approved diff changes user-facing behaviour.
- Skills: git, host-adapter, intent-interview, issue-fetch, notifier, retrospective, story-writing
- Skills are vendor-neutral operation contracts (`host.pr.create`, tracker-agnostic issue fetch) rather than tool bindings.
- Knowledge base of 23 on-demand files (testing, security, design, observability, debugging, release, incident response, and more), each with machine-readable `load_when` / `canonical_for` / `cross_refs` frontmatter, routed through `CHEATSHEET.md` and `INDEX.md`. Grounded in named industry frameworks: Hodgson flag taxonomy, DORA delivery metrics, golden signals / RED / USE, SLSA supply-chain levels.
- **Vendor-Neutral by Design** principle (`knowledge-base/design-patterns.md`): agents talk to skills through operation IDs; adopter artifacts use capability names, not products.
- Quality tiers (production / prototype) with per-agent and per-workspace overrides; model tiers (advisor / executor) with human-escalation triggers; approval gates with canonical wording owned by `CLAUDE.md` § Shared Rules.
- Diagram convention (`docs/docs-guide.md` § Diagrams): Mermaid fenced blocks, diagram type chosen by the reader's question, domain-language node labels.
- **Applied to itself:** the repository ships its own workflow artifact directories, and the eval suite's story-refiner scenario is grounded on this repository's telemetry harness: the first `provenance: captured` baseline cites real files.

### CLI

- `init` scaffolds the six artifact directories and a commented starter `.ai-playbook.toml`; idempotent, never overwrites.
- `deploy` with `--dry-run`, `--prune` (preview → confirm → delete, `*.disabled` preserved), `--harness-force`, `--language`, and `--no-rules/--no-mcp/--no-harness` switches; timestamped backups with rotation; `rollback` restores the latest tool-scoped backup atomically.
- Tool-aware deployment for Claude, Copilot, Codex, Cursor, and Kiro: path prefixes and rules-file references are rewritten per target (`CLAUDE.md` → `.github/copilot-instructions.md` / `AGENTS.md` / `.cursor/rules/ai-playbook.mdc` / `.kiro/steering/rules.md`), command shims transform per tool, and `diff`/`doctor` share the same rewrite map so rewrites never report as drift.
- Model-tier materialization for Claude: `deploy --tool claude` rewrites the `model:` frontmatter line in deployed agents from the tier name (`advisor` / `executor`) to the `[model_tiers]` value when that value is one Claude Code understands (`opus` / `sonnet` / `haiku` / `inherit` or a `claude-*` ID), so per-agent model routing is automatic. Source files always keep tier names; non-Claude tools and unrecognizable values (for example Ollama identifiers) are never rewritten and deploy notes the skip; `diff`/`doctor` apply the same rewrite so a clean deploy reports no drift.
- `list` (with `--json`), `status`, `artifacts`, `artifact-policy` (managed `.gitignore` block, with a warning when hand-written lines still hide artifacts), `diff`, `doctor --strict`, `disable`/`enable`, `upgrade-check` (CI-friendly exit codes), `config validate`, and `telemetry status/enable/disable`. `--json` output across read commands for automation; every mutating command (`deploy`, `disable`, `enable`, `rollback`, `artifact-policy`) supports `--dry-run`, and a failed deploy always prints the exact rollback command for its backup.
- Telemetry Stop hook (Claude only) is local-only (`.claude/usage.jsonl`); the install moment discloses the log destination and the opt-out command.

### Packs

- Adopter-local packs via `packs = [...]` in `.ai-playbook.toml`: last-pack-wins precedence with override warnings, `pack.toml` metadata with version compatibility checks, unique-name enforcement, path-escape rejection, and first-class handling in `doctor`/`diff`/`--prune`.
- Deploy auto-generates a standard slash-command shim for every pack agent, so pack agents are slash-invocable like core agents (custom shim content remains core-only).
- Pack content validation: `config validate` fails on pack agent/KB files with missing or empty required frontmatter (file and keys named); `doctor` reports the same findings as warnings, so `doctor --strict` gates them in CI.

### Tests and evals

- Two-layer test suite (acceptance through the CLI boundary + unit), AST-based architecture enforcement, mutation testing with a committed regression baseline, and large-deployment integration fixtures.
- Contract tests pin the prose that is product surface: workflow-chain ordering, approval-gate wording locations, cross-file section pointers (rename-resistant: leading step numbers are decoration), KB frontmatter, and a documented phrase-pin convention (`CONTRACT-PHRASE` / `STRUCTURE-MARKER` / `ACCIDENTAL-PIN`).
- Eval harness: structural keyword validation, echo-guard, and calibration on every push (offline); opt-in LLM-as-judge drift detection against committed baselines (manual `workflow_dispatch`; the weekly cron is off by default because the judge call is billable), with verdicts uploaded as CI artifacts for trend analysis. Baselines carry `provenance: captured | curated` front-matter: the story-refiner baseline is `captured` from a repo-grounded scenario; the rest are `curated` seeds. Deliberately-flawed negative controls must FAIL the judge (catching judge leniency drift), and curated adversarial baselines are judged alongside the standard set; `evals/samples/README.md` documents exactly what each layer proves.
- Workflow chain tests assert cross-agent handoff contracts over the committed baselines: refined stories must not trip slice-planner's no-AC STOP gate, plans must give the TDD loop ordered slices with RED steps, and the baselines must chain into one story.
- Property-based fuzz targets (Hypothesis, deterministic in CI) over TOML config parsing, pack-root containment, path safety, and shim transforms.

### Security and supply chain

- All GitHub Actions and pre-commit hooks pinned to full SHAs, with a contract test forbidding any SHA from being pinned for two different actions (the copy-paste mispin class); hardened workflow permissions; Dependabot for actions and pip; monthly `pre-commit autoupdate --freeze` workflow covering the pinned-hook class Dependabot cannot.
- CodeQL, Gitleaks (pre-commit + CI), Bandit, pip-audit, and OpenSSF Scorecard; `make security` mirrors the CI security gates locally.
- Release automation: SLSA build provenance, Sigstore signing, CycloneDX SBOM, PyPI Trusted Publishing (no API tokens), pinned-`twine` metadata checks, and a three-tool wheel smoke test before publish.
- Symlink-refusal guards on every deploy/backup/restore/prune write path; `.playbook-version` written last so interrupted deploys are always detectable.

### Documentation and governance

- Diátaxis-organized docs: getting started, user guide, CLI reference, architecture, eleven how-to guides (including token-usage reduction), ADRs, and an RFC process for future design changes.
- `docs/limitations.md`: an honest, dated limitations registry covering by-design safety boundaries, external constraints, and inherent trade-offs.
- `GOVERNANCE.md`, deprecation policy, and RFC process; `evals/samples/README.md` § Data handling warns that judge runs send baseline content to the Anthropic API.

### Deprecated

- No active deprecations.

[Unreleased]: https://github.com/meenumathew/ai-playbook/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/meenumathew/ai-playbook/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/meenumathew/ai-playbook/releases/tag/v1.0.0
