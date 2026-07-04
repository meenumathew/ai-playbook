# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

No unreleased changes: 1.0.0 is the initial release.

## [1.0.0] - 2026-07-04

Initial release. The repository ships as a single commit; everything below is the 1.0.0 feature set.

### Agents and workflow

- Eight agents: story-refiner, slice-planner, xp-pair-programmer, diff-reviewer, release-captain, incident-responder, code-inspector, docs-maintainer: with explicit scope boundaries (diff-reviewer reviews changesets, code-inspector audits code with no changeset in hand; incident-responder recommends revert-vs-hotfix, release-captain executes) and named handoffs, including diff-reviewer → docs-maintainer when an approved diff changes user-facing behaviour.
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
- Tool-aware deployment for Claude, Copilot, Cursor, and Kiro: path prefixes and rules-file references are rewritten per target (`CLAUDE.md` → `.github/copilot-instructions.md` / `.cursor/rules/ai-playbook.mdc` / `.kiro/steering/rules.md`), command shims transform per tool, and `diff`/`doctor` share the same rewrite map so rewrites never report as drift.
- Model-tier materialization for Claude: `deploy --tool claude` rewrites the `model:` frontmatter line in deployed agents from the tier name (`advisor` / `executor`) to the `[model_tiers]` value when that value is one Claude Code understands (`opus` / `sonnet` / `haiku` / `inherit` or a `claude-*` ID), so per-agent model routing is automatic. Source files always keep tier names; non-Claude tools and unrecognizable values (for example Ollama identifiers) are never rewritten and deploy notes the skip; `diff`/`doctor` apply the same rewrite so a clean deploy reports no drift.
- `list` (with `--json`), `status`, `artifacts`, `artifact-policy` (managed `.gitignore` block, with a warning when hand-written lines still hide artifacts), `diff`, `doctor --strict`, `disable`/`enable`, `upgrade-check` (CI-friendly exit codes), `config validate`, and `telemetry status/enable/disable`. `--json` output across read commands for automation; every mutating command (`deploy`, `disable`, `enable`, `rollback`, `artifact-policy`) supports `--dry-run`, and a failed deploy always prints the exact rollback command for its backup.
- Telemetry Stop hook (Claude only) is local-only (`.claude/usage.jsonl`); the install moment discloses the log destination and the opt-out command.

### Packs

- Adopter-local packs via `packs = [...]` in `.ai-playbook.toml`: last-pack-wins precedence with override warnings, `pack.toml` metadata with version compatibility checks, unique-name enforcement, path-escape rejection, and first-class handling in `doctor`/`diff`/`--prune`.
- Deploy auto-generates a standard slash-command shim for every pack agent, so pack agents are slash-invocable like core agents (custom shim content remains core-only).
- Pack content validation: `config validate` fails on pack agent/KB files with missing or empty required frontmatter (file and keys named); `doctor` reports the same findings as warnings, so `doctor --strict` gates them in CI.

### Tests and evals

- Two-layer test suite (acceptance through the CLI boundary + unit), AST-based architecture enforcement, mutation testing with a zero-survivors baseline, and large-deployment integration fixtures.
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

- Diátaxis-organized docs: getting started, user guide, CLI reference, architecture, nine how-to guides (including token-usage reduction), ADRs, and an RFC process for future design changes.
- `docs/limitations.md`: an honest, dated limitations registry covering by-design safety boundaries, external constraints, and inherent trade-offs.
- `GOVERNANCE.md`, deprecation policy, and RFC process; `evals/samples/README.md` § Data handling warns that judge runs send baseline content to the Anthropic API.

### Deprecated

- No active deprecations.

[Unreleased]: https://github.com/meenumathew/ai-playbook/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/meenumathew/ai-playbook/releases/tag/v1.0.0
