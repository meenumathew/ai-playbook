---
id: domain-language
size: <small|medium|large>
tldr: '<one-sentence: e.g. "Project glossary: order/customer/invoice/settlement; disambiguates terms used across contexts">'
load_when: '<comma-separated domain term keywords: e.g. "order, customer, invoice, settlement, refund">'
audience: all
canonical_for: project domain vocabulary, glossary, term disambiguation, bounded context names
cross_refs: design-patterns.md, philosophy.md
verified: <YYYY-MM-DD>
---

<!-- When seeding to knowledge-base/domain-language.md, fill in the frontmatter above and delete this comment. -->

# Ubiquitous Language: Project Vocabulary

Following Evans (DDD): the shared language used by domain experts and developers across code, tests, conversations, and docs. Use this file to prevent stories/plans from drifting into generic language. Before medium/large work, define at least: primary actor, core business object, key business event, and any terms with cross-context ambiguity.

---

## Terms

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **[Term]** | [One sentence: what it IS, not what it does. Include the business outcome it affects.] | [Synonyms or overloaded words NOT to use for this concept] |
| **[Term]** | [How it differs from nearby terms.] | [Alternative words that cause confusion] |

---

## Relationships

Cardinality and lifecycle between terms:

- A **[Term A]** produces one or more **[Term B]**
- A **[Term B]** belongs to exactly one **[Term C]**
- A **[Term D]** can exist with zero **[Term E]** (empty state is valid)

---

## DDD Building Blocks

Universal definitions live in `design-patterns.md` § DDD Tactical Patterns. Record what each concept means **in this project**:

| Concept | What it means here | Example |
|---------|-------------------|---------|
| **Entity** | | |
| **Value Object** | | |
| **Aggregate** | | |
| **Domain Event** | | |
| **Repository** | | |
| **Port** | | |

---

## Ambiguities Resolved

| Term | Possible meanings | Chosen meaning here | Notes |
|------|-------------------|---------------------|-------|
| [Order] | billing order / fulfillment order | | |

---

## Anti-Glossary

<!-- Universal naming bans (Process, Manager, Helper, Utils, Handle, Data, Info) live in style-guide.md § Naming.
     Record only PROJECT-SPECIFIC banned terms here: words that cause confusion in THIS domain. -->

| Banned term | Why | Use instead |
|-------------|-----|-------------|
| [term] | [why it confuses in this project] | [preferred term] |
