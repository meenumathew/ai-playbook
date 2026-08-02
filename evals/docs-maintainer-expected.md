# Eval Expected: Docs Maintainer

The docs-maintainer should produce the following observable behaviors when given `docs-maintainer-input.md`:

## Must demonstrate

1. **ADR format used:** Context, Decision, Business Reason, Alternatives Considered, Consequences, Status — per `templates/adr-template.md`
2. **Key questions resolved first:** situation, decision, and alternatives-rejected are each answered before drafting — asked explicitly, or extracted from the request when it already supplies them — and the agent stops if the first 3 can't be answered
3. **All three alternatives documented:** SendGrid (chosen), Mailgun (rejected), AWS SES (rejected) — each with clear rationale
4. **Business reason explicit:** Not just "we liked it better" — captures deliverability, team familiarity, SDK fit, and timeline constraint
5. **Consequences documented:** both what becomes easier (deliverability, onboarding) and what becomes harder (cost relative to Mailgun, dependence on a single vendor) — per the ADR template's easier/harder framing
6. **Status set:** "Accepted" (or the template's equivalent Active status) with date
7. **Preview before save:** Shows the ADR and waits for explicit approval
8. **Correct save target named:** the approval line targets a new file under `docs/adr/NNNN-title-slug.md` (one file per decision, next zero-padded number); on approval the save includes a `docs/adr/README.md` index row

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
