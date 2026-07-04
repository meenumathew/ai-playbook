---
id: index
size: medium
tldr: Topic-to-file routing table; load this first to decide which KB file to pull.
load_when: always; first hop for any KB lookup
audience: all
canonical_for: KB routing, topic-to-file map, load-order rule
cross_refs: all KB files
verified: 2026-06-10
---

# Knowledge Base Index

Topic → file routing table. Load on demand: do not inline.

## 30-Second Load Path (Agent-Friendly)

Use this when speed matters and the task is straightforward:

1. Read `CHEATSHEET.md` only.
2. If blocked, open exactly one cited canonical section.
3. Stop when you can act safely.
4. Keep quality gates, security checks, and verification unchanged.

## Loading Rule

Use the smallest source that can change the outcome:

1. **Start with `CLAUDE.md`**: always in context.
2. **Load `CHEATSHEET.md`** for the one-line rule first: covers ~80% of cases.
3. **On cheatsheet miss, search Exact Section Routing** below for the exact topic, then load the canonical file.
4. **Load one file or section at a time**: prefer a cited section over a whole file when tools support ranges.
5. **Stop reading once the rule is actionable.** Do not read conceptual background unless a decision, review finding, or test design needs it.
6. **Never skip required quality gates.** Efficient loading reduces tokens, not standards.

---

## By File

The "Load when" column is each file's `load_when:` frontmatter, verbatim (contract-tested). To change a row, edit the file's frontmatter first, then copy it here.

| File | Tier | Load when |
|------|------|-----------|
| `CLAUDE.md` | Core | Always: workflow, gates, quality tier, DoD, commits, review rules |
| `CHEATSHEET.md` | Core | always; try here before loading any KB file |
| `testing.md` | Task-core | test, TDD, AC coverage, retrofit tests, weak test, test quality, characterization test, test doubles |
| `security.md` | Task-core | auth, secrets, permissions, PII, payments, public API, dependency update, untrusted input, JWT, CORS, CSRF, XSS, SQL injection |
| `design-patterns.md` | Task-core | architecture, domain, service boundary, ports, adapters, hexagonal, DDD, dependency direction, anti-pattern |
| `style-guide.md` | Task-core | naming, file structure, comments, suppression, lint, format, dead code, refactor commit |
| `debugging.md` | Triggered | test fail, bug, regression, build failure, deploy failure, fix attempt, flaky test, root cause |
| `refactoring.md` | Triggered | refactor, smell, structural change, Strangler Fig, Parallel Change, Rule of Three |
| `performance.md` | Triggered | hot path, performance, N+1, caching, data-heavy, collections, latency, DB loop, API loop, profiling |
| `observability.md` | Triggered | logging, metrics, tracing, health check, correlation ID, error reporting, external call |
| `feature-flags.md` | Triggered | dark launch, gradual rollout, kill switch, A/B test, percentage rollout, flag cleanup, flag registry |
| `release.md` | Triggered | release, ship, merge, deploy, post-deploy, smoke test, rollback, version bump, tag, branch protection |
| `regression-and-contracts.md` | Triggered | plan changes, scope changes, code generation, OpenAPI, protobuf, GraphQL, migrations, API breaking change, contract change, behavior regression |
| `incident-response.md` | Triggered | production incident, outage, SEV1, SEV2, postmortem, on-call, triage, war room |
| `quality-gates.md` | Triggered | quality gate, coverage threshold, critical path, mutation score, make quality, make test, CI gate |
| `tool-policy.md` | Triggered | tool policy, permission, host adapter, issue fetch, notifier, vendor-neutral, operation ID, agent ↔ skill |
| `working-agreement.md` | Triggered | collaboration, review size, ownership, disagreement, escalation, agent workflow, operating model |
| `philosophy.md` | Reference | design decision, principle, bounded context, cognitive health, context efficiency, teach-back, AI anti-pattern |
| `design-fundamentals.md` | Reference | cohesion, coupling, abstraction, module property, review finding, design decision, "is this module pulling its weight", LCOM, afferent, efferent, complexity symptom, change amplification, cognitive load, unknown unknowns, software that lasts, strategic vs tactical, design checkpoint |
| `model-tier.md` | Reference | model tier, advisor, executor, model config, escalation, single model setup |
| `doc-linting.md` | Reference | docs, vale, markdownlint, lychee, doc lint fail, Diataxis |
| `testing-techniques.md` | Triggered | property-based, mutation, hypothesis, fast-check, contract test, pact, async test, queue, stream, eventual consistency, frozen time, httpx, respx, testcontainers, pytest-xdist |
| `workspaces/README.md` | Triggered | Story declares `workspace:` frontmatter, monorepo per-package overlays, per-workspace quality tier or language conventions |

The system seeds project-specific files from `templates/` on first use and announces the seed. Never skip a missing KB file silently. ADRs: [`docs/adr/`](../docs/adr/) ← [`templates/adr-template.md`](../templates/adr-template.md).

## Language-specific

| File | Agent loads when |
|------|-----------------|
| `languages/python.md` | PEP 8, type hints, docstrings, ruff, pyright, logging, pydantic: **reference implementation** |
| `languages/testing-python.md` | pytest, fixtures, mocking, parametrize: **reference implementation** |
| `languages/<lang>.md` | Auto-detected from project config (`go.mod`, `pom.xml`, `Cargo.toml`, etc.): seed from `templates/language-conventions-template.md` on first use |
| `languages/testing-<lang>.md` | Loaded alongside the language file: seed from `templates/testing-language-template.md` on first use |

To add a new language: copy `templates/language-conventions-template.md` to `languages/<lang>.md`. Use `languages/python.md` as the reference.

## Skills

| File | Agent loads when |
|------|-----------------|
| `skills/git/SKILL.md` | Commits, branches, PRs, worktrees, squash, merge conflict resolution |
| `skills/host-adapter/SKILL.md` | Host PR/MR operations across GitHub, GitLab, Bitbucket Cloud, Gitea/Forgejo |
| `skills/notifier/SKILL.md` | Outbound notifications (Slack, email, webhook) emitted by release-captain and incident-responder; default provider `none` |
| `skills/issue-fetch/SKILL.md` | Issue tracker reference received (Jira, GitHub, GitLab, Bitbucket, Linear) |
| `skills/intent-interview/SKILL.md` | Capturing intent on a vague request: five anchors, propose-then-ask, prompt minimization (cites CLAUDE.md) |
| `skills/story-writing/SKILL.md` | INVEST validation, sizing, story file creation |
| `skills/retrospective/SKILL.md` | Session-end learning loop |

## Templates

| File | Agent loads when |
|------|-----------------|
| `templates/story-template.md` | story-refiner writes a `story` or `chore`: new behaviour or tidy/upkeep |
| `templates/story-bug-template.md` | story-refiner writes a `bug`: fixing broken behaviour with regression coverage |
| `templates/story-spike-template.md` | story-refiner writes a `spike`: timeboxed learning, no code on main, no AC |
| `templates/research-template.md` | story-refiner writes research |
| `templates/plan-template.md` | slice-planner writes plan |
| `templates/review-template.md` | diff-reviewer writes review; code-inspector writes audit |
| `templates/how-to-template.md` | docs-maintainer writes how-to docs |
| `templates/runbook-template.md` | docs-maintainer writes runbooks |
| `templates/domain-language-template.md` | seed `knowledge-base/domain-language.md` on first use |
| `templates/quality-gates-template.md` | seed `knowledge-base/quality-gates.md` on first use |
| `templates/limitations-template.md` | seed `docs/limitations.md` on first use |
| `templates/feature-flag-registry-template.md` | seed `knowledge-base/feature-flag-registry.md` on first use |
| `templates/language-conventions-template.md` | Blank structure for any language: seed `knowledge-base/languages/<lang>.md` from this |
| `templates/testing-language-template.md` | Blank structure for any language test runner: seed `knowledge-base/languages/testing-<lang>.md` from this |
| `templates/adr-template.md` | docs-maintainer seeds ADRs under `docs/adr/` |
| `templates/changelog-template.md` | docs-maintainer seeds `CHANGELOG.md` (Keep a Changelog 1.1.0 + SemVer) |
| `templates/module-readme-template.md` | docs-maintainer seeds module-level `README.md` (purpose, responsibilities, usage, key classes, deps, limitations) |
| `templates/postmortem-template.md` | incident-responder writes the blameless postmortem under `incidents/INC-YYYY-MM-DD-slug.md` |
| `templates/importlinter-template.toml` | seed an `importlinter` config to enforce `design-patterns.md` § Architecture Layers in CI |
| `templates/.ai-playbook.toml.example` | adopter copies to `.ai-playbook.toml` to configure host, issue tracker, notifier, and review options |

---

## Exact Section Routing

| Topic | Where |
|-------|-------|
| Definition of Done | `CLAUDE.md` § Definition of Done |
| Conventional Commits | `CLAUDE.md` § Commits + `skills/git/SKILL.md` |
| Quality tier | `CLAUDE.md` § Quality Tier |
| Model tier (advisor / executor) | `CLAUDE.md` § Model Tier + `model-tier.md` |
| Free / local-only model setup | `model-tier.md` § Single-Model Setups |
| Model swap (cloud, local, mixed, or single-model) | `model-tier.md` § Capability Mapping |
| Read budget | `CLAUDE.md` § Shared Rules |
| Tidy first/after/later/never | `CHEATSHEET.md` § Decision Guide |
| When to go back | `CHEATSHEET.md` § When to Go Back |
| Intent anchors | `CLAUDE.md` § Shared Rules |
| Architecture layers | `CLAUDE.md` § Architecture |
| Context7 | `CLAUDE.md` § Tools |
| Tool policy / per-agent permissions | `tool-policy.md` § Per-Agent Matrix |
| Vendor-neutral operation IDs (`host.pr.create`, `notify(…)`) | `tool-policy.md` § Vendor-Neutral Operation IDs |
| Spike path | `CLAUDE.md` § Workflow |
| PR size limit (≤ 400 lines) | `working-agreement.md` § Code Review Norms |
| Pairing modes (Human+AI / Solo+AI review) | `working-agreement.md` § Pairing Modes |
| Disagreement protocol | `working-agreement.md` § Disagreement Protocol |
| Never log `str(e)` / `exc_info=True` | `security.md` § Data Handling |
| Suppression pragmas (`# noqa`, `# type: ignore`, `pytest.skip`) | `style-guide.md` § No Suppression Without Justification |
| Correlation IDs / structured logging | `observability.md` § What to Log |
| Sensitive data masking | `observability.md` § Sensitive Data Masking |
| JWT validation | `security.md` § Authentication & Authorisation |
| CSRF / SSRF / mass assignment / path traversal / insecure deserialization | `security.md` § Input Validation (web threat table) |
| CORS / rate limiting / API headers | `security.md` § API Security |
| STRIDE threat modeling (design-phase) | `security.md` § Design-Phase Threat Modeling (STRIDE) |
| AI safety: prompt injection / model drift / human accountability / treat AI input as data not instructions | `security.md` § AI Safety |
| Git worktrees (parallel sprints) | `skills/git/SKILL.md` § Worktrees |
| Dependency scanning (pip-audit, npm audit) | `security.md` § Dependencies & Supply Chain |
| Strangler Fig / Parallel Change | `refactoring.md` § Migration-Scale Moves |
| Anti-corruption layer (ACL) | `design-patterns.md` § Strategic DDD Patterns |
| Vendor-neutral by design: operation IDs (agent ↔ skill) and capability names (story ↔ implementation) | `design-patterns.md` § Vendor-Neutral by Design |
| TODO priority annotations (TODO(0)–TODO(3)) | `style-guide.md` § TODO Annotations |
| Pydantic input validation | `languages/python.md` § Input Validation (Pydantic v2) |
| Pydantic settings | `languages/python.md` § Environment Variables |
| Stuck on a bug, 2+ fixes failed | `debugging.md` § Iron Law + § 3-Fix Architectural Stop Rule |
| Build a feedback loop (how to reproduce) | `debugging.md` § Phase 1: Investigate: Build a Feedback Loop |
| Backward tracing | `debugging.md` § Backward Tracing |
| Verification before claiming fixed | `debugging.md` § Verification |
| What not to test (decision line) | `testing.md` § What Not to Test |
| Property-based testing | `testing-techniques.md` § Property-Based Testing |
| Async / event-driven testing (message consumers, eventual consistency, streaming response assertions) | `testing-techniques.md` § Async and Event-Driven Test Patterns |
| Which testing mode to use | `testing.md` § Choose The Testing Mode |
| Test independence / no shared mutable state / no control flow in tests | `testing.md` § Test Quality Rules |
| Characterization tests | `testing.md` § Retrofitting Tests onto Existing Untested Code |
| Test-story cycle | `testing.md` § Test-Story Cycle: When the Deliverable Is Tests |
| Integration tests (external services) | `testing.md` § Test Types Quick Guide |
| Post-deploy / post-fix tests (E2E / smoke / sanity) | `testing.md` § Post-Deploy Tests |
| Acceptance tests (AT) | `testing.md` § Acceptance Test (AT) Standards |
| 3-layer pyramid | `testing.md` § Test Types Quick Guide |
| Testability | `testing.md` § When Tests Are Hard to Write (Testability) |
| Test doubles / mocking | `testing.md` § Test Doubles |
| Mock at boundaries only | `testing.md` § Mock at boundaries only |
| Vertical vs horizontal TDD | `testing.md` § TDD Discipline: Vertical, Not Horizontal |
| Mutation testing | `testing-techniques.md` § Mutation Testing |
| Contract testing | `testing-techniques.md` § Contract Testing |
| Module depth / shallow modules / deletion test / two-adapter rule for ports | `design-patterns.md` § Module Depth and Seams |
| When to write an ADR | `docs/adr/README.md` § ADR Decision Criteria + `templates/adr-template.md` |
| How-to doc format | `templates/how-to-template.md` |
| Runbook format | `templates/runbook-template.md` |
| Bounded contexts | `philosophy.md` § Bounded Contexts + `design-patterns.md` § Strategic DDD Patterns |
| Cohesion (definition + detection signals) | `design-fundamentals.md` § Cohesion |
| Coupling (afferent/efferent, detection signals) | `design-fundamentals.md` § Coupling |
| Abstraction (deep vs shallow, information hiding) | `design-fundamentals.md` § Abstraction |
| Building software that lasts / complexity symptoms (change amplification, cognitive load, unknown unknowns) / strategic vs tactical / design it twice / what to hide | `design-fundamentals.md` § Building Software That Lasts |
| Design checkpoints (new name, new parameter, new import, hard-to-write test, ripple count) + three-question design check | `design-fundamentals.md` § Practical Application |
| Dual-message exceptions (CWE-209) | `security.md` § Error Response Pattern + `design-patterns.md` § Error Handling |
| Project quality gates | `knowledge-base/quality-gates.md` (seed from `templates/quality-gates-template.md` if missing) |
| Feature flags | `feature-flags.md` |
| Flag categories (release / experiment / ops / permission) | `feature-flags.md` § Flag Categories |
| Flag registry (live flags, owners, cleanup dates) | `feature-flags.md` § Flag Registry → `knowledge-base/feature-flag-registry.md` (seed from `templates/feature-flag-registry-template.md` if missing) |
| DORA delivery metrics (deploy frequency, lead time, change failure rate, MTTR) | `release.md` § Delivery Metrics (DORA) |
| Golden signals / RED / USE metric methods | `observability.md` § Metrics |
| Legacy / diff coverage gate (`diff-cover`) | `quality-gates.md` § Coverage Policy |
| Python conventions | `languages/python.md` |
| Python Protocol ports / TypedDict / async patterns | `languages/python.md` § Reference Notes |
| Python pytest conventions | `languages/testing-python.md` |
| Python pytest techniques (async / time-dependent / HTTP mocking / testcontainers / parallel xdist) | `testing-techniques.md` § Python pytest Techniques |
| Session-end learning | `skills/retrospective/SKILL.md` |
| Release gates / merge strategies / post-deploy smoke / rollback / hotfix | `release.md` |
| Validate existing behaviour / regression detection / code-generation completeness / contract preservation (UFX-2140 pattern) | `regression-and-contracts.md` |
| Severity matrix / war-room rules / blameless postmortem / follow-up tracking | `incident-response.md` |
| Deploy-time signals (error rate, latency, saturation thresholds) | `observability.md` § Deploy-Time Signals |
| Incident telemetry checklist | `observability.md` § Incident Telemetry |
| Host PR/MR operations (`pr.diff`, `pr.review`, `pr.create`, `pr.merge`, `pr.checks`) | `skills/host-adapter/SKILL.md` |
| `.ai-playbook.toml [host]` config | `skills/host-adapter/SKILL.md` § Configuration |
| GitLab issue fetch | `skills/issue-fetch/SKILL.md` § GitLab Adapter |
| Bitbucket Cloud issue fetch | `skills/issue-fetch/SKILL.md` § Bitbucket Adapter |
| Outbound notifications (Slack, email, webhook) | `skills/notifier/SKILL.md` |
| Notifier event names (release_shipped, smoke_warn, smoke_fail, incident_sev1/2, incident_resolved, postmortem_ready) | `skills/notifier/SKILL.md` § Canonical event names |
| Telemetry hook wire-up + jq queries | `knowledge-base/observability.md` § Agent Telemetry |
