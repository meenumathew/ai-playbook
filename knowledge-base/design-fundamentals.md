---
id: design-fundamentals
size: medium
tldr: "Cohesion, coupling, abstraction: the property vocabulary behind module shape; high cohesion + low coupling + good abstraction = changeability; complexity symptoms and design checkpoints translate the properties to everyday moments."
load_when: cohesion, coupling, abstraction, module property, review finding, design decision, "is this module pulling its weight", LCOM, afferent, efferent, complexity symptom, change amplification, cognitive load, unknown unknowns, software that lasts, strategic vs tactical, design checkpoint
audience: all
canonical_for: cohesion, coupling, abstraction, information hiding, levels of abstraction, complexity symptoms, strategic vs tactical programming, design checkpoints
cross_refs: design-patterns.md, philosophy.md, refactoring.md
verified: 2026-07-17
---

# Design Fundamentals

Cohesion, coupling, and abstraction are the **properties** behind module shape. The KB's operational rules: Architecture Layers, Module Depth and Seams, Smells → Moves, Anti-Patterns: are *consequences* of these properties. Read this file when a review finding or design decision is really about a property, not a pattern.

## Agent Use

- **Read first:** Cohesion, Coupling, Abstraction, How These Compose.
- **Reviewing or designing:** Building Software That Lasts (complexity symptoms), Practical Application (design checkpoints). Skip for routine implementation.

This file defines vocabulary; it does not introduce new rules. Each section cross-links to the existing canonical home for the *move* the property suggests.

---

## Cohesion

**Definition** (Constantine & Yourdon, *Structured Design*): the degree to which the elements inside a single module belong together. A module has high cohesion when its parts share a single responsibility and change for the same reason.

### Detection signals

| Signal | Meaning |
|--------|---------|
| Methods don't share state | Pieces of the module operate on disjoint data: split by data flow |
| Mixed levels of abstraction in one function | High-level orchestration interleaved with low-level mechanics: extract |
| The word "and" appears in the module's name or docstring | Two responsibilities pretending to be one |
| Multiple unrelated reasons-to-change | Single Responsibility violation: split by axis of change |

Canonical example shape: `OrderManager` doing pricing + persistence + notification has three unrelated reasons to change; split by reason-to-change (`OrderPricing`, `OrderRepository`, `OrderNotifier`).

### Where the moves live

- Symptom = Large Class / Long Function: `refactoring.md` § Smells → Moves.
- Symptom = God Object: `design-patterns.md` § Anti-Patterns.
- Architectural enforcement (each layer has one cohesive concern): `design-patterns.md` § Architecture Layers.

---

## Coupling

**Definition** (Constantine): the degree to which one module depends on another. Low coupling means a change in one module is unlikely to force a change in another.

Two directions worth naming:

- **Afferent (incoming)**: how many modules depend on *this* one. High afferent coupling = changes ripple outward; treat the interface as a contract.
- **Efferent (outgoing)**: how many modules *this* one depends on. High efferent coupling = this module is fragile to changes elsewhere.

### Detection signals

| Signal | Meaning |
|--------|---------|
| Cross-file changes ripple: one bug fix touches 5 files | Hidden coupling; missing abstraction unifying them (Shotgun Surgery) |
| "Import everything from neighbour" | Module reaches into another's internals: Law of Demeter violation |
| Passing a whole object when one field would do | Implicit dependency on the object's shape |
| Method on A uses more data from B than from A | Feature Envy: method belongs on B |
| Domain object imports infrastructure | Dependency direction violation: Must Fix |

Canonical example shape: `Invoice` reading `customer.address.country` to compute tax couples it to `Customer`, `Address`, and the tax table; inverting to a `TaxCalculator` port leaves one named dependency at the seam.

### Where the moves live

- Property → cost: `philosophy.md` § Principles: Constantine's Equivalence (`cost ≈ change ≈ coupling`).
- Architectural enforcement (deps flow inward only): `design-patterns.md` § Architecture Layers.
- Symptom = Tight coupling / Shotgun Surgery / Feature Envy: `refactoring.md` § Smells → Moves.
- Pattern at the seam (≥ 2 adapters justify a port): `design-patterns.md` § Module Depth and Seams.

---

## Abstraction

**Definition** (Ousterhout, *A Philosophy of Software Design*): a simplified view of an entity that omits unimportant details. The working consequence: the leverage a module gives its callers: how much behaviour they get per unit of interface they have to learn. **Information hiding** (Parnas, *On the Criteria to Be Used in Decomposing Systems*): the interface should expose decisions that won't change, and hide decisions that might.

A good abstraction is **deep**: small interface, large implementation. A bad abstraction is **shallow**: the interface is nearly as complex as the implementation, so the caller pays the learning cost without getting leverage.

### Detection signals

| Signal | Meaning |
|--------|---------|
| Interface as complex as implementation | Shallow module: pass-through; callers learn the same complexity twice |
| Function mixes high-level orchestration with low-level mechanics | Multiple levels of abstraction in one place: extract by level |
| Primitive obsession: raw `str` / `int` / dict for domain concepts | Domain meaning leaking through generic types: wrap in a Value Object |
| Caller has to know "if you're going to do X, also do Y" | Sequencing leaked through the interface: fold Y into X |
| Implementation details visible in parameter names or docstrings | Abstraction not hiding what it should: narrow the interface |

Canonical example shape: `save_user(db_connection, user_id, encoded_payload, transaction_marker, flush_after)` makes the caller learn five mechanical concepts for one operation; `UserRepository.save(user)` hides them all: same behaviour, one method to learn.

### Where the moves live

- Property → shape: `design-patterns.md` § Module Depth and Seams (deep vs shallow, deletion test, two-adapter rule).
- Symptom = Primitive Obsession / Inquisitive Code: `design-patterns.md` § Anti-Patterns.
- Symptom = Unnecessary indirection (over-abstracted, shallow): `refactoring.md` § Smells → Moves (Inline / One Pile).
- When *not* to abstract yet: `refactoring.md` § When to Refactor: Rule of Three.

---

## How These Compose

The three properties interact. None of them works alone.

| Combination | Result | Where it shows up |
|-------------|--------|-------------------|
| **High cohesion + low coupling** | Changeability: change locality is small; one reason-to-change touches one module | The whole point of Architecture Layers |
| **High cohesion + good abstraction** | Deep modules: small interface, large implementation, callers get leverage | `design-patterns.md` § Module Depth and Seams |
| **Low coupling at explicit seams** | Ports and Adapters: coupling is *named* and *bounded* at the seam, not diffuse | `design-patterns.md` § Hexagonal Architecture |
| **Low cohesion + low coupling** | Junk drawer: module hangs together by accident; rename or split |  |
| **High cohesion + tight coupling** | Brittle module: does one thing well but breaks every time a neighbour changes |  |
| **Deep abstraction + tight coupling** | Leaky abstraction: interface looks small but implementation reaches everywhere; callers think they're decoupled but aren't |  |

The composite rule, restated: **prefer designs that increase cohesion, reduce coupling, and deepen abstraction: usually one move serves all three.** Constantine's Equivalence (`philosophy.md` § Principles) is the cost-side framing of the same idea.

---

## Building Software That Lasts

Software that lasts stays **cheap to change**: most of a system's cost arrives after the first release, and complexity compounds against it one shortcut at a time. The properties above are how you fight it; this section is the long-horizon *why* and *when*.

### The three symptoms of complexity

Complexity (Ousterhout) is anything about the structure that makes a system hard to understand or modify. It shows up in exactly three ways: and each traces back to a property, which is what makes it fixable:

| Symptom | What it looks like | Property behind it | Where the move lives |
|---------|-------------------|--------------------|---------------------|
| **Change amplification** | A simple change requires edits in many places | Coupling | `refactoring.md` § Smells → Moves (Shotgun Surgery) |
| **Cognitive load** | A developer must hold too much in their head to change something safely | Abstraction: shallow or leaky interfaces | § Abstraction + `design-patterns.md` § Module Depth and Seams |
| **Unknown unknowns** | It is not obvious *which* code must change, or what you'd need to know | Cohesion + information hiding failure | § Cohesion; make the design obvious: `philosophy.md` § Principles (Least Surprise) |

Symptoms beat adjectives in review: instead of arguing "this is badly coupled", ask **"what does the next change in this area touch?"** and count files. The symptom is observable; the property names the cause; the cited section names the move.

### Strategic over tactical

Tactical programming makes today's feature work. Strategic programming (Ousterhout) treats working code as **not the finish line**: the design is what every future change pays for.

| Rule | Agent action |
|------|-------------|
| Working code is not enough | At GREEN, the REFACTOR step is mandatory thinking time, not optional polish (`refactoring.md` § When to Refactor) |
| Invest continuously, not in cleanup sprints | Small recurring payments: a better name, a deeper interface, tidy-first: beat a deferred "refactoring story" that never gets scheduled |
| Strategic ≠ speculative | Build for *today's* axes of change, not imagined ones: YAGNI and Rule of Three still bind (`refactoring.md` § When to Refactor) |
| Design it twice | For a non-trivial module, sketch two interface shapes before committing: the first idea is rarely the deepest. Maps to production-tier "present alternatives" (`CLAUDE.md` § Quality Tier) |

### Design for change: what to hide

Parnas' rule, made operational: decompose by **what is likely to change**, not by sequence of execution. The interface exposes decisions that won't change; the implementation hides decisions that might.

| Likely to change → hide behind a seam | Stable → safe to expose in the interface |
|--------------------------------------|------------------------------------------|
| Vendor choice, storage tech, wire formats, algorithms, config sources | Domain language terms, observable behaviour the ACs are written against |

The playbook applies its own rule: vendor-neutral operation IDs hide the vendor decision (`design-patterns.md` § Vendor-Neutral by Design); ports hide infrastructure (`design-patterns.md` § Hexagonal Architecture). When deciding where a new seam goes, ask "which decision here would I least like to be married to?": that's the one the interface must hide.

---

## Practical Application: Design Checkpoints

How the properties translate to everyday moments. Each row is a question asked **at the moment it occurs**: not a separate review phase, no extra artifact.

| Moment | Ask | If the answer is bad |
|--------|-----|---------------------|
| Naming a new module/class/function | Can I name it accurately without "and", "Manager", "Util", "Helper"? | Two responsibilities: split before writing (§ Cohesion) |
| Adding a parameter | Does the caller now need to know an implementation detail? | Fold it inside: deepen the interface (§ Abstraction) |
| Adding an import | Does the dependency point outward (domain → infra) or skip a layer? | Must Fix: invert via a port (`design-patterns.md` § Architecture Layers) |
| Passing a whole object for one field | Does the callee now depend on the object's shape? | Pass the field, or move the method to the data (§ Coupling: Feature Envy) |
| Repeating logic a third time | Is the same knowledge now in three places? | Extract now: Rule of Three (`refactoring.md` § When to Refactor) |
| A test is hard to write | Am I testing past the interface? | Module is the wrong shape: pull complexity behind the seam (`testing.md` § When Tests Are Hard to Write) |
| A "simple" change touches 5 files | What missing abstraction unifies them? | Shotgun Surgery: extract it (`refactoring.md` § Smells → Moves) |
| Reviewing a diff | What does the *next* change in this area cost? | Cite the property and the symptom, not personal taste |

### The three-question design check

When the full table is too heavy (prototype tier, tiny diffs), three questions cover all three properties:

1. **Cohesion**: does each touched module still have one reason to change?
2. **Abstraction**: does each new or changed interface hide more than it exposes?
3. **Coupling**: if the most likely requirement change lands next month, how many of these files change again?

"Yes / yes / few" is the whole check. Any other answer routes to the table above for the move.

---

## Named Principles

Shorthand reviewers already use: each maps to one operational home, where the move lives. These are not independent rules, so no rule text here:

| Principle | Operational home |
|-----------|------------------|
| **SRP** | § Cohesion + `design-patterns.md` § Anti-Patterns (Large Class) |
| **DRY** (third repetition, not second) | `refactoring.md` § When to Refactor (Rule of Three) |
| **KISS** | `philosophy.md` § Principles (Readability over cleverness) |
| **YAGNI** | `refactoring.md` § When to Refactor + `design-patterns.md` § Anti-Patterns (Premature Abstraction) |
| **Law of Demeter** | `design-patterns.md` § Anti-Patterns (Inquisitive Code) + § Coupling above |
| **SOLID beyond SRP** | DIP → `design-patterns.md` § Hexagonal Architecture; ISP → `design-patterns.md` § Module Depth and Seams; OCP/LSP violations surface as smells in `design-patterns.md` § Anti-Patterns |
