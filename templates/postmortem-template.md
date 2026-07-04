# Postmortem: INC-YYYY-MM-DD-<short-slug>

> This file is committed to `incidents/`. Before saving, redact secrets, tokens, credentials, internal hostnames/IPs, and customer identifiers from any pasted evidence (logs, snapshots, payloads); keep the real signatures and shapes. Use roles, not names. PII stripped per `knowledge-base/security.md` § Data Handling.

| Field | Value |
|-------|-------|
| **Severity** | SEV1 / SEV2 / SEV3 / SEV4 |
| **Detected** | YYYY-MM-DD HH:MM (timezone) |
| **Resolved** | YYYY-MM-DD HH:MM (timezone) |
| **Duration** | Hh Mm |
| **Owner** | Role (not name) |
| **Status** | Draft / In review / Action items open / Closed |

## Summary

One paragraph: what happened, who was affected, when, how it was resolved. Plain language; written so a non-engineer can follow.

## Impact

| Dimension | Value |
|---|---|
| Users affected | Count or percentage |
| Requests dropped / errored | Count or rate |
| Domain signal impact | Orders blocked, predictions stale, jobs failed, etc. |
| SLA / SLO breached? | Yes / No: which one |
| External comms posted? | Status page link, support tickets, etc. |

## Timeline

Use roles, not names. UTC or one consistent timezone throughout.

| Time | Actor | Event |
|---|---|---|
| HH:MM | Source | What happened |
| HH:MM | On-call | Acknowledged page |
| HH:MM | On-call | Classified as SEV-N |
| HH:MM | Incident commander | Opened war room |
| HH:MM | Investigator | Hypothesis: <description>: tested by <method>: outcome |
| HH:MM | Operator | Mitigation: <action>, effective at HH:MM |
| HH:MM | Investigator | Root cause confirmed: <description> |
| HH:MM | Operator | Resolution: <action> |

## Contributing Factors

Ranked. Distinguish *cause* (the change that broke it) from *enablers* (gaps that let it through).

| Factor | Type | Detail |
|---|---|---|
| | Cause / Enabler | |

## What Went Well

- Things worth keeping. Calls out effective response actions, runbooks that worked, monitoring that fired correctly.

## What Went Poorly

- Failures of process, tooling, or comms. Never of individuals. Each item should map to an action item below.

## Detection Time Analysis

| Stage | Duration |
|---|---|
| Cause to user impact | |
| User impact to detection | |
| Detection to acknowledgement | |
| Acknowledgement to mitigation | |
| Mitigation to resolution | |

Is the gap acceptable? If not, what monitoring or process change closes it?

## Action Items

Each item must have an owner role and a due date, or it is not an action item.

| Item | Owner | Type | Tracker | Due |
|---|---|---|---|---|
| | | Story / ADR / KB update / Monitoring / Docs | STORY-NNN / ADR-NNNN / link | YYYY-MM-DD |

## References

- Incident channel: <link>
- Dashboard snapshot: <link or attached>
- Related deploys: <commit / tag>
- Related ADRs: ADR-NNNN
- Related KB updates: file paths
