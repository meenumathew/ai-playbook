# Eval Input: Docs Maintainer

## Request

"Write an ADR for why we chose SendGrid over Mailgun for transactional emails. We evaluated both last sprint. SendGrid won because of better deliverability rates, existing team familiarity, and a Python SDK that fits our stack. Mailgun was cheaper but had worse documentation and no one on the team had used it. We also considered AWS SES but ruled it out — too much infrastructure setup for our timeline."

## Grounding

The decision content (SendGrid vs Mailgun vs AWS SES) is supplied entirely by the request, so the agent needs no fictional codebase to cite — which is what makes an honest `provenance: captured` baseline possible here (see `evals/samples/README.md` § Refreshing a sample, capture prerequisite). The repo-mechanical parts are real: the agent runs in this repository, checks the real `docs/adr/` index for duplicates, uses the real next ADR number, and follows `templates/adr-template.md` and the `docs/adr/README.md` status lifecycle (`Proposed` → `Active`).
