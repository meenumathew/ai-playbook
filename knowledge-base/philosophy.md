---
id: philosophy
size: medium
tldr: Readability over cleverness; bounded contexts; teach-back gate; AI workflow anti-patterns.
load_when: design decision, principle, bounded context, cognitive health, context efficiency, teach-back, AI anti-pattern
audience: all
canonical_for: development principles, bounded contexts, teach-back gate, context engineering
cross_refs: design-patterns.md, working-agreement.md, performance.md
verified: 2026-07-17
---

# Development Philosophy

## Agent Use

- **Read first:** Bounded Contexts, Cognitive Health, Context Briefing, AI Workflow Anti-Patterns.
- **Load deeper only on trigger:** broad design philosophy and creative exploration. Do not load for routine implementation.

---

## Principles

| Principle | Agent enforcement |
|-----------|-----------------|
| **Readability over cleverness** | Choose the simpler implementation. Flag clever code in review. |
| **Explicit over implicit** | No hidden side effects. Inject dependencies. No magic. |
| **Strict boundaries** (deliberately inverts Postel's "be liberal in what you accept": leniency at boundaries breeds parser divergence and security bugs) | Validate strictly at input boundaries. Accept reasonable format variations (trim whitespace, normalise casing). |
| **Least Surprise** | Methods do only what their name says. Flag side effects in getters/queries during review. |
| **Tidying = optionality** | Tidy code that blocks the current change (separate commit). Leave code cleaner than you found it. See `CHEATSHEET.md` § Decision Guide. |
| **Progress over perfection** | Ship the smallest useful change. Don't over-polish: better code exists, perfect code doesn't. |
| **Constantine's Equivalence** | `cost(software) ≈ cost(change) ≈ coupling`: prefer designs that reduce coupling between modules. See `design-fundamentals.md` § Coupling for the underlying property. |
| **Strategic over tactical** | The design is what every future change pays for: invest continuously, never in deferred cleanup sprints. Canonical: `design-fundamentals.md` § Building Software That Lasts. |

---

## Domain Model

| Rule | Agent action |
|------|-------------|
| Model correctness > code elegance | When the model is wrong, fix the model first: don't polish bad abstractions |
| Models improve through refactoring | When tests reveal a better abstraction, propose the refactoring |
| Architecture layers | Enforce via `design-patterns.md` § Architecture Layers |

---

## Bounded Contexts

**Trigger:** same word, different meaning in different parts of the codebase (e.g. "Account" in billing vs. auth).

**Agent action:** flag during research. Recommend splitting the story or defining a translation layer. Never cross a context boundary in a single story without explicit approval.

---

## Design Thinking

| Signal | Agent action |
|--------|-------------|
| No pattern has emerged yet | Write the simplest code. Extract only after Rule of Three (`refactoring.md`) |
| Problem is unclear | Ask before building: don't assume |

---

## Error Handling

| Rule | Agent action |
|------|-------------|
| Actionable error messages | Include what failed AND what to do about it |
| Fail fast in dev, gracefully in prod | Throw on invalid state in dev; log + degrade in production |
| Idempotent operations | Design for safe retry: failures must not corrupt state |
| Exceptions respect boundaries | Domain raises domain exceptions, services catch at boundaries (where layers exist); in any codebase, translate exceptions at module boundaries instead of leaking internals upward. |

---

## Code Quality Signals

| Signal | Agent action |
|--------|-------------|
| Cross-file changes cause inconsistency | Treat as code smell: tighten the boundary or add a linter rule |
| Same fix needed across sessions | Add an environment fix (linter rule, test, contract): not a prompt-level fix |

---

## Reference Notes

Background sections: load only when the `## Agent Use` trigger matches; skip for routine implementation.

### Context Engineering

KB loading discipline (smallest source, stop when actionable) is canonical in `CLAUDE.md` § Knowledge Base. Beyond it:

| Rule | Agent action |
|------|-------------|
| Predictable context | Pre-fetch files named in the plan before starting implementation |
| Context too large | Break work into smaller pieces: don't try to hold everything |
| Prompt caching when available | Repeated context (KB files, system prompts) costs ~10% rate via `cache_control` / cached_tokens: order static content first so the cache prefix is stable |
| Edit over Write for changes | Edit sends the diff; Write resends the whole file. Use Write only for new files or full rewrites |
| Targeted reads | Use file offset/limit when you know which lines you need; full-file reads burn tokens for content you won't use |
| Subagents for branched investigation | Spawn fresh-context subagents for parallel research; don't bloat the parent conversation with content you only need once |

---

### Cognitive Health

| Debt | Risk | Workflow defense | Hard gate |
|------|------|-----------------|-----------|
| **Technical** | Shortcuts compromise changeability | TDD, refactoring, code review | Tests + linters block commit |
| **Cognitive** | Team can't reason about the code | Comprehension checkpoints, teach-back | Teach-back question before commit |
| **Intent** | Goals and rationale lost | 5 anchors, ADRs, domain language | Commit body explains *why* and ends with `Teach-back:` trailer (`commit-msg` hook) |

#### Teach-Back Gate (Cognitive Debt defense)

After xp-pair-programmer writes non-trivial code, the developer must answer at least one:

1. **What**: "What does this code do?" (without reading comments or the prompt)
2. **Where**: "If this broke at 2am, where would you look first?"
3. **Change**: "What would you change if the requirements shifted?"

Can't answer → don't commit. Rewrite simpler, or ask the agent to explain until you understand. Goal is comprehension, not speed.

#### Context Briefing

On request, the active agent pauses and explains the smallest useful map: what changed/exists, why it matters, where the seams are, what evidence exists, where to debug first. Comprehension checkpoint, not a separate workflow.

#### Decision Rationale in Commits (Intent Debt defense)

Commit body explains *why*, not just *what*. Requirement and trailer format: `CLAUDE.md` § Definition of Done + `skills/git/SKILL.md` § Teach-back Trailer. For stories with multiple design choices, add `## Decisions` to the story file (one bullet per choice) so choices live where AC live.

#### Agent responsibilities

- After non-trivial implementation: offer a comprehension checkpoint ("Does anything here surprise you?")
- Before PR: offer teach-back ("Want me to walk through the key design decision?")
- On request: provide a short context briefing before continuing
- When generating code faster than the human can review: pause and chunk the work
- If a module is poorly understood: suggest rewriting over patching
- If the developer skips teach-back: flag it: "You accepted this without review. Want a walkthrough?"

---

### AI Workflow Anti-Patterns

| Anti-pattern | Signal | Agent action |
|-------------|--------|-------------|
| **Silent Misalignment** | Plausible output, doesn't match intent | Check alignment before implementation; show plan preview |
| **Flying Blind** | Output accepted without review | Enforce TDD; use diff-reviewer / code-inspector |
| **Sunk Cost** | 3+ failed attempts, code getting messier | STOP per `debugging.md` § 3-Fix Architectural Stop Rule: reset to last green, question the architecture before any fix #4 |
| **LLM Non-Determinism** | Same prompt produces different output across runs (sampling, batching, tokenization, silent model updates) | Pin behaviour with tests, not chat memory: outcomes via running tests, state in markdown artifacts, deterministic quality gates. Pin model versions where possible. Don't rely on "the model did X last time." See `testing.md` § Test Quality Rules + `CLAUDE.md` § Shared Rules. |

---

### Creative Exploration

Use during story-refiner step 6, slice-planner step 5:

| Technique | Agent action |
|-----------|-------------|
| **Constraint removal** | Ask "What if X weren't a constraint?": test whether the constraint is real |
| **Analogy search** | Search codebase for similar patterns before inventing new ones |
| **Diverge-then-converge** | Generate 3+ approaches before evaluating any |
| **Reframing** | Ask "What if this were two things instead of one?" |

Rules: timebox, produce artifacts (not just thoughts), respect existing ADRs.
