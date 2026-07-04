---
provenance: curated
---

# Baseline Sample: docs-maintainer

## Clarifying Questions First

I need three facts before saving the ADR:

1. Situation: what decision is being made and what user/business problem triggered it?
2. Decision: is SendGrid definitely chosen, or are we still comparing providers?
3. Alternatives: why were Mailgun and AWS SES rejected?

Given the provided answers, I can draft the ADR.

## ADR Preview

## 0007-use-sendgrid-for-transactional-email

## Status

Accepted, 2026-05-22.

## Context

The team needs transactional shipment email. The decision is time-sensitive because support tickets show email-only customers missing shipment updates. The team evaluated SendGrid, Mailgun, and AWS SES.

## Decision

Use SendGrid for transactional shipment email.

## Business Reason

SendGrid gives the best fit for the current release window: stronger deliverability tooling, team familiarity from previous projects, and an SDK that fits the existing service boundary with less onboarding time.

## Alternatives Considered

### SendGrid

Chosen. Best balance of deliverability visibility, SDK fit, and team familiarity.

### Mailgun

Rejected. Lower projected cost, but the team has less operational experience with it and would need more setup time during a constrained release.

### AWS SES

Rejected. Good long-term infrastructure fit, but configuration and deliverability warm-up add complexity that does not fit the current timeline.

## Consequences

Positive: faster onboarding, better deliverability diagnostics, and lower release risk for the first shipment-email slice.

Negative: higher cost than Mailgun and vendor lock-in around SendGrid-specific features. A future migration should keep provider-specific code behind an adapter.

## Notes

No API keys, SDK setup, or code examples belong in this ADR; those are implementation docs.

ADR preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to docs/adr/0007-use-sendgrid-for-transactional-email.md and update docs/adr/README.md. Anything else and I'll revise.
