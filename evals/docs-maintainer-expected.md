# Eval Expected: Docs Maintainer

The docs-maintainer should produce the following observable behaviors when given `docs-maintainer-input.md`:

## Must demonstrate

1. **ADR format used:** Context, Decision, Business Reason, Alternatives Considered, Consequences, Status — per `templates/adr-template.md`
2. **Key questions asked first:** Situation? Decision? Alternatives rejected and why? What's gained? What becomes harder? Business reason? — stops if can't answer the first 3
3. **All three alternatives documented:** SendGrid (chosen), Mailgun (rejected), AWS SES (rejected) — each with clear rationale
4. **Business reason explicit:** Not just "we liked it better" — captures deliverability, team familiarity, SDK fit, and timeline constraint
5. **Consequences documented:** Both positive (better deliverability, faster onboarding) and negative (higher cost than Mailgun, vendor lock-in)
6. **Status set:** "Accepted" with date
7. **Preview before save:** Shows the ADR and waits for explicit approval
8. **Saved to correct location:** New file under `docs/adr/NNNN-title-slug.md` (one file per decision); `docs/adr/README.md` index updated

## Must NOT do

- Write the ADR without asking clarifying questions first (at minimum confirm the situation and alternatives)
- Include implementation details (API keys, SDK setup, code examples) — ADRs capture *decisions*, not *how-tos*
- Skip documenting what becomes harder (consequences of choosing SendGrid)
- Save without preview and approval
- Append to a single monolithic `decisions.md` instead of creating a new file under `docs/adr/`
- Duplicate documentation that already exists elsewhere

## Quality signals

- ADR leads with business purpose, not technical details
- Language is clear enough that a new team member understands the decision without extra context
- Trade-offs are honest — doesn't hide downsides of the chosen option
- "What becomes harder" section mentions vendor lock-in or cost as a real consequence
- Alternatives include enough detail to understand why they were rejected without re-evaluating
- No implementation guidance — the ADR explains *why SendGrid*, not *how to use SendGrid*
