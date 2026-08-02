---
id: domain-language
size: small
tldr: "Project glossary: define AI Playbook terms here before using them in stories and plans"
load_when: term definition, glossary, naming, vocabulary, ubiquitous language, what does <term> mean, term drift
audience: all
canonical_for: project domain vocabulary, glossary, term disambiguation, bounded context names
cross_refs: design-patterns.md, philosophy.md
verified: 2026-07-23
---

# Ubiquitous Language: Project Vocabulary

The shared language used across the CLI, agents, tests, and documentation.

## Agent Use

- **Read first:** Terms, then Ambiguities Resolved when planning deployment or workflow changes.
- **Update when:** a shipped capability introduces a new playbook concept or changes an existing definition.
- **Keep vendor-neutral:** describe capabilities and playbook concepts, not product-specific implementations.

---

## Terms

| Term | Definition | Aliases to avoid |
|------|------------|------------------|
| **Adopter** | A project or team that installs and uses the AI Playbook. | customer, downstream repo |
| **Agent** | A named workflow role with bounded inputs, outputs, tool policy, and handoff rules. | bot, persona |
| **Artifact** | A durable workflow document, such as a story, research note, plan, review, audit, or postmortem. | output, generated file |
| **Deployment Record** | The target-local record of the playbook version, tool, scope, and source fingerprints actually installed. | version file, lockfile |
| **Deployment Target** | The adopter project directory and tool-specific surface into which playbook content is installed. | destination repo, output folder |
| **Metrics backend** | The team-selected external system that receives exported usage events; a capability name, with the vendor bound only at the adapter. | Datadog (in AC/stories), dashboard tool |
| **Pack** | A versioned extension that adds or overrides a bounded set of playbook content subject to compatibility rules. | plugin, bundle |
| **Session-end hook** | The tool lifecycle hook (`harness/telemetry.sh`) that records one usage event when a session ends; makes no network calls and never blocks the host tool. | Stop hook (Claude-specific), telemetry script |
| **Skill** | Reusable procedural guidance or an adapter invoked by agents for a specific capability. | helper, utility |
| **Usage event** | One privacy-minimal record per session end: timestamp, source tool, approximate turns, best-effort active agent. Never tokens, session IDs, or content. | telemetry record, log entry |
| **Usage log** | The machine-local, gitignored JSONL file of usage events (`.claude/usage.jsonl` / `.codex/usage.jsonl`), rotated with gzipped archives. | usage.jsonl (in stories/AC) |

---

## Relationships

Cardinality and lifecycle between terms:

- An **Adopter** can maintain one or more **Deployment Targets**.
- A **Deployment Target** has at most one current **Deployment Record** per tool.
- An **Agent** can invoke zero or more **Skills** and can produce one or more
  **Artifacts**.
- A **Pack** can contribute agents, skills, templates, and knowledge-base
  content to a deployment.

---

## DDD Building Blocks

Universal definitions live in `design-patterns.md` § DDD Tactical Patterns. Record what each concept means **in this project**:

| Concept | What it means here | Example |
|---------|-------------------|---------|
| **Entity** | An artifact whose identifier persists while its status changes. | A story moving from ready to in-progress to done |
| **Value Object** | An immutable value compared by meaning rather than identity. | A semantic version or deployment scope |
| **Aggregate** | A consistency boundary updated as one unit. | A deployment record and its recorded source fingerprints |
| **Domain Event** | A meaningful completed workflow transition. | A release shipped or an incident resolved |
| **Repository** | Storage for durable workflow or deployment state. | The target-local deployment record |
| **Port** | A vendor-neutral capability boundary used by an agent or service. | `host.pr.create` or `notify(event, message)` |

---

## Ambiguities Resolved

| Term | Possible meanings | Chosen meaning here | Notes |
|------|-------------------|---------------------|-------|
| Agent | Source definition / deployed tool file / active runtime role | Use **Agent definition**, **deployed agent**, or **active agent** when the distinction matters. | The unqualified term means the workflow role. |
| Target | Supported AI tool / adopter directory | Use **tool target** or **deployment target** explicitly. | Never infer one from the other. |
| Artifact | Any generated file / approval-gated workflow document | The durable workflow document. | Tool-generated caches and logs are not artifacts. |

---

## Anti-Glossary

<!-- Universal naming bans (Process, Manager, Helper, Utils, Handle, Data, Info) live in style-guide.md § Naming.
     Record only PROJECT-SPECIFIC banned terms here: words that cause confusion in THIS domain. -->

| Banned term | Why | Use instead |
|-------------|-----|-------------|
| bot | Hides the bounded workflow role and handoff contract. | Agent |
| destination repo | Conflates the adopter project with a tool-specific installed surface. | Deployment Target |
| version file | Omits the installed scope and fingerprints carried by the record. | Deployment Record |
