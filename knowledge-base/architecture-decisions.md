---
id: architecture-decisions
size: medium
tldr: Profile data and workload needs before choosing the simplest sufficient architecture; require evidence for operational complexity.
load_when: architecture choice, system structure, deployment model, data ownership, distributed system, cloud architecture, operational complexity, quality attribute, workload profile
audience: all
canonical_for: architecture decision framing, data-first workload profiles, quality-attribute trade-offs, evidence for operational complexity
cross_refs: design-patterns.md, security.md, performance.md, observability.md, philosophy.md
verified: 2026-08-01
---

# Evidence-Based Architecture Decisions

## Agent Use

- **Read first:** Architecture-Impact Trigger, Start With the Data, Workload Quality Attributes,
  Evidence for Operational Complexity, Record the Decision.
- **Load deeper only on trigger:** use the linked security, performance, observability, and design
  sources only when their attribute can change the decision.
- **Skip for:** routine internal refactoring, simple CRUD, scripts, and glue code whose deployment,
  data ownership, process boundaries, and operational characteristics stay unchanged.

Architecture is a set of consequential trade-offs, not a catalogue of fashionable patterns. Start
from the workload, choose the simplest deployable architecture that satisfies its known needs, and
add operational complexity only when evidence makes the simpler choice insufficient.

## Architecture-Impact Trigger

Apply this framework when a proposed change materially affects at least one of:

- System or module structure across a process or ownership seam
- Deployment model, runtime topology, or independent release boundaries
- Data ownership, consistency, retention, residency, or sensitive-data exposure
- Reliability, throughput, latency, recovery, or availability targets
- Operational responsibility, infrastructure cost, or failure diagnosis

Do not run a questionnaire mechanically. Profile only facts capable of changing the design. Follow
`CLAUDE.md` § Shared Rules: infer high-confidence defaults, record reversible assumptions, and ask
one material question at a time.

## Start With the Data

Before naming services, queues, databases, or deployment platforms, establish the data shape:

| Concern | Decision input |
|---|---|
| Meaning and ownership | Which domain owns each fact, and who may change it? |
| Valid state | Which invariants and state transitions must always hold? |
| Access | Which reads and writes dominate, and where do they originate? |
| Consistency | Which operations require immediate consistency, and which may converge later? |
| Lifecycle | What is created, retained, archived, exported, or deleted? |
| Sensitivity | Which data is confidential, regulated, or unsafe to expose in telemetry? |
| Scale | What are current and credible near-term volume, growth, and concurrency? |

Use domain vocabulary from `domain-language.md`. Domain-heavy work continues into
`design-patterns.md` § DDD Tactical Patterns; ordinary data-processing work does not need DDD
ceremony.

## Workload Quality Attributes

Capture an attribute only when it can distinguish viable options. A target beats an adjective:
"recover within four hours" is actionable; "highly reliable" is not.

| Attribute | Minimum decision evidence | Canonical detail |
|---|---|---|
| Reliability | Critical journeys, tolerated failure, recovery objective, data-loss tolerance | `observability.md` § SLOs & SLIs |
| Security and privacy | Trust boundaries, sensitive data, permissions, compliance constraints | `security.md` § Design-Phase Threat Modeling |
| Performance and scale | Expected peak, latency/throughput target, data size, growth assumption | `performance.md` § Load & Stress Testing |
| Operability | Ownership, deploy/rollback path, failure diagnosis, dependency handling | `observability.md` |
| Cost | Budget or relative cost constraint, idle footprint, main scaling driver | Project constraint or ADR |

Requirements conflict. More replicas may improve recovery while increasing cost and operational
load. Record the trade-off instead of claiming that one option optimizes every attribute.

## Evidence for Operational Complexity

Prefer the simplest deployable architecture that meets the recorded workload profile. The burden
of proof belongs to the more operationally expensive option.

Examples that require explicit justification include independently deployed services, message
brokers, multi-region topology, orchestration platforms, event sourcing, and separate read/write
models. This is not a ban and not a closed list.

Valid evidence names a current constraint, for example:

- Independent scaling backed by measured or forecast load
- Independent deployment required by team or release ownership
- Fault isolation needed to satisfy a stated recovery or availability objective
- Asynchronous processing required by latency, throughput, or dependency behaviour
- A compliance, residency, or security boundary

"Industry standard", "future-proof", "cloud native", or possible future growth is not evidence.
When a simpler option satisfies all known requirements, choose it. When an unknown would materially
change the decision, ask; otherwise record the smallest reasonable assumption.

## Compare Viable Options

For each credible option, record:

1. Which workload requirements it satisfies
2. Important benefits and costs in business terms
3. Failure modes and operational responsibilities
4. Constraints it cannot satisfy
5. Why rejected alternatives lost

Use `design-patterns.md` only after the need is clear. A pattern is an implementation response to a
constraint, not the starting requirement.

## Record the Decision

Research and plans record ordinary, reversible choices and their assumptions. Mark an **ADR candidate**
only when all existing criteria hold: the choice is hard to reverse, surprising without context,
and involves a real trade-off. The canonical criteria and `docs-maintainer` handoff live in
[`docs/adr/README.md`](../docs/adr/README.md) § ADR Decision Criteria.

Reviewers compare the implementation with the recorded workload profile and accepted trade-offs.
Inspectors look across files for missing evidence, unjustified operational complexity, contradictory
assumptions, and drift from active ADRs.
