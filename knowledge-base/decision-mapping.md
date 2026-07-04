---
id: decision-mapping
size: small
tldr: For work too big and too foggy for one session, resolve the open decisions first as a tracked map of decision items, before slicing a build.
load_when: decision mapping, too big for one session, foggy, unknown decisions, open decisions, decision spike, map the unknowns, multi-session planning, pre-planning decisions
audience: all
canonical_for: decision-mapping mode, resolving open decisions before slicing, decision-item map
cross_refs: CHEATSHEET.md
verified: 2026-07-17
---

# Decision Mapping

Some work arrives **too big for one session and wrapped in fog**: the destination is roughly known, but the *decisions* that shape the build are unresolved. Slicing straight into a plan would bake in guesses. Decision Mapping charts the way first: it names the open **decisions**, resolves them one at a time, and stops when nothing is left to decide before someone can plan the build.

This is `story-refiner` **Mode D**. It is *planning*, not building: the output is resolved decisions and a story (or an ADR), never code.

## Agent Use

- **Read first:** When to use it, The decision map, The loop.
- **Load deeper only on trigger:** Boundaries, when unsure whether a decision belongs in the map or is really a build slice.

---

## When to use it

Use Decision Mapping when **all** of these hold:

- The effort is larger than one refine-and-slice pass can hold.
- The blocker is **open decisions**, not missing detail (design forks, cross-team ownership, sequencing, data-shape choices).
- Charging at the destination would force premature guesses that are expensive to unwind later.

If the requirement is clear and only the *slices* are unknown, skip this and go to `slice-planner`. If a single decision blocks everything, a normal ADR is enough. Decision Mapping is for the case of **several coupled decisions** that must resolve before planning.

## The decision map

The map is a single tracked artifact: an epic-level story or a `research/RESEARCH-NNN-<slug>.md` section titled **Decision Map**. It is an **index, not a store**: each decision lives in exactly one place (its own item), and the map only gists it and links.

Each **decision item** captures:

| Field | What it holds |
|---|---|
| Decision | The question whose answer is a decision, not a slice of build. Phrased neutrally. |
| Options | The viable answers, with a one-line "why / why not" each. |
| Blocks | Which other decisions or slices cannot start until this resolves. |
| Owner | Who decides (may be another team). |
| Resolution | Filled when decided: the chosen option + one-line rationale. Links to the ADR if one was written. |

Refer to each item by a **name** (its title), never a bare id or number: a wall of `#41, #42, #43` is illegible; names read at a glance.

## The loop

1. **Name the destination.** One sentence: the spec to hand off, the decision to lock, or the change to make. This shapes every item.
2. **Chart the decisions.** List the open decisions as items. Do not list build slices here: those come after, from `slice-planner`.
3. **Order by blocking.** Resolve decisions with no unresolved blockers first; a decision that unblocks the most others is highest-leverage.
4. **Resolve one at a time.** For each: research neutrally, propose your recommended answer with reasoning, ask the one decision, record the resolution. Write an ADR when the decision is architectural (`docs/adr/`).
5. **Stop when the fog clears.** The map is done when no decision remains that would change scope, architecture, data model, or sequencing. Hand off to `slice-planner` (build) or `docs-maintainer` (ADR/spec).

The pull to "just start building" mid-map is the signal you have reached the edge of the map: that is the hand-off point, not permission to skip the remaining decisions.

## Boundaries

- **Decisions, not deliverables.** Mode D produces resolved decisions and a story/ADR, never code or slices. Slicing is `slice-planner`'s job.
- **Respect existing ADRs.** Never re-open a previously rejected decision (`docs/adr/`).
- **One decision per item.** A tangled item that resolves two things at once should be two items.
- **Timebox the whole map** if the fog is deep: agree the timebox up front, same as a Spike (`CLAUDE.md` § Workflow).
