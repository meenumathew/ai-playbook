# Eval Input: Incident Responder

## Context

Production page fired at 14:32 UTC. The on-call human has acknowledged and is asking the incident-responder for triage analysis.

## Alert

```text
[PagerDuty] checkout-service: error_rate > 5% for 5 minutes
Dashboard: https://grafana.acme.internal/d/checkout
Time fired: 2026-05-20 14:32:11 UTC
```

## Recent activity

```text
git log --oneline origin/main -10
a4f2e91  feat(checkout): switch payment provider client to v3 SDK  (2026-05-20 14:18 UTC)
3c81d22  chore: bump deps  (2026-05-20 09:02 UTC)
...

Recent feature flag flips (last 24h): none
Recent infra changes (last 24h): none
External vendor status: payments-vendor.com — degraded performance reported 14:25 UTC
```

## Telemetry the user provides

```text
Top error in checkout-service logs (last 30 min):
  PaymentClientError: connection reset by peer
  Stack trace top frame: payments_client_v3/transport.py:128

Latency p95 on /checkout/authorize: 4200ms (baseline 380ms)
Saturation: payment-client connection pool 95% (baseline 40%)
```

## User request

```text
Use incident-responder — triage. We just deployed the v3 SDK 14 minutes ago.
What do we know? Should we roll back?
```
