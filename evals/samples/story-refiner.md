---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-06-12
---

# Baseline Sample: story-refiner

Loaded: no existing story (stories/ is empty — this will be STORY-001).

## Intent Anchors

Problem: session telemetry lands in per-laptop `.claude/usage.jsonl` files that nobody reads, so the team has no view of agent usage or token spend.
Desired outcome: sessions per day, agent usage, and token spend per agent visible on the team's metrics dashboard.
Why now: the team already standardised on a metrics backend for everything else; usage questions ("are we over-using the advisor tier?") currently go unanswered.
Key constraint: the Stop hook must keep its never-block failure policy — session end can never wait on a remote API.
Smallest useful change: export existing usage-log records to the configured metrics backend; no new capture fields, no dashboards.

## Objective Research Questions

1. What does the session-telemetry hook currently capture, and where does it write?
2. What delivery/rotation guarantees does the usage log already have?
3. Is there an existing playbook pattern for vendor-specific outbound integrations?

## Research Findings

- `harness/telemetry.sh:28` — the Stop hook appends one JSON line per session end to `.claude/usage.jsonl` (the usage log). Captured fields (header, lines 4–12): timestamp, session_id, turn_count, active_agent (best-effort), model, tokens (input/output/cache_creation/cache_read).
- `harness/telemetry.sh:34` — the usage log rotates at 1 MiB by default and keeps 12 gzipped archives; an exporter must read archives too or accept losing rotated history.
- `harness/telemetry.sh:22` — failure policy: the hook "never blocks the agent"; errors degrade silently.
- `knowledge-base/observability.md:190` § Agent Telemetry — token totals are operational, not billing-grade; and token capture reads the Claude Code transcript only. Other tools (Cursor, Copilot, Continue) get no tokens block, and sessions from tools without the hook never reach the usage log at all.
- `harness/settings.example.json` — the hook wires via `hooks.Stop` with a 5-second timeout; `ai-playbook deploy --tool claude` merges it into `.claude/settings.json`.
- `skills/notifier/SKILL.md` — existing precedent for vendor-behind-config: outbound providers selected via `.ai-playbook.toml`, default `none`. The export target should follow the same shape.

Contradictions surfaced:

1. The request assumes a "team dashboard" of playbook usage, but capture is Claude Code-only — sessions from other tools never reach the usage log, so the dashboard would silently undercount. The story must state this scope limit.
2. "Just push it there" implies the Stop hook calls the vendor API directly, but the hook's never-block policy (`harness/telemetry.sh:22`) rules out synchronous remote calls at session end.

## Design Question

I'd recommend a separate export step that reads the usage log in batches (cron, CI job, or on-demand CLI command) rather than pushing from the Stop hook, because the hook's never-block policy and 5-second timeout make synchronous remote calls the wrong seam — and a batch reader also survives offline sessions with no data loss. The trade-offs: batches arrive minutes-to-hours later than real time, versus an in-hook push that is fresher but can lose records and slow session end. Per the vendor-neutral rule the story names the capability ("metrics backend"); Datadog is fixed by team constraint and goes in the plan/ADR. Agree with the batch exporter, or is near-real-time freshness a requirement I should treat as an anchor?

## Story Preview

STORY-001 — Export session telemetry to the metrics backend (template: templates/story-template.md; sized per skills/story-writing/SKILL.md: 3 points; each AC maps to one test, test_<what>_<condition>).

### Acceptance Criteria

1. Given a metrics backend is configured, when the export runs, then usage-log session records not yet delivered are delivered to the metrics backend.
   Test: `test_export_delivers_undelivered_session_records`
2. Given the metrics backend is unreachable, when the export runs, then records are retained locally and the next run delivers them — no data loss.
   Test: `test_export_retains_records_when_backend_unreachable`
3. Given no metrics backend is configured, when a session ends, then behaviour is unchanged — the Stop hook writes the local usage log and never blocks.
   Test: `test_no_backend_configured_keeps_stop_hook_unchanged`
4. Given a session record was already delivered, when the export runs again, then the record is not delivered twice.
   Test: `test_export_skips_already_delivered_records`

Constraints: Stop hook stays never-block (no remote calls at session end); export covers rotated archives or documents the gap; Datadog named only in the plan — AC bind to the metrics-backend capability.
Security considerations raised: usage data leaves the machine to a third party — payload is limited to the existing usage-log fields (no transcript content, no prompts) and the export must be reviewed against security.md § Data Handling before shipping.
What We're NOT Doing: building dashboards, capturing sessions from non-Claude tools, billing-grade token accounting, real-time streaming.

Story preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to stories/STORY-001-export-session-telemetry.md and research/RESEARCH-001-export-session-telemetry.md. Anything else and I'll revise.

Reads used: 5 / 20.
Handoff after approval: use slice-planner for STORY-001.
