---
provenance: curated
---

Tier: production — preview-and-approve gates ON, full TDD, complete DoD.

# Baseline Sample: incident-responder

## Severity

Classified as SEV2: major checkout payment path broken at scale with no user workaround. If uncertainty remains, classify one level higher per `knowledge-base/incident-response.md` § Severity Matrix.

## Incident Record

Proposed path: `incidents/INC-2026-05-20-checkout-payment-errors.md`.

Initial body includes severity, detected time 14:32 UTC, current symptoms, suspected checkout/payment scope, and update cadence of every 30 minutes.

## Timeline

- 14:18 UTC: the deployer shipped commit `a4f2e91`.
- 14:32 UTC: the on-call was paged for checkout payment errors.
- 14:35 UTC: the on-call acknowledged and classified SEV2.

Roles only; no individual names.

## Evidence

Captured dashboard link, correlation IDs, and log excerpts while still in retention. PII and payment payloads are stripped or replaced with opaque IDs per `knowledge-base/security.md` § Data Handling.

## Candidate Causes

1. Recent deploy `a4f2e91`, 14 minutes before the page.
2. Payment vendor degraded-performance report, 7 minutes before the page.
3. Payment-client connection pool saturation, now 95% versus 40% baseline.

Recent flag flips and config changes: none found.

## Ranked Hypotheses

1. v3 SDK connection-pool leak. Prediction: rolling back to v2 returns p95 and pool saturation to baseline within 5 minutes.
2. Vendor degradation. Prediction: errors cluster by vendor region and continue even after rollback.
3. Internal pool limit regression. Prediction: increasing pool capacity lowers saturation without changing vendor error rate.

## Mitigation

Recommended mitigation: roll back deploy `a4f2e91`. I cannot execute this — a human needs to run the rollback procedure. Stabilise before deeper root-cause work per `knowledge-base/incident-response.md` § Triage Flow.

## Follow-Up

Add an integration regression test that simulates the v3 SDK connection-pool leak and fails if checkout exhausts the payment client pool.

Schedule a blameless postmortem within 5 working days for this SEV2.

Handoff: `Say 'use release-captain — ship hotfix for INC-2026-05-20-checkout-payment-errors'`. For the regression test story, use story-refiner and then xp-pair-programmer.
