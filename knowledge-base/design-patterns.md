---
id: design-patterns
size: medium
tldr: Domain inward; pure domain, no framework imports; ports/adapters; pick patterns only when they solve a real problem.
load_when: architecture, domain, service boundary, ports, adapters, hexagonal, DDD, dependency direction, anti-pattern
audience: all
canonical_for: architecture layers, hexagonal architecture, DDD tactical patterns, dependency inversion
cross_refs: philosophy.md, refactoring.md, security.md
verified: 2026-06-08
---

# Design Patterns

Use patterns when they solve a real problem; prefer the simplest solution otherwise. For simple CRUD or glue code: clear boundaries and testability without forcing layers.

## Agent Use

- **Read first:** Architecture Layers, Module Depth and Seams, Preferred Patterns, Anti-Patterns.
- **Load deeper only on trigger:** DDD tactical/strategic patterns, event-driven guidance, or framework-specific convention conflicts.

---

## Hexagonal Architecture

Default for domain-heavy systems: **Ports and Adapters** (Cockburn). Domain is pure: no framework imports, no I/O. Infrastructure implements ports defined by the domain. Deps flow inward only.

---

## Architecture Layers

Dependencies flow inward only: inner layers never import from outer layers.

| Layer | Contains | Must NOT contain |
|-------|----------|-----------------|
| **Domain** | Entities, VOs, Aggregates, Domain Events, Specifications, Ports (interfaces) | DB calls, HTTP, framework imports, flag SDK |
| **Service** | Use cases, orchestration, transaction boundaries, flag evaluation | Business rules, SQL, direct infrastructure calls |
| **Infrastructure** | Repos, adapters, DB sessions, HTTP clients, flag SDK wrappers | Business logic, domain rules |
| **Entry point** | Controllers, serializers, request validation | Business logic, domain objects instantiated directly |

**Violation rule:** if a domain object imports anything from service or infrastructure → **Must Fix**.

**Mechanical enforcement.** The rule is honor-system without a linter. Python: [`templates/importlinter-template.toml`](../templates/importlinter-template.toml) ships a starter config with three contracts (layered direction, domain purity, optional bounded-context independence). Other stacks: dependency-cruiser (JS/TS), ArchUnit (Java), go-cleanarch (Go), NetArchTest (C#). Tool changes; rule doesn't.

---

## Module Depth and Seams

> Property vocabulary behind module shape: `design-fundamentals.md` § Cohesion + § Abstraction.

Vocabulary for evaluating *whether a module pulls its weight*. Use these terms exactly: don't substitute "boundary", "API", "service", or "component". Source: Ousterhout (depth), Feathers (seams).

| Term | Meaning |
|------|---------|
| **Module** | Anything with an interface and an implementation: function, class, package, slice. Scale-agnostic. |
| **Interface** | Everything a caller must know to use the module: types, invariants, error modes, ordering, config. Not just the type signature. |
| **Implementation** | The code inside. |
| **Depth** | Leverage at the interface: how much behaviour callers get per unit of interface they have to learn. |
| **Seam** | A place where you can change behaviour without editing in place. Where an interface lives. (Avoid "boundary": overloaded with bounded context.) |
| **Adapter** | A concrete thing satisfying an interface at a seam. |

### Deep vs Shallow

| Module | Interface | Implementation | Verdict |
|--------|-----------|----------------|---------|
| **Deep** | Small | Large | Pulls weight: preferred |
| **Shallow** | Nearly as complex as the implementation | Small | Pass-through: flag in review |

**Why deep:** callers learn a small interface, get much behaviour. Tests assert through that interface, survive internal refactors. Bugs and changes concentrate in one place.

### Heuristics

| Heuristic | How to apply |
|-----------|-------------|
| **Deletion test** | Imagine deleting the module. Does complexity vanish (shallow: was hiding nothing) or reappear across N callers (deep: earned its keep)? |
| **One adapter = hypothetical seam, two = real seam** | Don't introduce a port unless ≥2 adapters justify it (typically prod + test/in-memory). A single-adapter port is just indirection. |
| **The interface is the test surface** | If you need to test past the interface, the module is the wrong shape: pull complexity behind it. |

### When to deepen

- Tests reach into private state to verify behaviour → seam is too high; pull complexity behind the interface
- Pure functions extracted "for testability" but real bugs live in how they're called → bad locality; merge them and test through the caller
- Tightly-coupled modules leak across their seams → wrong split; merge or redraw

**Seam vs bounded context:** seam is technical (where an interface lives). Bounded context is domain (where a model is valid). Don't conflate. Detail: `philosophy.md` § Bounded Contexts.

---

## DDD Tactical Patterns

`core` = use by default once real business rules justify a domain layer (never force onto simple CRUD or glue: see the intro rule). `advanced` = reach for only when the simpler pattern isn't enough.

| Pattern | Tier | What it is | Agent enforcement |
|---------|------|-----------|------------------|
| **Entity** | core | Object with identity that persists over time | Equality by ID, not attributes; mutable state |
| **Value Object** | core | Object defined entirely by its attributes | Immutable, equality by value; no ID field. **Prefer VO over Entity when in doubt.** |
| **Aggregate** | core | Cluster of entities/VOs with a single root entity | All access through the root; one repo per aggregate. **Keep aggregates small**: it should load into memory and complete a domain operation in a few milliseconds; if the object tree is deep or loading is slow, split it. |
| **Domain Event** | core | Record that something significant happened | Past tense naming (`OrderPlaced`, `PaymentFailed`); immutable |
| **Port** | core | Interface the domain defines for infrastructure needs | Lives in domain layer; infrastructure implements it |
| **Factory** | advanced | Encapsulates complex object/aggregate creation | Protects invariants during construction; use when creation logic doesn't belong in a constructor |
| **Specification** | advanced | Composable business rule object | Combine with AND/OR/NOT; keeps complex rule logic in domain layer, out of services |
| **Unit of Work** | advanced | Tracks changes in a transaction, commits or rolls back atomically | One per request/transaction; prevents partial saves; pairs with Repository |

---

## Preferred Patterns

> **Two tiers:** Universal principles apply to all projects: agents enforce them. Language/framework conventions are the default but can be overridden in `knowledge-base/languages/<lang>.md` when the framework has its own established pattern.

### Universal principles: enforced where a domain layer exists

| Pattern | When to use | Agent enforcement |
|---------|------------|------------------|
| **Repository** | Separating data access from business logic in a layered codebase | **One repo per aggregate root**; returns domain objects, never raw DB rows. ActiveRecord-style frameworks (Django ORM, Rails) are a legitimate framework convention: document in `languages/<lang>.md` instead of fighting the framework |
| **Strategy** | 3+ conditional branches doing similar things *and* the variants change independently | Consider polymorphism over `if/elif` chains; a flat `match`/dict dispatch is fine when variants are stable and simple |
| **Decorator** | Cross-cutting concerns (logging, caching, retry) | Compose at runtime: never modify the wrapped class |
| **CQS** | Method both mutates state and returns data | Queries must be side-effect-free; commands return void or a result ID only. Established idioms (`pop()`, fluent builders, upsert-returning-row) are accepted exceptions: flag only new APIs that mix the two without an idiom to point at |

### Language/framework conventions: enforced by default, override in language file

| Pattern | Default | Escape hatch |
|---------|---------|-------------|
| **Dependency Injection** | Constructor injection: explicit, testable, no magic | Framework-managed DI (Spring `@Autowired`, NestJS `@Injectable`, Angular) may use field/setter injection: document the framework choice in `languages/<lang>.md` |
| **Composition over inheritance** | Favour composing objects over deep class hierarchies | Shallow inheritance (1 level) for framework base classes (`BaseModel`, `TestCase`) is acceptable: document if your framework requires it |

### Standard patterns: use as needed, no enforcement

| Pattern | When to use |
|---------|------------|
| **Factory Method** | Creating objects without specifying exact class (reports, parsers) |
| **Builder** | Complex objects with many optional fields (config, queries, test data) |
| **Adapter** | Wrapping external APIs or converting data formats |
| **Facade** | Hiding subsystem complexity behind a simple interface |

---

## Vendor-Neutral by Design

The playbook treats **vendor neutrality as a design discipline**, not a renaming exercise. The same principle shows up at two layers: agent ↔ skill (operation IDs) and story ↔ implementation (capabilities). The contract is the stable name; the vendor is interchangeable.

### Layer 1: Vendor-Neutral Operation IDs (agent ↔ skill)

When an agent needs to talk to an external tool family: git host, notifier, issue tracker, secret store, registry: call a **dotted operation ID**, never a vendor command. The skill maps the operation ID to whatever provider `.ai-playbook.toml` selects.

| Operation ID | Provider examples | Skill |
|---|---|---|
| `host.pr.create`, `host.pr.merge`, `host.pr.checks`, `host.pr.diff`, `host.pr.review` | GitHub `gh`, GitLab `glab`, Bitbucket REST, Gitea `tea` | `skills/host-adapter/SKILL.md` |
| `notify(event, …)` with canonical events (`release_shipped`, `smoke_fail`, `incident_sev1`, …) | Slack, email, webhook, `none` | `skills/notifier/SKILL.md` |
| `issue.fetch(<ref>)` with provider inferred from ref shape or config | Jira, GitHub, GitLab, Bitbucket, Linear | `skills/issue-fetch/SKILL.md` |

**Why this is a separate principle from Adapter / ACL:**

- *Adapter* converts one interface into another at one boundary; *ACL* defends a domain from an external model. **Vendor-neutral operation ID** is the **stable name** the rest of the playbook commits to: it survives provider swaps, lets `.ai-playbook.toml` move config out of agents, and lets escalation triggers fire on the operation, not the vendor command.
- It is the **citable contract** between agents and skills. Agents may write `host.pr.merge`; they may not write `gh pr merge`.

**Rules.**

- Operation IDs are dotted, lowercase, verb-last (`host.pr.create`, not `createPullRequest` or `host.pr.open`).
- Each skill lists its operation IDs in `## Operations` headings so agents and reviewers can grep them.
- Adding a new provider is implementing the skill's operation IDs against the new vendor: never adding new operation IDs in the agent.
- Adding a new operation ID lives in the skill with a `## Adding a New Operation` note explaining why the existing set was insufficient. Three new operation IDs of the same shape across skills → consider a new operation family (a new skill).

**When to introduce a new operation family.** Three independent agents reaching for vendor-specific commands of the same shape (`docker push` / `crane push`, `aws s3 cp` / `gsutil cp`, `vault write` / `op write`). The `Rule of Three` (`refactoring.md` § When to Refactor) applies: extract the operation family once you have three call sites that would otherwise drift.

**Anti-patterns.** Agents that call `gh`, `glab`, `slack-cli`, `jira-cli`, `op`, `vault`, `kubectl`, `aws`, `gcloud` directly. Reviewers must flag these as **Must Fix** with a citation to this section.

### Layer 2: Vendor-Neutral Adopter Artifacts (story ↔ implementation)

Adopter-facing artifacts name **capabilities**, not products, by default: same reason as Layer 1: the artifact is the stable contract; the vendor is interchangeable.

| Artifact | Default | Vendor name allowed when |
|---|---|---|
| `knowledge-base/domain-language.md` | Capability vocabulary only ("identity store", "object store", "chat notifier", "issue tracker"). | Never: the glossary is the most vendor-neutral file. Vendors live in ADRs. |
| Story body + AC | Capabilities and observable behaviour. | The vendor IS the constraint: infra mandate, compliance lock-in, integration contract, or named in an ADR. Cite the ADR or constraint inline (`skills/story-writing/SKILL.md` § Acceptance Criteria). |
| Plan steps + research findings | Capabilities at the design level; concrete vendor in the implementation step. | Always allowed at the implementation step (it has to call a real API). |
| ADRs | Always vendor-explicit. | ADRs exist to capture *why this vendor, what alternatives*: that's their job. |

**Heuristic.** If swapping the vendor would force a story rewrite, the story leaked. Rewrite to the capability and let the plan name the vendor: *"Send order-confirmation event to the chat notifier"* (story) vs *"Post to Slack `#orders` via the `notifier(release_shipped, …)` op"* (plan).

**Why not stricter.** Adopters routinely ship vendor-specific products and the rule above isn't a renaming exercise: over-enforcement creates churn ("S3 bucket" → "object container") with no benefit. The exception ("when the vendor IS the constraint") is load-bearing; do not tighten it.

**Reviewer prompt.** Story names a product (`Slack`, `Jira`, `S3`, `Stripe`) without an ADR or constraint citation → ask: *"Should this be the capability name? If the vendor is genuinely fixed, point to the ADR or constraint."* Not always a Must Fix: depends on whether the vendor is fixed by an external commitment.

**Make it mechanical when you can.** The OpenAPI precedent (Layer 1) is enforceable by a contract test: a CI check that grep's the spec for `operationId` values matching `*Auth0*` / `*Okta*` / vendor patterns and fails if the public name leaks. The same trick applies to stories: a contract test over `stories/**/*.md` that flags product names outside an `## ADRs` / `## Constraints` block. Optional, recommended for adopters whose stories accumulate vendor leakage.

---

## Strategic DDD Patterns

| Pattern | Tier | What it is | Agent action |
|---------|------|-----------|-------------|
| **Bounded Context** | core | Explicit boundary where a domain model is valid | Same word, different meaning → flag it, define the boundary. See `philosophy.md` § Bounded Contexts. |
| **Anti-Corruption Layer (ACL)** | core | Translation layer between your domain and an external/legacy model | Integrating with any external system → require ACL to prevent foreign concepts leaking in |
| **Context Map** | advanced | Diagram documenting how bounded contexts relate | Before building integrations across multiple bounded contexts |
| **Shared Kernel** | advanced | A subset of the model shared between two teams | Changed only by explicit agreement: minimise its size |

---

## Event-Driven Architecture Decisions

Event-driven implementation patterns are **project architecture choices**, not universal playbook defaults.

| Pattern | Use when | Agent action |
|---------|----------|--------------|
| **Event sourcing** | The audit log is the source of truth and rebuilding state from events is a business requirement | Require an ADR before implementation |
| **CQRS** | Read and write models have materially different scaling, latency, or shape needs | Require an ADR; avoid for simple CRUD |
| **Saga orchestration** | A long-running workflow spans multiple services and needs central coordination/compensation | Require an ADR naming the orchestrator and compensation rules |
| **Saga choreography** | Services can react independently to events without a central coordinator | Require an ADR showing ownership, failure handling, and observability |

Minimum ADR content for any of these patterns:

- Why the simpler synchronous/domain-service design is insufficient
- Failure model: retries, idempotency, dead letters, compensation
- Observability: correlation IDs, event IDs, tracing, replay/debug path
- Testing strategy: handler ATs, broker integration tests, and E2E/smoke coverage

See `knowledge-base/testing-techniques.md` § Async and Event-Driven Test Patterns.

---

## Error Handling: Dual-Message Exceptions

Custom base exception carries two fields: `message` (client-safe, generic: "Database service temporarily unavailable") and `internal_message` (full diagnostics: "DynamoDB get_item failed for user_id=X, tenant=Y: ConditionalCheckFailedException"). Constructor enforces both. Each subclass sets its default client message. Handlers log `internal_message` with `exc_info=True`, return only `message`.

Makes info-leak prevention structural instead of per-handler sanitization. Aligns with CWE-209.

**Enforcement:** flag exception classes exposing diagnostic details in the client-facing message, or handlers returning `internal_message` / `str(e)`.

---

## Anti-Patterns: Flag in Review

> Each anti-pattern below is a symptom of low cohesion or high coupling: see `design-fundamentals.md` for the underlying property.

| Anti-pattern | Agent action |
|-------------|-------------|
| **Large Class (God Object)**: classes that know or do too much | Split into focused, single-responsibility classes |
| **Inquisitive Code**: reaching into objects to inspect state and decide on their behalf | Make code **assertive**: ask `order.is_eligible()`, don't inspect `order.status` and `order.items` from outside (Law of Demeter) |
| **Premature Abstraction**: patterns or layers before you need them | Wait for the pattern to emerge (`refactoring.md` § When to Refactor: Rule of Three) |
| **Primitive Obsession**: raw `str`/`int`/`float` for domain concepts | Create Value Objects: `UserId`, `Money` |
| **Anemic Domain Model**: domain objects with only getters/setters; logic lives in services | Move business rules into the domain object; services orchestrate, they don't implement rules |

**Inquisitive vs assertive: worked example:**

```python
# Inquisitive: the caller reaches in and decides on the order's behalf
if order.status == "paid" and order.items and not order.refunded:
    ship(order)

# Assertive: the rule lives on the object; callers just ask
if order.is_eligible_for_shipping():
    ship(order)
```

AI workflow anti-patterns (Silent Misalignment, Flying Blind, Sunk Cost): `philosophy.md` § AI Workflow Anti-Patterns.
