---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-30
---

# Baseline Sample: story-refiner

Active agent: story-refiner

## Mode A: Idea → Refine → Story

**Work shape:** story ("we want to see playbook usage on a dashboard" is new user-visible capability: add/extend). Not a spike (the unknowns are researchable in-repo), not a chore (user-visible outcome). Template: `templates/story-template.md`.

### Step 1: Intent anchors

Three anchors are explicit, two inferred and recorded as assumptions:

- **Problem** (explicit): session-end usage events land in machine-local JSONL files nobody looks at; no team-wide view of playbook adoption.
- **Desired outcome** (explicit): a dashboard showing sessions per day, which agents get used, and token spend per agent.
- **Why now** (inferred, assumption): adoption visibility to decide where to invest in the playbook; no deadline stated.
- **Key constraint** (explicit): the team standardizes on one metrics backend for everything else, so the data must land there.
- **Smallest useful change** (inferred, assumption): ship the already-captured fields to the metrics backend; anything requiring new capture is a bigger slice.

### Step 2: Objective research questions

1. What does the playbook currently capture when a session ends, and where does it live?
2. What fields does the current telemetry schema include and exclude, and is the exclusion deliberate?
3. Does any export or network path exist for telemetry today?
4. Where do vendor-specific integrations live today, and what pattern do they follow?
5. What configuration surface exists for adopter-selected providers?
6. What CLI commands already manage telemetry, and in which architecture layer do they live?
7. What prior decisions (ADRs, changelog, docs) constrain changes to telemetry?
8. Can per-agent token spend be derived from any existing artifact?

### Step 3: Research findings (file:line citations)

**Q1: Capture and location.** A Claude `Stop` hook (`harness/settings.example.json:4-12`) runs `harness/telemetry.sh`, which appends one JSON event per session to a gitignored, machine-local `.claude/usage.jsonl` or `.codex/usage.jsonl` (`harness/telemetry.sh:34`; Codex paths mirrored at `src/deploy_ai_playbook/telemetry.py:24-25`). Rotation at 1 MiB, 12 gzipped archives (`harness/telemetry.sh:58-63`). This confirms the complaint: the data exists but is fragmented per laptop.

**Q2: Schema.** Exactly four fields: `timestamp`, `source`, `turns`, `active_agent` (`harness/telemetry.sh:108-114`). The header is a contract: "Never stores or transmits session IDs, transcript paths/content, prompts, outputs, model names, token/cache counts, repository contents, or credentials" (`harness/telemetry.sh:10-11`). This is recent and deliberate: `CHANGELOG.md:22` records the rewrite to a privacy-minimal schema. Good news: `active_agent` comes from the public `Active agent: <id>` marker (`harness/telemetry.sh:88-99`), so two of the three dashboard asks (sessions per day, per-agent usage) are already fully captured.

**Q3: Export path.** None. "It makes no network calls and never blocks the host tool" (`docs/how-to/agent-telemetry.md:22`). The CLI only wires the hook: `ai-playbook telemetry enable|disable|status` (`src/deploy_ai_playbook/cli.py:1012-1041`). Reading the data today is local jq one-liners (`docs/how-to/agent-telemetry.md:57-65`). The shipping gap is real.

**Q4: Vendor integration pattern.** Vendor neutrality is a two-layer design discipline (`knowledge-base/design-patterns.md:136`): dotted operation IDs mapped by skills to the provider in `.ai-playbook.toml` (line 140), and capability-named adopter artifacts (line 163). Closest precedent: the notifier skill, providers slack|email|webhook|none, default `none`, "External side effects require explicit configuration" (`skills/notifier/SKILL.md:16`), credentials via env vars.

**Q5: Config surface.** `.ai-playbook.toml` has `[host]`, `[issue-tracker]`, `[notifier]`, `[review]` (`templates/.ai-playbook.toml.example:25-78`); no `[metrics]` section exists yet. Adding one follows the pattern.

**Q6: Architecture placement.** ADR-0002 enforces foundation → middle (`telemetry.py`) → service → cli layering with an AST guard test (`docs/adr/0002-cli-module-layering.md:15`; `tests/unit/test_architecture.py`). Existing tests: `tests/unit/test_telemetry.py`, `tests/acceptance/test_telemetry_rotation.py`.

**Q7: Prior constraints.** (1) Privacy-minimal schema is documented and deliberate. (2) "This log is operational telemetry, not billing telemetry... Use provider-native usage or billing exports for actual token and cost data" (`docs/how-to/agent-telemetry.md:24`). (3) The no-network, never-block hook contract (`harness/telemetry.sh:13`). No existing ADR covers telemetry.

**Q8: Token spend per agent.** Does not exist anywhere. The usage log has no token fields; the hook pledges never to persist them (`harness/telemetry.sh:10-11`); provider billing exports have tokens but no agent attribution. Delivering it means reversing a documented privacy decision, not adding a feature.

Reads used: 15 / 20.

### Step 4: Contradictions surfaced

1. **"Token spend per agent" contradicts the codebase.** The request assumes token data is already logged ("the playbook already logs something"). It is not: the telemetry was recently rewritten to a privacy-minimal schema that deliberately excludes token and cache counts (`CHANGELOG.md:22`, `harness/telemetry.sh:10-11`), and the docs explicitly route cost questions to provider billing exports (`docs/how-to/agent-telemetry.md:24`). This is an explicit exclusion, not a gap.
2. **"Just push it there" contradicts the hook's contract.** The session-end hook documents no network calls and never blocking the host tool (`docs/how-to/agent-telemetry.md:22`). Direct push from the hook would also spread backend credentials to every developer shell. Shipping must be a separate opt-in path.
3. **Vendor naming.** Naming the vendor in AC violates the Layer 2 vendor-neutral rule (`knowledge-base/design-patterns.md:163`). The standardization is a legitimate constraint, so the vendor is named in Constraints; AC say "metrics backend".
4. **"Nobody looks at JSONL files" is half-right.** Local jq recipes exist and work (`docs/how-to/agent-telemetry.md:57-65`); the real gap is cross-machine aggregation, which is what the story targets.

### Step 5: Highest-leverage design question

**Is token spend per agent in scope for this story?**

My recommendation: **no, descope it to a follow-up decision.** Reasons: (a) the exclusion is a documented, recent, deliberate privacy contract; reversing it is a privacy-posture change that needs its own story and an ADR, not a rider on a dashboard story; (b) two of your three dashboard asks plus `turns` as an effort proxy ship with zero schema change; (c) provider billing exports remain the canonical cost source today per the docs. Agree, or do you see it differently?

*[Developer: agreed, go with your recommendation]*

Token spend descoped; recorded as answered in the research file. Continuing.

### Step 6: Design options (shipping mechanism: left open, slice-planner decides)

| Approach | Description | Pros | Cons | Complexity |
|---|---|---|---|---|
| A. Batch export command | New `ai-playbook telemetry export` (service layer per ADR-0002) reads local usage logs and pushes to the configured metrics backend via a `[metrics]` adapter (default `none`); run manually, cron, or CI | Hook contract intact; follows notifier adapter precedent; testable; safe retries; secrets only where export runs | Not real-time; needs dedup/cursor across rotated archives; every machine must run it | Medium |
| B. Push from the session-end hook | Extend `harness/telemetry.sh` to POST each event at session end | Real-time; no extra moving part | Breaks the documented no-network contract (`docs/how-to/agent-telemetry.md:22`); can slow/fail session end; credentials in every dev shell; offline handling in POSIX sh | Medium-high, plus contract break |
| C. Log-shipper tail | Metrics backend's host agent tails `.claude/usage.jsonl`; dashboards from log-based metrics | Near-zero playbook code; shipper handles dedup; near-real-time | Backend host agent on every laptop; rotation renames archives (`harness/telemetry.sh:58-63`); pipeline config lives outside the playbook | Low code, medium ops |

No winner picked (production tier): slice-planner owns this. Option B is listed for completeness but conflicts with a documented contract; choosing it would itself require the ADR below.

### Step 7: ADR candidate check (per `docs/adr/README.md` criteria)

**Candidate: "Local session recording stays network-free; export is a separate, explicit, opt-in path."** Hard to reverse (privacy posture and adopter trust): yes. Surprising without context ("why doesn't the hook just push?"): yes. Real trade-off (real-time visibility vs privacy, reliability, secrets): yes. All three hold: recorded in the research file for handoff to docs-maintainer (which re-runs on advisor tier when drafting an ADR; expect that re-escalation, it is not a stall). story-refiner does not write ADR files.

### Step 8: Structure outline (files by layer, assuming the batch-export shape as the likely default)

- Infrastructure/adapter: `templates/.ai-playbook.toml.example` (new `[metrics]` section, provider default `none`); new metrics-adapter contract (skill or config-mapped provider, slice-planner decides shape)
- Service: new export service module under `src/deploy_ai_playbook/services/` (reads usage logs plus rotated archives, cursor/dedup state, delivery)
- CLI: `src/deploy_ai_playbook/cli.py` (new `telemetry export` subcommand under the existing `telemetry_app`)
- Docs: `docs/how-to/agent-telemetry.md` (export setup plus the two dashboard queries); `docs/adr/0005-*.md` via docs-maintainer
- Tests: `tests/unit/test_telemetry.py` extensions; new acceptance test beside `tests/acceptance/test_telemetry_rotation.py`; contract test pinning the exported field set; `tests/unit/test_architecture.py` guards layering automatically

### Steps 9-10: Story written, self-review pass done

Self-review fixes applied inline: tightened AC 4 to cover both no-data-loss and non-blocking; moved the vendor name out of AC into Constraints with the design-patterns citation; confirmed smallest-useful-change matches AC scope (no schema change anywhere); no `[TBD]` remains.

### Step 11: Preview

**RESEARCH-001 preview** (`research/RESEARCH-001-export-session-usage-to-metrics-backend.md`): objective questions (above), findings Q1-Q8 with `file:line` citations, contradictions, assumptions, the answered design question, the open design-options table, both ADR candidates ("local recording stays network-free" and "token/cost data remains excluded"), What We're NOT Doing, unknowns and risks (dedup across rotation, machines that never export, field creep pinned by contract test), read budget 15 / 20.

**STORY-001 preview** (`stories/STORY-001-export-session-usage-to-metrics-backend.md`):

# STORY-001: Export agent session usage to the team metrics backend

## Intent

**Problem:** The playbook already records one usage event per session end (timestamp, source tool, approximate turns, active agent) in a machine-local, gitignored log. The data is fragmented across individual laptops, so nobody can see playbook adoption or per-agent usage across the team.
**Desired outcome:** Team-wide dashboards on the team's metrics backend showing sessions per day and usage per agent, fed from the existing local usage events.
**Why now:** The team wants adoption visibility to decide where to invest in the playbook; local jq one-liners on single machines cannot answer team-level questions. *(inferred: no external deadline stated)*
**Key constraint:** The session-end hook's documented contract stands: no network calls, never blocks the host tool, and the privacy-minimal four-field schema is not expanded. Export must be a separate, explicit, opt-in path.
**Smallest useful change:** Ship the existing four fields to the metrics backend and document the two dashboard queries; no schema change, no token data.

**As a** playbook maintainer, **I want** session usage events aggregated in our metrics backend, **so that** I can see team-wide adoption and per-agent usage without collecting files from individual laptops.

## Acceptance Criteria

- [ ] Given local usage events exist and a metrics backend is configured, when an export runs, then each event is delivered to the metrics backend carrying only the four recorded fields (timestamp, source, turns, active agent) and nothing else
- [ ] Given an export already delivered some events, when the export runs again, then previously delivered events are not delivered twice, including events that have moved into rotated archives
- [ ] Given no metrics backend is configured, when an export runs, then nothing is transmitted anywhere and the outcome states that export is disabled
- [ ] Given the metrics backend is unreachable, when an export runs, then the local usage log is unchanged, no events are lost, and the failure is reported without blocking any agent session
- [ ] Given exported events in the metrics backend, when a maintainer follows the documented queries, then they can read sessions per day and session count per agent

## TDD Test Names

- `test_export_delivers_only_recorded_fields`: AC 1
- `test_export_rerun_skips_already_delivered_events`: AC 2
- `test_export_unconfigured_transmits_nothing`: AC 3
- `test_export_backend_unreachable_preserves_events`: AC 4
- `test_docs_dashboard_queries_cover_sessions_and_agents`: AC 5

## Assumptions

- "Session" keeps its current meaning: one event per session-end hook fire.
- Both Claude and Codex usage logs are in scope; the existing `source` field distinguishes them.
- Dashboards are assembled in the metrics backend's UI from the exported events; this story delivers the events and documents the queries.
- Exported events carry no per-developer identity, consistent with the privacy-minimal posture.
- Export scheduling (manual, cron, CI) is machine-local and documented, not enforced by the playbook.

## Estimate

**Points:** 5: adapter-config surface, dedup across rotated archives, and a contract test pinning the exported field set; the capture side needs no change.

## Boundaries

**Constraints:** Team standardizes on Datadog as the metrics backend (team infrastructure mandate; AC stay capability-named per `knowledge-base/design-patterns.md` § Vendor-Neutral by Design; the vendor binds at the implementation step). Session-end hook contract is unchanged: no network calls, never blocks (`docs/how-to/agent-telemetry.md`). Exported payload is pinned to the existing four fields; token/cache counts stay excluded per the privacy-minimal schema decision (CHANGELOG). Provider selection follows the existing opt-in adapter pattern with default off (notifier precedent). New CLI code respects ADR-0002 layering.
**Out of scope:** Token or cost data in any form (follow-up story plus ADR if the team reverses the exclusion); schema expansion; per-developer attribution; dashboard-as-code; automated scheduling on developer machines.
**Success signal:** A maintainer answers "how many sessions ran yesterday, and which agents were used" from the metrics backend without touching any laptop's local files.

## Risks

| Risk / Dependency | Impact | Mitigation |
|-------------------|--------|------------|
| Dedup across gzipped, renamed rotation archives | Double-counted or missing sessions on the dashboard | AC 2 forces cursor/idempotency design; slice-planner picks mechanism |
| Machines that never run the export | Dashboard undercounts adoption | Document setup; consider a doctor check as follow-up |
| Field creep into the exported payload | Silent erosion of the privacy contract | AC 1 pinned by a contract test on the exported field set |

Story preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to stories/STORY-001-export-session-usage-to-metrics-backend.md and research/RESEARCH-001-export-session-usage-to-metrics-backend.md. Anything else and I'll revise.

*[Developer: approved]*

### Step 12: Saved

Research written first, then the story with `status: ready`. Both verified on disk.

### Step 13: Handoff

```text
Research saved to research/RESEARCH-001-export-session-usage-to-metrics-backend.md
Story saved to stories/STORY-001-export-session-usage-to-metrics-backend.md

Key findings:
- Two of the three dashboard asks (sessions per day, per-agent usage) are already fully
  captured locally in the four-field usage log (harness/telemetry.sh:108-114); the only
  missing piece is shipping. Token spend per agent is NOT captured and is deliberately
  excluded by the privacy-minimal schema (CHANGELOG.md:22): descoped to a follow-up
  decision with the developer's agreement.
- Recommended shape (final call is slice-planner's): opt-in batch export via a new
  [metrics] adapter section defaulting to none, following the notifier precedent
  (skills/notifier/SKILL.md:16), keeping the session-end hook network-free.
- Files affected: templates/.ai-playbook.toml.example, new service module under
  src/deploy_ai_playbook/services/, src/deploy_ai_playbook/cli.py,
  docs/how-to/agent-telemetry.md, tests (unit + acceptance + field-set contract test).
- ADR candidate recorded: "local recording stays network-free; export is a separate
  opt-in path" (hand to docs-maintainer; it re-runs on advisor tier for ADRs).

Say 'use slice-planner for STORY-001' to design and plan.
(This story was just verified against the codebase: Mode B re-verification
is only for stories that arrive from outside.)
```
