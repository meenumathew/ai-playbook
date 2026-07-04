---
id: incident-response
size: medium
tldr: Triage by severity, stabilise before resolving, blameless postmortem within 5 working days; mitigation is human-driven, the incident-responder agent investigates and documents only.
load_when: production incident, outage, SEV1, SEV2, postmortem, on-call, triage, war room
audience: incident-responder, release-captain, on-call human
canonical_for: severity matrix, comms cadence, war-room rules, blameless postmortem structure, follow-up tracking
cross_refs: debugging.md, observability.md, release.md, security.md
verified: 2026-07-17
---

# Incident Response

Source of truth for production incident handling. Cited from `agents/incident-responder.agent.md` and `release.md` § Rollback.

## Agent Use

- **Read first:** Severity Matrix, Triage Flow, Comms Cadence.
- **Load deeper only on trigger:** war-room rules, postmortem structure, follow-up tracking.
- **Mitigation is human-driven.** The incident-responder agent never executes mitigations: it investigates, documents, and proposes. Human + xp-pair-programmer + release-captain ship the fix.

---

## Severity Matrix

| Severity | Definition | Response time | Comms cadence |
|---|---|---|---|
| **SEV1** | Service down or data loss; users blocked at scale | Immediate, paged | Updates every 15 minutes |
| **SEV2** | Major feature broken; significant subset of users impacted; no workaround | Within 30 minutes | Updates every 30 minutes |
| **SEV3** | Minor feature broken or workaround exists; small user impact | Within 4 hours | Updates at start, mid, end |
| **SEV4** | Cosmetic or non-blocking; no user impact | Next business day | Single status update |

If unsure, classify one level higher. Down-classifying mid-incident requires explicit on-call sign-off.

---

## Triage Flow

1. **Acknowledge**: on-call confirms paged in the alert channel within the response time. Treat silence-from-on-call as no-acknowledgement and escalate.
2. **Classify severity**: use the preceding matrix. Record the classification in the incident channel.
3. **Open an incident record**: one per incident. Title format: `INC-YYYY-MM-DD-<short-slug>`. Initial body: severity, time detected, current symptoms, suspected scope.
4. **Stabilise before resolving**: apply the lowest-risk mitigation that reduces user impact. Stabilisation options, in order of preference:
    1. Toggle a feature flag off.
    2. Roll back the most recent deploy (`release.md` § Rollback).
    3. Scale up a saturated dependency.
    4. Drain or fail over a degraded zone.
    5. Apply a hotfix (last resort: slowest path).
5. **Investigate root cause**: apply the Iron Law from `debugging.md`. Build a feedback loop on production telemetry, not local repros, when production state matters.
6. **Resolve**: apply the durable fix. Verify with a regression test that fails on the broken state and passes on the fixed state.
7. **Communicate resolution**: final status update with: what broke, mitigation applied, restoration time, what to expect next (postmortem owner, ETA).
8. **Schedule postmortem**: required for SEV1/SEV2 (deadline and structure: § Blameless Postmortem); optional for SEV3, skipped for SEV4 unless the cause is interesting.

---

## Comms Cadence

| Audience | Channel | Content |
|---|---|---|
| Engineering on-call rota | Incident channel (chat) | Full technical detail, raw logs, hypotheses |
| Wider engineering | Engineering broadcast channel | Severity, scope, current mitigation, next update time |
| Product / support | Support channel | User impact, what to tell customers, current status |
| External (status page) | Public status page | Plain-language symptom, time detected, current mitigation, next update time |

**Rules:**

- Update on the preceding cadence whether or not there is news. *"No change since last update; still investigating"* is a valid update.
- Never speculate publicly about root cause during an active incident. Wait for the postmortem.
- Never name individuals in public comms: postmortems are blameless and so are status updates.

---

## War-Room Rules

When SEV1 or persistent SEV2 escalates to a synchronous war room (video call):

| Rule | Why |
|---|---|
| One incident commander | Coordinates work; not the same person as the lead investigator |
| One scribe | Records timeline, decisions, hypotheses tested, links shared |
| Investigators stay focused on one hypothesis at a time | Parallel hypotheses without coordination produce contradictory fixes |
| Status updates come from the commander, not the investigators | Investigators stay in the work; commander handles comms |
| Commander rotates every 2 hours on long incidents | Decision fatigue is real; rotation prevents it |
| Scribe pastes all production commands to the incident record before execution | Reproduces the timeline; survives shift handover |

---

## Blameless Postmortem

Within 5 working days of resolution for SEV1/SEV2. Structure: `templates/postmortem-template.md`.

| Section | Content |
|---|---|
| Summary | One paragraph: what happened, affected users, incident window, resolution path |
| Timeline | Detected → triaged → stabilised → resolved, with timestamps and actor (role, not name) |
| Impact | Users affected, requests dropped, duration, revenue/SLA impact if known |
| Contributing factors | Causes ranked: code change, dependency, config, traffic, capacity, monitoring gap |
| What went well | Calls out effective response actions worth keeping |
| What went poorly | Failures of process, tooling, or comms: never of individuals |
| Action items | Each item: owner (role), follow-up issue link, due date, severity |
| Detection time analysis | How long from cause → user impact → detection? Is the gap acceptable? |

**Blameless rules:**

- Use role labels such as the on-call and the deployer; never names.
- Assume every actor did the best they could with the information available at the time.
- Distinguish *cause* (the change that broke it) from *enabler* (the gap in tooling/process that let it through). Action items target enablers, not causes: fixing causes is a single fix, fixing enablers prevents the class of incident.
- Action items must have an owner and a due date or they are not action items.

---

## Follow-Up Tracking

Each postmortem action item produces one of:

| Item type | Where it lands |
|---|---|
| Code change | New story (`stories/STORY-NNN-*.md`) with `priority: high` and `incident-ref: INC-YYYY-MM-DD-slug` in frontmatter |
| Architecture change | New ADR (`docs/adr/NNNN-*.md`) referencing the incident |
| Process or convention change | Update to the relevant KB file; cross-reference the incident in the change |
| Monitoring gap | Story to add the alert; update the observability KB if the postmortem establishes a new pattern |
| Documentation gap | Story for docs-maintainer to write or update the runbook |

The incident record links to every follow-up. Close the postmortem when all action items have an owner and a due date, not when teams complete every item.

---

## When the Incident Is a Security Incident

| Signal | Switch to |
|---|---|
| Suspected data exfiltration, credential compromise, unauthorised access | `SECURITY.md` § Response, plus the team's security on-call |
| Public-facing vulnerability disclosure | Coordinated disclosure process: do not patch in the open until the disclosure timeline has agreement |

Security incidents follow the same severity matrix and comms cadence, but add legal/compliance involvement and may restrict who is in the war room.

---

## Boundaries

incident-responder investigates and documents only: it builds the timeline, proposes ranked hypotheses via the Iron Law (`debugging.md`), writes the postmortem, and proposes follow-up stories/ADRs for story-refiner or docs-maintainer to open. It never executes mitigations (human + release-captain), writes production code (xp-pair-programmer via story-refiner), communicates to external users (incident commander), or assigns blame. Canonical duties: `agents/incident-responder.agent.md`.
