---
id: refactoring
size: small
tldr: Refactor only when green; Rule of Three; separate structural and behavioural commits.
load_when: refactor, smell, structural change, Strangler Fig, Parallel Change, Rule of Three
audience: xp-pair-programmer, diff-reviewer, code-inspector
canonical_for: when-to-refactor triggers, safe refactoring procedure, smells-to-moves table
cross_refs: style-guide.md, design-patterns.md, testing.md
verified: 2026-06-10
---

# Refactoring

Commit discipline (structural vs behavioural separation): `style-guide.md` § Refactoring Commit Discipline.

## Agent Use

- **Read first:** When to Refactor, Safe Refactoring Procedure, Smells to Moves.
- **Load deeper only on trigger:** migration-scale moves such as Strangler Fig or Parallel Change.

---

## When to Refactor

| Trigger | Agent action |
|---------|-------------|
| Tests are green and code has a smell (see table below) | Refactor now: this is the REFACTOR step |
| Third repetition of the same logic (Rule of Three) | Extract the abstraction |
| A new concept has emerged that deserves a name | Extract and rename |
| Test just went green and code can be simpler | Simplify before moving to next test |

**Do NOT refactor when:**

| Condition | Agent action |
|-----------|-------------|
| Tests are failing | Get to green first: never refactor on red |
| No tests exist for this code | Write tests first (`testing.md` § Retrofitting Tests onto Existing Untested Code) |
| Guessing at future needs | YAGNI: wait for a real trigger |

**Green Bar Rule:** only refactor when all tests pass. If you break tests while refactoring, undo and take a smaller step. No tests over the code you are about to restructure? Write characterization tests first (`testing.md` § Retrofitting Tests onto Existing Untested Code): a green bar that doesn't cover the touched code protects nothing.

---

## Safe Refactoring Procedure

Every refactoring move follows this sequence:

1. Verify green bar (all tests pass)
2. Make ONE small structural change
3. Run tests immediately
4. Green → commit with a structural-change message → next move
5. Red → undo the change, take a smaller step

One smell per commit. Never mix structural and behavioural changes in the same commit.

---

## Smells → Moves

When you detect a smell, apply the corresponding move.

| Smell | How to detect | Refactoring move |
|-------|--------------|-----------------|
| **Long function** | Function does multiple things; hard to name accurately | **Extract Method/Function**: each piece gets a name |
| **Large class** | Class has many responsibilities; changes for unrelated reasons | **Extract Class**: split by responsibility |
| **Complex conditionals** | Deep nesting, long boolean chains | **Simplify Conditionals**: guard clauses, named predicates |
| **Naming doesn't fit** | Name doesn't reflect current understanding of the concept | **Rename**: match the domain language |
| **Over-abstraction** | Code split into tiny pieces harder to read *because* of splitting | **One Pile** (Beck, *Tidy First?*): inline everything, then re-extract with better boundaries |
| **Inconsistent patterns** | Same logic written different ways in different places | **Normalize Symmetries**: pick one way, convert all |
| **Duplicated logic** | Third repetition of the same structure | **Remove Duplication**: extract to single source |
| **Unnecessary indirection** | Abstraction adds complexity with no benefit | **Inline**: collapse the indirection |
| **Long parameter list** | Function takes many arguments | Extract a parameter object or configuration |
| **Feature Envy** | Method uses more data from another class than its own | Move the method to the class it envies |
| **Shotgun Surgery** | One change requires edits across many unrelated files | Extract the missing abstraction that unifies them |
| **Tight coupling** | Changes in one module force changes in another | Introduce an interface or port at the boundary. See `design-fundamentals.md` § Coupling. |

**Smells with canonical homes elsewhere**: detect and reference:

- Dead code → `style-guide.md` § Dead Code
- Comments explaining *what* → `style-guide.md` § Comments
- Primitive Obsession → `design-patterns.md` § Anti-Patterns
- Magic Numbers → `style-guide.md` § Naming (use named constants)

---

## Migration-Scale Moves

For changes too large for inline refactoring:

| Move | When | Agent action |
|------|------|-------------|
| **Strangler Fig** | Replacing a legacy module | Build replacement alongside; route traffic incrementally; retire old when migration complete. Rollback possible at each step. |
| **Parallel Change (Expand-Contract)** | Breaking interface change | Add new interface alongside old; migrate all callers; delete old. No flag day needed. |
| **Branch by Abstraction** | Replacing an implementation behind a stable interface | Introduce an abstraction over the existing implementation; build the new implementation behind the same abstraction; switch callers; remove the old. Lets the change land in trunk-friendly increments without a long-lived branch. |

**Common to all three:** one increment per commit; keep both the old and new paths working and tested through the transition; delete the old path only after every caller has migrated and the suite is green. If you cannot keep both paths green at the same time, the slice is too big: make it smaller.

---

## Inline vs Planned

| Type | Scope | Agent action |
|------|-------|-------------|
| **Inline** (default) | Small: seconds per move | Apply during TDD REFACTOR step. Commit immediately. |
| **Planned** | Large: smell has grown beyond inline | Create a separate story. Never mix with feature work. |
