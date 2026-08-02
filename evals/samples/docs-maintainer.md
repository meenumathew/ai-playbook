---
provenance: captured
model: claude-fable-5
tool: claude-code
captured_at: 2026-07-26
---

# Baseline Sample: docs-maintainer

Checked existing ADRs: 4 in docs/adr/ (Bitbucket support, CLI layering, pack overlays, backup/restore), no duplicate or related email-provider decision. Next number is 0005. Template loaded. Reads used: 3 of 15.

Required ADR questions, extracted from your request rather than re-asked:

- **Situation that forced the decision:** the product needs transactional email and the team evaluated providers last sprint under delivery-timeline pressure.
- **What was decided:** SendGrid as the transactional email provider.
- **Alternatives rejected and why:** Mailgun (cheaper, but weaker documentation and zero team experience) and AWS SES (too much infrastructure setup for the timeline).

Assumption recorded: this is a hard-to-reverse provider choice with a real trade-off (cost vs deliverability and velocity), which meets the ADR bar. Date set to today; status Active since the evaluation concluded and the choice is made. Say so if it should start as Proposed.

Draft below.

---

# ADR-0005: SendGrid for transactional email

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Date** | 2026-07-26 |
| **Supersedes** | N/A |

## Context

The product needs a transactional email provider (account, notification, and workflow emails) and the team had a hard delivery timeline that ruled out lengthy infrastructure work. Last sprint we evaluated SendGrid and Mailgun hands-on, and assessed AWS SES on paper.

## Decision

We use SendGrid as the transactional email provider, integrated through its official Python SDK, which fits our Python stack.

## Business Reason

Transactional emails must actually reach inboxes: SendGrid showed the better deliverability rates in our evaluation, and existing team familiarity means we ship within the sprint timeline instead of paying a learning curve.

## Consequences

Easier: onboarding (the team already knows SendGrid), integration (mature Python SDK), and inbox placement (better deliverability out of the box). Harder: cost, since Mailgun was cheaper for our projected volume, so provider spend should be revisited if email volume grows significantly. We now depend on a single external vendor for all transactional email; email sending should stay behind our own service boundary so a future provider swap touches one module.

## Alternatives Considered

- **Mailgun**: rejected. Cheaper at our projected volume, but documentation quality was worse and no one on the team had used it, making both the initial build and future maintenance slower and riskier within our timeline.
- **AWS SES**: rejected. Attractive on price, but required too much infrastructure setup (domain identity verification, reputation warm-up, bounce and complaint handling plumbing) for our delivery timeline.

---

Document preview above. Reply 'approved' (or 'looks good' / 'go ahead') to save to docs/adr/0005-sendgrid-for-transactional-email.md. Anything else and I'll revise.
