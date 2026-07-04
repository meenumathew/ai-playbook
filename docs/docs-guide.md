# Documentation Guide (Diataxis)

This project follows the [Diataxis framework](https://diataxis.fr/) for technical documentation. Diataxis separates documentation into four quadrants by reader need: tutorials (learning), how-to guides (tasks), reference (information), and explanation (understanding).

The docs use Diataxis strictly: every page has one primary quadrant. A page can link to another quadrant, but it should not embed that second job in place.

---

## The Four Quadrants

| Quadrant | Purpose | Reader's need | Style |
|----------|---------|---------------|-------|
| **Tutorial** | Learning-oriented | "Teach me" | Step-by-step, hands-on, achieves a goal |
| **How-to** | Task-oriented | "Help me do X" | Practical steps, assumes knowledge |
| **Reference** | Information-oriented | "What are the details?" | Precise, complete, structured |
| **Explanation** | Understanding-oriented | "Why does it work this way?" | Discursive, context, rationale |

Use the two-axis check when a page does not fit cleanly:

| Reader mode | Acquiring capability | Applying capability |
|-------------|----------------------|---------------------|
| **Action** | **Tutorial**: guided first success for a learner | **How-to**: steps for a competent user solving a real task |
| **Cognition** | **Explanation**: context and mental model | **Reference**: factual lookup during active work |

Quick memory rule: tutorials are for studying, how-to guides are for working, reference is for lookup, and explanation is for understanding.

---

## Strict Placement Rules

**Golden rule:** each page must belong to exactly one quadrant. Mixing modes makes the page harder to use: tutorial steps in reference slow down lookup; architectural rationale inside a how-to hides the task; reference tables inside a tutorial interrupt the first success path.

1. **One page, one primary reader need.** Pick tutorial, how-to, reference, or explanation before writing.
2. **Split instead of mixing.** If a how-to needs background, link to an explanation. If an explanation needs steps, link to a how-to. If a tutorial needs exact flags, link to reference.
3. **Stable paths beat decorative taxonomy.** Folder names do not need to mirror quadrants. Existing stable paths stay in place; the strictness lives in the page purpose and map.
4. **Every docs page appears in the map.** Add new files to [Documentation Index](README.md) and to the map below in the same change.
5. **Navigation pages are allowed.** An index can route readers by need, but it must not become a tutorial, task recipe, or rationale essay.

**Automated checks.** Vale enforces some of these rules mechanically (allow-listed per folder in `.vale.ini`): `docs/how-to/**` H1s must start with "How to" and stay task-focused; `docs/adr/**` may not contain step-by-step instructions or how-to/tutorial/reference titles. The full quadrant rule set lives in `.vale/styles/Diataxis/`; enable the matching rules when you add a `docs/tutorials` or `docs/reference` folder. Vale is a backstop, not a substitute for the placement judgment above.

---

## Current Documentation Map

<!-- vale Google.We = NO -->
| File | Primary quadrant | Contract |
|------|------------------|----------|
| `docs/README.md` | Reference index | Routes readers by Diataxis need; no task steps beyond page selection. |
| `getting-started.md` | Tutorial | Beginner first success; avoid alternatives and deep theory. |
| `user-guide.md` | How-to index | Day-to-day workflow routing for users who know the basics. |
| `how-to/choose-workflow-path.md` | How-to | Task recipe for selecting full, minimal, spike, solo, or team workflow. |
| `how-to/enforce-quality.md` | How-to | Task recipe for local hooks, CI gates, and quality checks. |
| `how-to/invoke-agents.md` | How-to | Task recipe for starting agents with correct inputs. |
| `how-to/reduce-token-usage.md` | How-to | Task recipe for lowering token use while preserving quality gates. |
| `how-to/resume-session.md` | How-to | Task recipe for continuing after context loss or a tool switch. |
| `how-to/run-with-local-models.md` | How-to | Task recipe for local and open source model setup. |
| `how-to/setup-issue-tracker.md` | How-to | Task recipe for tracker setup or manual issue paste. |
| `how-to/setup-multi-repo.md` | How-to | Task recipe for shared vocabulary across repositories. |
| `how-to/write-a-pack.md` | How-to | Task recipe for project-specific playbook packs. |
| `rfcs/README.md` | How-to | Process recipe for proposing changes larger than a PR. |
| `cli-reference.md` | Reference | Complete command, flag, agent, skill, template, and config lookup. |
| `deprecation-policy.md` | Reference | Compatibility promise, covered surfaces, and lifecycle facts. |
| `limitations.md` | Reference | Factual registry of known constraints and unsupported surfaces. |
| `docs-guide.md` | Reference | Documentation standards, placement rules, and quadrant map. |
| `architecture.md` | Explanation | Design rationale, boundaries, workflow model, and trade-offs. |
| `references.md` | Explanation | Methodology background, sources, and attribution. |
| `adr/README.md` | Explanation | ADR purpose, criteria, lifecycle, and decision index. |
| `adr/*.md` | Explanation | One durable decision, context, and consequences per file. |
| Root `README.md` | Project landing page | Introduces the project and routes readers to the docs index. |
| Root `README.md` `Your First Feature` | Tutorial | End-to-end first feature walkthrough from the repository landing page. |
<!-- vale Google.We = YES -->

---

## Guidelines for New Documentation

Start with the page's quadrant, then use the matching style below. If two styles seem necessary, split the page or cross-link.

Ask two questions before drafting:

1. Is the reader trying to act, or trying to understand?
2. Is the reader acquiring a capability, or applying one they already have?

The answers choose the quadrant. Action plus acquisition means tutorial; action plus application means how-to; cognition plus application means reference; cognition plus acquisition means explanation.

### Writing a Tutorial (learning-oriented)

- A tutorial is a **lesson**: you are a teacher, the reader is a student
- People learn **by doing**, not by reading explanations
- Don't try to explain: resist the urge to add theory; it overwhelms beginners
- Inspires **confidence**, is an **enjoyable experience**
- Must result **in success**: the reader finishes with something working
- Title: "Build a ..." or "Your first ..."
<!-- vale Google.We = NO -->
<!-- vale Diataxis.HowToVoice = NO -->
- Voice: *"In this tutorial we will..."*
<!-- vale Diataxis.HowToVoice = YES -->
<!-- vale Google.We = YES -->
- Structure: numbered steps that always work
- Keep a **narrative of expectations**: tell the reader what should happen after each step ("the server responds with...", "if you don't see X, you missed Y") so they can self-verify
- Never: link away mid-flow, offer choices, explain alternatives
- Analogy: teaching a kid to bake a cake: success and fun matter more than understanding the chemistry

### Writing a How-to (task-oriented)

- **Goal-oriented**: addresses a real-world goal or problem
- Reader is an **already-competent user**: they know the basics, they need to do something specific
- A rich list of how-tos shows the breadth of your capabilities
- Keep it short and focused: one topic per file; if it grows past a page, split it
- Title: "How to ..." or imperative verb
- Voice: *"To achieve this, do that"*: imperative, direct
- Structure: steps, prerequisites, expected outcome
- Never: teach fundamentals, go into theory
- Analogy: a cooking recipe

### Writing a Reference (information-oriented)

- **Information-oriented**: contains the technical description
- Complete, reliable information: neutral, austere, consistent
- One hardly reads reference material; one **consults** it
- **Reference is the foundation**: write reference docs first; other quadrants link into them
- Improving reference forces you to improve the code (signatures, docstrings, naming)
- Title: noun phrase (the thing you document)
- Voice: neutral, factual, no personality
- Structure: tables, lists, exhaustive coverage
- **Mirror the code**: order reference docs to match the product's own structure so the docs read as a 1:1 map of the territory
- Never: explain why, offer opinions, tutor
- Analogy: a Wikipedia page

### Writing an Explanation (understanding-oriented)

- **Understanding-oriented**: provides context, background, clarity
- Helps answer the questions: *why? how does it work?*
- Establishes **connections** between concepts
- Title: "About ...", "Why ...", or topic noun
- Voice: *"The reason for X is because historically..."*: discursive, reflective
- Structure: prose, comparisons, history, alternatives considered
- Never: include step-by-step instructions, assume a specific task
<!-- vale Google.We = NO -->
- Analogy: "Why do we crave chocolate?": not a recipe, not a reference, an exploration of reasons
<!-- vale Google.We = YES -->

---

## Vendor-Neutral Language

The playbook is tool-, host-, tracker-, and model-agnostic by design. Reflect that in prose:

| Context | Use vendor names? | Example |
|---|---|---|
| Vendor-specific how-to (e.g. `setup-issue-tracker.md`, `run-with-local-models.md`) | Yes: purpose is that vendor's setup | "Authenticate `glab` with `glab auth login`" |
| Architecture / reference docs | Only as illustrative examples: list multiple vendors so no single one looks canonical | "Common pairings: Claude Opus, GPT-4, Gemini Pro, Llama 70B" |
| Core workflow / cross-cutting docs | No: use the abstraction | "Configure your AI tool to fetch issues from your tracker" |
| Slug, headings, key concepts | No: abstract names age better | `host-adapter`, `model-tier`, `issue-fetch` (not `github-adapter`) |

A vendor name in a core doc implies lock-in that does not exist. When you find one, replace it with the abstraction or move the prose into a vendor-specific file.

Use **work item** for external project-management objects unless the doc is intentionally naming a provider field. Jira may call it an issue with type Story, GitHub Projects may show an issue or project item, Linear calls it an issue, and teams may say ticket or task. The playbook's internal implementation artifact is a **story artifact** in `stories/`, with `issue-ref:` preserving the original tracker identity.

---

## Diagrams

Prefer Mermaid fenced code blocks (```` ```mermaid ````) over image files: GitHub and GitLab render them inline, they diff like code, and they never go stale in an assets folder nobody re-exports.

- **One diagram per concept.** A diagram that needs a legend to explain itself should be two diagrams.
- **Pick the type by what the reader asks:** sequence diagram for "what calls what, in what order" (flows, handoffs, incident timelines); flowchart for "which branch applies" (decision trees, workflow routing); state diagram for lifecycle states (story status, release stages).
- **Node labels use domain language**: the terms from `knowledge-base/domain-language.md`, not implementation names. `story-refiner → slice-planner`, not `module_a → module_b`.
- **Where they pay off:** architecture docs and ADRs (alternatives compared visually), runbooks (triage decision trees). Tutorials and references rarely need them: a diagram in a reference is usually an explanation trying to escape its quadrant.
- **Keep them small.** Past ~10 nodes, split by concern. Verify rendering in the host's built-in Markdown preview when available; do not search for or install Mermaid packages for routine documentation work. If preview is unavailable, statically check the fenced block syntax and call out that rendering was not previewed. Broken Mermaid syntax renders as a code block, not an error.

---

## Practical Lessons

These come from real-world Diataxis adoption (Django, Panel, hvPlot):

1. **Link, don't inline**: when a how-to needs background, link to an explanation instead of writing it in-place. Keeps each doc focused on its quadrant.

2. **Reference is the foundation**: without solid reference docs, other quadrants have nowhere to point. Write reference first, then how-tos that link into it.

3. **Don't delete before replacing**: existing messy docs serve readers better than a gap. Remove old content only after its replacement is live and linked.

4. **Repetition across quadrants is OK**: the same feature may appear in a tutorial, how-to, reference, and explanation. Each serves a different user need. This is not DRY violation.

5. **Adopt gradually**: don't attempt a complete docs overhaul in one pass. Pick one spot, decide what quadrant it should become, rewrite it, move on. Structure emerges iteratively.

6. **How-tos are contributor-friendly**: short, focused how-tos are easy for contributors to add (30 minutes each). They fill gaps naturally once the structure exists.

---

## Navigation

| Starting point | Go to |
|----------------|-------|
| Need the full docs map | [Documentation Index](README.md) |
| Never used the playbook | [Getting Started](getting-started.md) (Tutorial) |
| Know the basics, need to do something | [User Guide](user-guide.md) (How-to index) |
| Need to do one specific task | [how-to/](how-to/) directory (focused How-tos) |
| Need exact command syntax | [CLI Reference](cli-reference.md) (Reference) |
| Want to check known constraints | [Known Limitations](limitations.md) (Reference) |
| Want to understand design choices | [Architecture](architecture.md) (Explanation) |
| Want methodology background | [References](references.md) (Explanation) |
