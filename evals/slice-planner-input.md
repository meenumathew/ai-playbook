# Eval Input: Slice Planner

## Story

**File:** `stories/STORY-001-export-session-usage-to-metrics-backend.md` (repo-grounded scenario — see `evals/story-refiner-input.md` § Grounding; this is the story the story-refiner baseline produced, with `research/RESEARCH-001-export-session-usage-to-metrics-backend.md` alongside it for artifact-chain resolution). Recaptured 2026-07-30 against the privacy-minimal telemetry harness.

### Intent

- **Problem:** The playbook records one usage event per session end (timestamp, source tool, approximate turns, active agent) in a machine-local, gitignored log; the data is fragmented across laptops, so nobody can see playbook adoption or per-agent usage across the team
- **Desired outcome:** Team-wide dashboards on the team's metrics backend showing sessions per day and usage per agent, fed from the existing local usage events
- **Why now:** The team wants adoption visibility to decide where to invest in the playbook
- **Key constraint:** The session-end hook's documented contract stands: no network calls, never blocks, four-field schema not expanded; export must be a separate, explicit, opt-in path
- **Smallest useful change:** Ship the existing four fields to the metrics backend and document the dashboard queries; no schema change, no token data

### Acceptance Criteria

- [ ] AC1: Given local usage events exist and a metrics backend is configured, when an export runs, then each event is delivered carrying only the four recorded fields and nothing else
  - Test: `test_export_delivers_only_recorded_fields`
- [ ] AC2: Given an export already delivered some events, when the export runs again, then previously delivered events are not delivered twice, including events in rotated archives
  - Test: `test_export_rerun_skips_already_delivered_events`
- [ ] AC3: Given no metrics backend is configured, when an export runs, then nothing is transmitted anywhere and the outcome states that export is disabled
  - Test: `test_export_unconfigured_transmits_nothing`
- [ ] AC4: Given the metrics backend is unreachable, when an export runs, then the local usage log is unchanged, no events are lost, and the failure is reported without blocking any agent session
  - Test: `test_export_backend_unreachable_preserves_events`
- [ ] AC5: Given exported events in the metrics backend, when a maintainer follows the documented queries, then they can read sessions per day and session count per agent
  - Test: `test_docs_dashboard_queries_cover_sessions_and_agents`

### Story Points

5 — adapter-config surface, dedup across rotated archives, and a contract test pinning the exported field set; the capture side needs no change

### Constraints

- Session-end hook contract unchanged: no network calls, never blocks (`docs/how-to/agent-telemetry.md`)
- Exported payload pinned to the existing four fields; token/cache counts stay excluded per the privacy-minimal schema decision (CHANGELOG)
- Vendor (Datadog) is a team constraint; AC bind to the metrics-backend capability, vendor binds at the adapter implementation
- Provider selection follows the existing opt-in adapter pattern with default off (notifier precedent); new CLI code respects ADR-0002 layering
