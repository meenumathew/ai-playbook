# Methodology and References

AI Playbook packages established software-engineering practices into deployable agent instructions. This page records the major influences behind the workflow and knowledge base.

---

## Core Practices

| Area | Influence | How it appears in the playbook |
|------|-----------|--------------------------------|
| Extreme Programming | Pairing, small steps, simple design, continuous feedback | `xp-pair-programmer` works one test at a time, runs checks frequently, and asks for review at useful points. |
| Test-Driven Development | Red/green/refactor and acceptance-test driven development | `xp-pair-programmer` writes acceptance tests from ACs, then drives implementation with focused inner-loop tests. |
| Domain-Driven Design | Ubiquitous language, bounded contexts, domain model ownership | `story-refiner` checks domain language and agents route architecture questions through the knowledge base. |
| Hexagonal Architecture | Ports and adapters, dependencies flowing inward | `knowledge-base/design-patterns.md` keeps business rules in domain objects and infrastructure at the edges. |
| Documentation as code | Markdown artifacts and reviewable records | Stories, plans, research, ADRs, audits, and runbooks are plain files in the repo. |
| Cognitive & Intent Debt | Triple debt model (technical + cognitive + intent) | Teach-back gate, commit rationale, comprehension checkpoints in `knowledge-base/philosophy.md` § Cognitive Health. |
| Harness Engineering | Context + Constraints + Linters as mechanical enforcement | Architecture tests, Make targets, local hooks, CI pipeline: tooling enforces rules, not just documentation. Also: lint messages as teaching, doc gardening, garbage collection sweeps (`knowledge-base/working-agreement.md` § Reference: Agent-First Automation). |
| Cohesion / Coupling / Abstraction | Property vocabulary behind module shape (Constantine, Parnas, Ousterhout) | `knowledge-base/design-fundamentals.md` defines the properties; design-patterns.md, philosophy.md, and refactoring.md cross-link to it as the canonical home. |

---

## References

### Books

| # | Reference | Relevance |
|---|-----------|-----------|
| 1 | Beck, K. (2000). *Extreme Programming Explained: Embrace Change*. Addison-Wesley. | XP practices: pairing, small releases, simple design, continuous feedback |
| 2 | Beck, K. (2003). *Test-Driven Development: By Example*. Addison-Wesley. | Red-green-refactor cycle |
| 3 | Freeman, S. & Pryce, N. (2009). *Growing Object-Oriented Software, Guided by Tests*. Addison-Wesley. | Acceptance Test-Driven Development (ATDD), double-loop TDD |
| 4 | Evans, E. (2003). *Domain-Driven Design: Tackling Complexity in the Heart of Software*. Addison-Wesley. | Ubiquitous language, bounded contexts, domain model |
<!-- vale Google.We = NO -->
| 5 | Cockburn, A. (2005). *Hexagonal Architecture (Ports and Adapters)*. alistair.cockburn.us. | Dependencies flowing inward, domain isolation |
<!-- vale Google.We = YES -->
| 6 | Fowler, M. (2018). *Refactoring: Improving the Design of Existing Code* (2nd ed.). Addison-Wesley. | Refactoring moves, code smells |
| 7 | Martin, R.C. (2008). *Clean Code: A Handbook of Agile Software Craftsmanship*. Prentice Hall. | Naming, single responsibility, readability |
| 8 | Humble, J. & Farley, D. (2010). *Continuous Delivery*. Addison-Wesley. | CI/CD pipelines, deployment automation, Branch by Abstraction (`refactoring.md` § Migration-Scale Moves) |
| 9 | Yourdon, E. & Constantine, L. (1979). *Structured Design: Fundamentals of a Discipline of Computer Program and Systems Design*. Prentice-Hall. | Cohesion and coupling as named properties; original taxonomies (`design-fundamentals.md`) |
| 10 | Hunt, A. & Thomas, D. (1999). *The Pragmatic Programmer*. Addison-Wesley. | DRY principle, orthogonality (`design-fundamentals.md` § Named Principles) |
| 11 | Martin, R.C. (2002). *Agile Software Development: Principles, Patterns, and Practices*. Prentice Hall. | SOLID principles (SRP, OCP, LSP, ISP, DIP): referenced by name in `design-fundamentals.md` § Named Principles |
| 12 | Feathers, M. (2004). *Working Effectively with Legacy Code*. Prentice Hall. | Seams vocabulary (`design-patterns.md` § Module Depth and Seams); characterization tests (`testing.md` § Retrofitting Tests) |
| 13 | Ousterhout, J. (2018). *A Philosophy of Software Design*. Yaknyam Press. | Deep modules, complexity, leverage at the interface (`design-patterns.md` § Module Depth and Seams + `design-fundamentals.md` § Abstraction); three symptoms of complexity, strategic vs tactical programming, design it twice (`design-fundamentals.md` § Building Software That Lasts) |

### Papers & Articles

| # | Reference | Relevance |
|---|-----------|-----------|
| 14 | Storey, M.-A. (2026). "From Technical Debt to Cognitive and Intent Debt: Rethinking Software Health in the Age of AI." *arXiv:2603.22106*. | Triple debt model: cognitive debt (team loses understanding) and intent debt (rationale disappears) as risks of AI-generated code |
| 15 | Lopopolo, R. (2026). "Harness Engineering: Leveraging Codex in an Agent-First World." *OpenAI Engineering Blog*, Feb 11. | Context + Constraints + Linters framework for AI agent environments; lint messages as teaching; doc gardening; garbage collection sweeps |
| 16 | Cunningham, W. (1992). "The WyCash Portfolio Management System." *OOPSLA '92 Experience Report*. | Original "technical debt" metaphor |
| 17 | OWASP Foundation. *OWASP Top Ten*. https://owasp.org/www-project-top-ten/ | Security validation at input boundaries |
| 18 | Parnas, D. (1972). "On the Criteria to Be Used in Decomposing Systems Into Modules." *Communications of the ACM*, 15(12). | Information hiding: decompose by what changes, not by sequence (`design-fundamentals.md` § Abstraction) |
| 19 | Lieberherr, K. & Holland, I. (1989). "Assuring Good Style for Object-Oriented Programs." *IEEE Software*, 6(5). | Law of Demeter: only call methods on self, parameters, owned objects, or direct components (`design-fundamentals.md` § Named Principles) |
| 20 | Fowler, M. (2004). "StranglerFigApplication." martinfowler.com. | Strangler Fig migration pattern (`refactoring.md` § Migration-Scale Moves) |

### Standards & Conventions

| # | Reference | Relevance |
|---|-----------|-----------|
| 21 | Conventional Commits. https://www.conventionalcommits.org/ | Commit message format |
| 22 | Keep a Changelog. https://keepachangelog.com/ | Changelog format |
| 23 | Semantic Versioning. https://semver.org/ | Version numbering. Compatibility surface defined in [`docs/deprecation-policy.md`](deprecation-policy.md). |
| 24 | Michael Nygard. "Documenting Architecture Decisions." *Cognitect Blog*, Nov 2011. | ADR template format |
| 25 | RFC process for proposals larger than a PR. | See [`docs/rfcs/README.md`](rfcs/README.md) |

---

## Knowledge Base Sources

| Topic | Local source of truth |
|-------|-----------------------|
| Workflow and agent routing | [../CLAUDE.md](../CLAUDE.md) |
| Testing conventions | [../knowledge-base/testing.md](../knowledge-base/testing.md) |
| Security conventions | [../knowledge-base/security.md](../knowledge-base/security.md) |
| Architecture and design patterns | [../knowledge-base/design-patterns.md](../knowledge-base/design-patterns.md) |
| Cohesion, coupling, abstraction (property vocabulary) | [../knowledge-base/design-fundamentals.md](../knowledge-base/design-fundamentals.md) |
| Debugging discipline | [../knowledge-base/debugging.md](../knowledge-base/debugging.md) |
| Git workflow | [../skills/git/SKILL.md](../skills/git/SKILL.md) |
| Cognitive health and intent preservation | [../knowledge-base/philosophy.md](../knowledge-base/philosophy.md) § Cognitive Health |
| Agent-first automation patterns | [../knowledge-base/working-agreement.md](../knowledge-base/working-agreement.md) § Agent-First Automation |

---

## Attribution Notes

The playbook references broadly known industry ideas rather than copying proprietary methods or text. This repository adapts naming and structure for its agent workflow, with the canonical rules kept in local markdown files so teams can review and change them.

---

## Related Docs

- [Getting Started](getting-started.md)
- [User Guide](user-guide.md)
- [How-to Guides](how-to/): focused task recipes
- [CLI Reference](cli-reference.md)
- [Known Limitations](limitations.md)
- [Architecture](architecture.md)
- [Governance](../GOVERNANCE.md), [Deprecation Policy](deprecation-policy.md), [RFCs](rfcs/README.md): adopter contract
