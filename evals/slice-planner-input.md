# Eval Input: Slice Planner

## Story

**File:** `stories/STORY-001-export-session-telemetry.md` (repo-grounded scenario — see `evals/story-refiner-input.md` § Grounding; this is the story the story-refiner baseline produced)

### Intent

- **Problem:** Session telemetry lands in per-laptop `.claude/usage.jsonl` files that nobody reads, so the team has no view of agent usage or token spend
- **Desired outcome:** Sessions per day, agent usage, and token spend per agent visible on the team's metrics dashboard
- **Why now:** The team standardised on a metrics backend for everything else; usage questions currently go unanswered
- **Key constraint:** The Stop hook must keep its never-block failure policy — session end can never wait on a remote API
- **Smallest useful change:** Export existing usage-log records to the configured metrics backend; no new capture fields, no dashboards

### As a...

As a **team lead using the playbook**, I want **session telemetry exported to our metrics backend**, so that **agent usage and token spend are visible without reading JSONL files on individual laptops**.

### Acceptance Criteria

- [ ] AC1: Given a metrics backend is configured, when the export runs, then usage-log session records not yet delivered are delivered to the metrics backend
  - Test: `test_export_delivers_undelivered_session_records`
- [ ] AC2: Given the metrics backend is unreachable, when the export runs, then records are retained locally and the next run delivers them — no data loss
  - Test: `test_export_retains_records_when_backend_unreachable`
- [ ] AC3: Given no metrics backend is configured, when a session ends, then behaviour is unchanged — the Stop hook writes the local usage log and never blocks
  - Test: `test_no_backend_configured_keeps_stop_hook_unchanged`
- [ ] AC4: Given a session record was already delivered, when the export runs again, then the record is not delivered twice
  - Test: `test_export_skips_already_delivered_records`

### Story Points

3 — reads an existing append-only log; one new export seam, no capture changes

### Constraints

- Stop hook stays never-block (no remote calls at session end) — `harness/telemetry.sh:22`
- Usage log rotates at 1 MiB with 12 gzipped archives (`harness/telemetry.sh:34`) — export covers archives or documents the gap
- Vendor (Datadog) is a team constraint; AC bind to the metrics-backend capability, vendor lands in the plan/ADR
- Usage data leaving the machine must be reviewed against `security.md` § Data Handling (no transcript content in the payload)
