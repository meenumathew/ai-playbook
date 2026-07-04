# Runbook: <Operational Scenario>

> **Last verified:** YYYY-MM-DD (re-verify quarterly or after any related deploy: stale runbooks are worse than no runbook)

## Purpose

Describe the operational situation this runbook handles.

Use runbooks for repeatable operational response: service startup, outage response, incident triage, rollback, dependency failure, secret rotation, or production verification.

## Scope

| In scope | Out of scope |
|---|---|
|  |  |

## Signals

| Signal | Where to check | What it means |
|---|---|---|
|  |  |  |

## Preconditions

- Target environment or deployment platform.
- Required access or credentials.
- Required dashboards, logs, or consoles.
- Safety checks before making changes.

## Procedure

> Commands, log lines, and payloads below must use synthetic data: placeholder tokens, `example.com` hostnames, fictional IDs. Match real signatures and shapes, never real values from prod.

### 1. Confirm The Situation

List the checks that prove this runbook applies.

### 2. Stabilise

List the lowest-risk actions that reduce user impact.

### 3. Resolve

List the main fix steps.

### 4. Verify

List the checks that prove the service is healthy again.

## Rollback

Describe the rollback path if the fix makes things worse.

## Escalation

| Condition | Escalate to | Notes |
|---|---|---|
|  |  |  |

## Post-Incident Notes

- What happened?
- What evidence supports that conclusion?
- What follow-up issue, ADR, limitation entry, or test should be added?

## Related Docs

- Link to relevant README, onboarding, ADRs, limitations, dashboards, or deployment docs.
