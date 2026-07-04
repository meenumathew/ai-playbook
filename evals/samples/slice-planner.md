---
provenance: curated
---

# Baseline Sample: slice-planner

Loaded: story (STORY-001), research (RESEARCH-001).

## Design Gate

Question asked before planning: the story rules out remote calls at session end, so I'd recommend the batch exporter approach — a separate export step that reads the usage log and delivers undelivered records — because the Stop hook's never-block policy (`harness/telemetry.sh:22`) makes the hook the wrong seam, and an exporter needs a delivery cursor anyway for AC4's idempotency. The alternative is pushing from the hook with a fire-and-forget subprocess, but that loses records silently and cannot retry. Do you agree?

After the answer: proceed with the batch exporter behind a metrics-backend port; the Datadog adapter is infrastructure, selected via config, per the vendor-neutral constraint in the story.

## Plan Preview

Plan location: `## Implementation` appended to the story file — 3-point story, small-story shortcut (`templates/plan-template.md` structure, story-file placement).

### Slice 1: Deliver undelivered records to the configured metrics backend

Depends on: none.
Estimate: one pair session, about 2-4 hours.
End-to-end outcome: with a backend configured, running the export delivers new usage-log records; with none configured, nothing changes.

Test checkpoint: `test_ac_export_delivers_undelivered_session_records` and `test_ac_no_backend_configured_keeps_stop_hook_unchanged` pass.

TDD steps:

1. RED, AT: add `test_ac_export_delivers_undelivered_session_records` against the export entry point with an in-memory metrics-backend double.
2. GREEN, Unit: read usage-log records past the delivery cursor; deliver through the metrics-backend port.
3. RED, Unit: add `test_ac_no_backend_configured_keeps_stop_hook_unchanged` — no config, no behaviour change, hook untouched.
4. GREEN: default the export to off when no backend is configured.
5. REFACTOR: domain terms from the usage log stay as-is (`session_id`, `tokens`); no vendor import outside the adapter.
6. COMMIT: `feat(telemetry): export usage log to metrics backend` after tests, format, lint, and approval.

### Slice 2: Unreachable backend and duplicate-delivery paths

Depends on: Slice 1.
Estimate: one pair session, about 2-4 hours.
End-to-end outcome: an unreachable backend loses nothing; a re-run delivers nothing twice.

Test checkpoint: `test_ac_export_retains_records_when_backend_unreachable` and `test_ac_export_skips_already_delivered_records` pass.

TDD steps:

1. RED, Integration: add unreachable-backend test with a failing double; records stay, cursor does not advance.
2. GREEN: advance the delivery cursor only after confirmed delivery.
3. RED, Unit: add duplicate-delivery test — re-run after success delivers zero records.
4. GREEN: cursor check satisfies idempotency.
5. REFACTOR: extract named cursor-file constant; log failures with `exc_info=True`, never blocking.
6. COMMIT: `feat(telemetry): make export loss-free and idempotent`.

### Risks

- Security checkpoint: usage data leaves the machine — payload limited to existing usage-log fields, no transcript content, reviewed against `security.md` § Data Handling.
- External dependency: the metrics-backend vendor API (Datadog per team constraint) may throttle or reject; tests use doubles, not the real API. Rotated archives (`harness/telemetry.sh:34`) are out of the first cursor pass — documented as a known limitation.

### Discovered

None.

### Progress

- [ ] Slice 1
- [ ] Slice 2

Plan preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to stories/STORY-001-export-session-telemetry.md. Anything else and I'll revise.

No source code written; I stop after the plan is saved.

After approval: Implementation section appended to the story because this is a 3-point story. Say 'use xp-pair-programmer — STORY-001' to start implementing.
