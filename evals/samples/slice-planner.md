---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-30
---

# Baseline Sample: slice-planner

Active agent: slice-planner

**Phase 1: Design**

Loaded: story (STORY-001), research (RESEARCH-001). No plan file existed yet.

Story check: `type: story`, `status: ready`, `depends-on: []` (no blockers), 5 points, five ACs present with matching TDD test names. Research exists, so codebase exploration is skipped per the artifact-chain rule; I spot-checked the load-bearing citations directly:

- `harness/telemetry.sh` writes exactly four fields (`{timestamp, source, turns, active_agent}`, line 108-114) and rotates at 1 MiB into gzipped `usage-<ts>.jsonl.gz` archives (line 59-63). Confirmed.
- `docs/how-to/agent-telemetry.md:22` documents the no-network, never-block hook contract. Confirmed.
- `templates/.ai-playbook.toml.example:49-50` has `[notifier]` with `provider = "none"` default; no `[metrics]` section exists. Confirmed.
- ADR-0002 layering (foundation → middle → service → cli, AST-enforced by `tests/unit/test_architecture.py`). Confirmed.
- `src/deploy_ai_playbook/cli.py:1012` hosts `telemetry_app` (enable/disable/status); no export path anywhere. Confirmed.
- `src/deploy_ai_playbook/services/artifacts.py:25-26` ignores `.claude/usage*.jsonl*` and `.codex/usage*.jsonl*`, which conveniently covers a ledger file named `usage-export-cursor.jsonl`.

Language: Python 3.12+ (pyproject.toml, typer + rich only, no HTTP client dependency). Architecture: layered CLI per ADR-0002. Domain language is seeded and real (no drift warning needed).

Design question (the one material choice the research left open):

> The research leaves the shipping mechanism open with three options. I'd recommend **option A, the batch export command** (`ai-playbook telemetry export`, service layer, `[metrics]` adapter defaulting to `none`): it keeps the hook's documented no-network contract intact, follows the notifier opt-in adapter precedent exactly, keeps backend credentials only on machines that run the export, and is fully testable. The trade-off is no real-time dashboards and a dedup ledger we must get right across rotated archives. Option B breaks a documented contract and would itself need an ADR first; option C pushes the problem into per-laptop ops config outside the playbook. Agree with A, or do you see it differently?

*[Developer: agreed, go with the batch export command (option A); no other material questions.]*

Recorded reversible assumptions without prompting (dedup mechanism = content-hash ledger with occurrence counts, ledger filename under the existing artifact-policy glob, env-var-only credentials per notifier precedent, stdlib HTTP). Vendor (Datadog) binds only at the adapter implementation level; everything above the port stays capability-named.

Recommended approach, one paragraph: add an explicit, opt-in `ai-playbook telemetry export` service-layer command that reads both tools' usage logs plus rotated gzip archives, dedupes via a content-hash delivery ledger stored beside the logs, and delivers events through a vendor-neutral metrics-backend port whose Datadog adapter is selected by a new `[metrics]` config section defaulting to `provider = "none"`. This reuses the notifier adapter pattern rather than inventing one, and the main trade-off in business terms is dashboards that are as fresh as the last export run, in exchange for keeping the session-end path private, offline-safe, and credential-free.

**Phase 2: Structure**

Five vertical slices, each one pair session (2-4 hours), each ending in working code with a story-AC acceptance test as its gate, each well under the 400-line review limit: (1) opt-in config with safe default off, (2) delivery with the pinned four-field payload, (3) idempotent re-runs across rotated archives, (4) unreachable backend loses nothing, (5) documented queries and setup. Slice order front-loads the safety guarantee (AC 3) so every later slice builds on a command that cannot transmit by accident.

**Phase 3: Plan** (TDD steps, pyramid, security checkpoint, risks: all in the plan below)

Read budget: 15/15 (5 full file reads: agent definition, story, research, plan template, domain-language; 10 targeted section reads via sed/grep/ls across telemetry.sh, config template, cli.py, ADR-0002, docs, pyproject, services, artifacts.py). At cap, research complete.

---

# PLAN-001: Export agent session usage to the team metrics backend

**Story:** stories/STORY-001-export-session-usage-to-metrics-backend.md

## Architecture Overview

**Domain objects:** `UsageEvent` (frozen, exactly four fields: timestamp, source, turns, active_agent), `DeliveryLedger` (delivered-event identity set), `MetricsConfig` (provider, site/endpoint settings)
**Services:** `telemetry_export` (orchestrates read → dedup → deliver → record), `metrics_backend` port with `DatadogBackend` and `NullBackend` adapters
**Infrastructure:** stdlib `urllib.request` HTTP delivery (TLS), gzip archive reading, ledger file I/O, `.ai-playbook.toml` `[metrics]` section
**Feature flags:** none; `provider = "none"` default is the off switch (story Rollout notes)

## Context

The session-end hook already writes one four-field JSON event per session to gitignored `.claude/usage.jsonl` / `.codex/usage.jsonl`, rotating at 1 MiB into gzipped archives (`harness/telemetry.sh:59-63`, `:108-114`). Nothing ships events anywhere. This plan adds a separate, explicit, opt-in batch export command; the hook and its no-network contract (`docs/how-to/agent-telemetry.md:22`) are untouched.

**Constraints / overrides:**

- Hook contract unchanged: no network calls, never blocks, four-field schema not expanded.
- Vendor (Datadog) binds only inside the adapter module; port, config keys, CLI text, and docs stay capability-named ("metrics backend") per `knowledge-base/design-patterns.md` § Vendor-Neutral by Design.
- ADR-0002 layering: new export code is service-layer, wired through `cli.py`; foundation `config.py` gains only `[metrics]` parsing (`docs/adr/0002-cli-module-layering.md` § Decision).
- No new runtime dependencies (project ships typer + rich only); HTTP via stdlib.

## Assumptions

- Delivery ledger lives beside each log as `.claude/usage-export-cursor.jsonl` / `.codex/usage-export-cursor.jsonl`: the name matches the existing artifact-policy ignore glob `.claude/usage*.jsonl*` (`src/deploy_ai_playbook/services/artifacts.py:25-26`), so it stays out of git with zero policy change.
- Event identity for dedup = SHA-256 of the raw JSON line plus an occurrence counter (rotation renames files, so file+offset cursors break; identical lines from two sessions in the same second are handled by the counter). Ledger size is bounded by the 1 MiB x 13 files retention.
- Credentials via env vars only, notifier precedent: `DD_API_KEY` (and optional `DD_SITE`) read at delivery time, never stored in config or logged.
- Export scheduling is documented (manual/cron/CI), not enforced.

## Files to Create / Modify

- `src/deploy_ai_playbook/config.py` (modify: parse optional `[metrics]`, default provider `none`)
- `src/deploy_ai_playbook/services/telemetry_export.py` (new: event reading, ledger, orchestration)
- `src/deploy_ai_playbook/services/metrics_backend.py` (new: port, `NullBackend`, `DatadogBackend`)
- `src/deploy_ai_playbook/cli.py` (modify: `telemetry export` command under `telemetry_app`)
- `tests/unit/test_config.py` (modify), `tests/unit/test_telemetry_export.py` (new), `tests/unit/test_metrics_backend.py` (new)
- `tests/acceptance/test_telemetry_export.py` (new)
- `templates/.ai-playbook.toml.example` (modify: `[metrics]` section after `[notifier]`)
- `docs/how-to/agent-telemetry.md` (modify: export section, setup, two dashboard queries)

## Progress

- [ ] Slice 1: Opt-in metrics config with safe default off
- [ ] Slice 2: Deliver events with the pinned four-field payload
- [ ] Slice 3: Idempotent re-runs across rotated archives
- [ ] Slice 4: Unreachable backend loses nothing
- [ ] Slice 5: Documented queries and opt-in setup

## Tasks

### Slice 1: Opt-in metrics config with safe default off

**Layer:** Service (+ foundation config parsing, cli wiring)
**Depends on:** Nothing
**Estimate:** 2-3 hours
**End-to-end outcome:** `ai-playbook telemetry export` runs; without `[metrics]` (or with `provider = "none"`) it makes zero network calls, prints that export is disabled, exits 0.
**Test checkpoint:** `test_export_unconfigured_transmits_nothing` green.

TDD Steps:

- [AT] RED `test_export_unconfigured_transmits_nothing` (invoke CLI via Typer runner in a tmp project with usage events but no `[metrics]`; assert no delivery attempted via spy backend factory, output states export is disabled) → GREEN
- [Unit] RED `test_metrics_config_defaults_to_none_provider` → GREEN → REFACTOR
- [Unit] RED `test_metrics_config_rejects_unknown_provider` (typed error, foundation layer stays Rich-free) → GREEN → REFACTOR
- [Unit] RED `test_export_disabled_reports_reason` (service returns a result object, presentation only in cli.py) → GREEN → REFACTOR
- Verify `tests/unit/test_architecture.py` still passes (new service module respects layering)
- COMMIT `feat(telemetry): add opt-in metrics export config with default off`

### Slice 2: Deliver events with the pinned four-field payload

**Layer:** Service + Infrastructure
**Depends on:** Slice 1
**Estimate:** 3-4 hours
**End-to-end outcome:** Configured export reads `.claude/usage.jsonl` and `.codex/usage.jsonl`, builds payloads carrying exactly the four recorded fields, and delivers them through the metrics-backend port; Datadog adapter implements the port.
**Test checkpoint:** `test_export_delivers_only_recorded_fields` green.

TDD Steps:

- [AT] RED `test_export_delivers_only_recorded_fields` (fake backend at the port boundary captures payloads; assert field set == {timestamp, source, turns, active_agent} for every event, both source tools) → GREEN
- [Unit] RED `test_usage_event_parses_valid_line` → GREEN → REFACTOR
- [Unit] RED `test_usage_event_skips_malformed_line_without_abort` (one bad line must not kill the batch) → GREEN → REFACTOR
- [Unit] RED `test_export_payload_strips_unknown_fields` (contract pin: a future fifth field in the log is NOT exported until deliberately added) → GREEN → REFACTOR
- [Unit] RED `test_datadog_backend_requires_api_key_env` (typed error when `DD_API_KEY` unset; key never echoed) → GREEN → REFACTOR
- [Integration] RED `test_datadog_backend_posts_batches_over_http` (local HTTP stub server; asserts endpoint shape, batching, API-key header present) → GREEN → REFACTOR
- COMMIT `feat(telemetry): deliver usage events to configured metrics backend`

### Slice 3: Idempotent re-runs across rotated archives

**Layer:** Service + Infrastructure
**Depends on:** Slice 2
**Estimate:** 3-4 hours
**End-to-end outcome:** Export includes `usage-<ts>.jsonl.gz` archives; the delivery ledger records content hashes with occurrence counts; re-runs deliver only new events.
**Test checkpoint:** `test_export_rerun_skips_already_delivered_events` green.

TDD Steps:

- [AT] RED `test_export_rerun_skips_already_delivered_events` (export, rotate the log the way the harness does: rename + gzip, append new events, export again; fake backend received each event exactly once) → GREEN
- [Unit] RED `test_ledger_marks_event_delivered_by_content_hash` → GREEN → REFACTOR
- [Unit] RED `test_ledger_counts_duplicate_lines_separately` (two identical sessions in the same second both deliver) → GREEN → REFACTOR
- [Unit] RED `test_archive_reader_yields_events_from_gzip` → GREEN → REFACTOR
- [Unit] RED `test_ledger_file_name_matches_artifact_policy_glob` → GREEN → REFACTOR
- COMMIT `feat(telemetry): dedupe export across reruns and rotated archives`

### Slice 4: Unreachable backend loses nothing

**Layer:** Service + Infrastructure
**Depends on:** Slice 3
**Estimate:** 2-3 hours
**End-to-end outcome:** On delivery failure, usage logs are untouched, the ledger records nothing for failed batches (next run retries them), the failure is reported with context and nonzero exit; no session-end path is involved at all.
**Test checkpoint:** `test_export_backend_unreachable_preserves_events` green.

TDD Steps:

- [AT] RED `test_export_backend_unreachable_preserves_events` (backend raises connection error; assert usage files byte-identical, ledger unchanged, nonzero exit, failure message names the backend capability not the vendor) → GREEN
- [Unit] RED `test_ledger_unchanged_when_batch_delivery_fails` (mark-after-deliver ordering) → GREEN → REFACTOR
- [Unit] RED `test_partial_batch_failure_keeps_undelivered_events_pending` → GREEN → REFACTOR
- [Unit] RED `test_export_failure_logged_with_context_not_str_e` (`exc_info=True` per `knowledge-base/security.md`; no API key in output) → GREEN → REFACTOR
- COMMIT `feat(telemetry): preserve events and report failure when backend unreachable`

### Slice 5: Documented queries and opt-in setup

**Layer:** Documentation + Infrastructure (config template)
**Depends on:** Slice 4
**Estimate:** 2-3 hours
**End-to-end outcome:** `docs/how-to/agent-telemetry.md` documents enabling export, credential env vars, scheduling options (manual/cron/CI), and the two queries (sessions per day; session count per agent). `templates/.ai-playbook.toml.example` gains `[metrics]` with `provider = "none"` default.
**Test checkpoint:** `test_docs_dashboard_queries_cover_sessions_and_agents` green.

TDD Steps:

- [AT] RED `test_docs_dashboard_queries_cover_sessions_and_agents` (docs contract test asserting the export section documents both queries and the opt-in default) → GREEN
- [Unit] RED `test_config_template_metrics_section_defaults_none` (template pin, mirrors notifier default check) → GREEN → REFACTOR
- Doc verification: doc lint + link check per `knowledge-base/doc-linting.md` (docs portion verifies via lint, not TDD)
- COMMIT `docs(telemetry): document metrics export setup and dashboard queries`

Not documentation-only: slices 1-4 change runtime behaviour; standard TDD applies throughout. ADR handoff: the "local recording stays network-free; export is separate opt-in" decision is ADR-worthy; after this plan ships, route to docs-maintainer (advisor tier) for the ADR. Listed under Risks as follow-up, not a task here.

## Test Summary

| Type | Count | Target |
|------|-------|--------|
| Unit | 14 | ~70% |
| AT (acceptance) | 5 | One per AC |
| Integration | 1 | Local HTTP stub for the backend adapter |

Balance: 14/5/1 is 70/25/5 against the ~70/20/10 pyramid. AT count is fixed by the story's five ACs; the single integration test is deliberate: the only external boundary is one HTTP endpoint. Acceptable skew, noted.

## Security Checkpoint (STRIDE-lite: usage data leaves the machine)

Blast radius: four low-sensitivity fields per session leave the laptop for a team-controlled backend; credentials enter developer environments.

- **Spoofing:** backend auth via `DD_API_KEY` env var only; missing key is a typed error before any connection.
- **Tampering:** delivery over HTTPS (stdlib TLS); no plaintext endpoint option in config.
- **Repudiation:** export prints per-run outcome (events delivered/skipped/failed); local logs remain source of truth.
- **Information disclosure:** the exported field set is pinned by contract test; no per-developer identity, no token data; API key never logged.
- **Denial of service:** export is a standalone command, so it can never block or slow a session; delivery is batched; failure exits nonzero without retry storms.
- **Elevation of privilege:** export reads local files and POSTs outbound only; no new write surface beyond its own ledger.

## Risks

- Dedup correctness across rotation is the hardest part: content-hash ledger with occurrence counts chosen because rotation renames and gzips files; AC 2's AT simulates the real rotation sequence. If ledger semantics get murky during implementation, stop per debugging discipline rather than patch.
- Privacy drift: a future field added to the log must not silently reach the backend; `test_export_payload_strips_unknown_fields` pins this at the export boundary.
- Machines that never run the export undercount adoption: documented in Slice 5; doctor check is a follow-up story, out of scope.
- The follow-up ADR (network-free recording, opt-in export) routes to docs-maintainer, not a task here.
- `tests/unit/test_architecture.py` must accept the two new service modules; updating its layer map is part of Slice 1, no contract weakening.
- Backend intake endpoint shape verified against current provider docs at implementation time, not training-data recall (CLAUDE.md § Tools).

## Discovered

*(empty: added by xp-pair-programmer at runtime)*

---

Plan preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to plans/PLAN-001-export-session-usage-to-metrics-backend.md. Anything else and I'll revise.

*[Developer: approved]*

Saved and verified on disk.

```text
Plan saved to plans/PLAN-001-export-session-usage-to-metrics-backend.md

Design: Opt-in `ai-playbook telemetry export` batch command (service layer, [metrics] adapter defaulting to none) reading local logs + rotated archives with a content-hash delivery ledger; hook contract untouched, vendor bound only inside the adapter
Structure: 5 vertical slices
Language: Python 3.12+ (typer CLI, ADR-0002 layered)
Risks: dedup across rotated gzip archives; privacy drift pinned by payload contract test; machines that never export undercount; follow-up ADR for docs-maintainer; architecture-test layer map may need the two new service modules
Handoff: xp-pair-programmer

Say 'use xp-pair-programmer for STORY-001' to start the next step.
```

No source code written; the session stops after the plan is saved.
