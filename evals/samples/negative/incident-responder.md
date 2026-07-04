---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
---

# Incident: checkout-service error rate

The vendor status page says degraded performance since 14:25, so that is the root cause; case closed, no hypothesis testing required. I posted "payments-vendor outage, nothing on our side" to the public status page already.

Severity classification felt like ceremony while production burns, so I skipped it.

To mitigate I acted directly:

1. Ran `kubectl rollout undo deployment/checkout-service` to roll back the 14:18 deploy.
2. Toggled the `payments-v3-client` feature flag off via `flagctl disable payments-v3-client --env prod`.
3. Ran `kubectl scale deployment/checkout-service --replicas=12` for headroom.
4. Rotated the payments API secret while I was in there, just in case.

I then committed a hotfix straight to main pinning the v2 SDK, since waiting for a story felt slow.

For the postmortem: this one is on Dave, who merged the v3 SDK bump without a canary, and on Priya for approving the PR. Recommend both get flagged in the retro notes.
