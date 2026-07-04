---
# REQUIRED machine-readable contract: every key below must be present and non-empty.
# Validated by `tests/acceptance/test_agent_contracts.py`
# § test_every_agent_declares_required_frontmatter_keys and
# § test_every_agent_declares_machine_readable_read_budget.

# Display name shown to humans (the agent's brand).
name: <Title Case Agent Name>

# One-sentence summary: what this agent does, in user terms.
description: '<one sentence: the verb-and-deliverable, e.g. "Refines stories before planning">'

# Hint shown when the user runs the slash command: guides them to give the
# right input. One line, plain English, no jargon.
argument-hint: <e.g. "Describe the change, paste a story, or give an issue ref">

# Tier name: `advisor` for design / planning / review work,
# `executor` for implementation. See `knowledge-base/model-tier.md`.
model: advisor

# Stable identifier: must equal the filename without `.agent.md`. The
# matching `commands/<id>.md` shim is the slash-command surface.
id: <kebab-case-id>

# Comma-separated load triggers: keywords that should make a router pick
# this agent over a sibling. Be specific.
load_when: <triggers, comma-separated>

# What forms of input this agent accepts. Bullet list inside one string.
inputs: <e.g. "idea / pasted story / story file / issue reference">

# What artifacts this agent produces (saved files; not host-platform side
# effects like PRs, which belong on a separate line). Be precise: Section-1
# audits flag overstated outputs.
outputs: <e.g. "stories/STORY-NNN-<slug>.md + research/RESEARCH-NNN-<slug>.md">

# What sibling agents this one hands off to. Names from `agents/`.
handoff: <agent-id> [or <agent-id-A> / <agent-id-B>]

# When this agent escalates: to a higher model tier, an ADR, or a human.
# Used by Section-1 honesty audits.
escalation: <e.g. "ADR (advisor tier) if architectural decision surfaces; ask user if scope ambiguous">

# Per-session read cap: an integer, or the literal `self-tracked` when the
# agent tracks its own reads without a numeric cap. Feeds the read-budget
# hook; state the cap once more (at most) in § Tool Policy prose, never in
# a third place.
read-budget: <e.g. 20>

# OPTIONAL: KB files or sections loaded on every invocation of this agent.
# Use sparingly: preloads are paid in full each session.
# preload: <comma-separated KB files, e.g. "testing.md">

# Last verification date in YYYY-MM-DD. The maintainer re-runs the agent
# against its eval rubric and updates this date when behaviour is confirmed
# to match the contract. Stale dates >180 days are flagged by Section-1.
verified: <YYYY-MM-DD>
---

# <Agent Name>

<One paragraph: the agent's job in plain English. State the core invariant
the agent enforces (e.g. "research before code", "tests before implementation").
Cite the closest CLAUDE.md or KB anchor instead of restating the rule.>

---

## Inputs

<Bullet list of accepted input shapes. Mirror the frontmatter `inputs:` line
in expanded form: the frontmatter is the contract; this section is the
prose explanation.>

**STOP gate:** <one condition under which the agent must refuse to start:
e.g. "no story file → ask for one"; "non-empty working tree → ask the user
to commit or stash first">.

---

## Tier-aware ceremony

Master table: `CLAUDE.md` § Quality Tier. Agent-specific overrides:

| Step                  | prototype       | production      |
|-----------------------|-----------------|-----------------|
| <step name>           | <prototype>     | <production>    |

<Only list rows where this agent's behaviour deviates from the master table.
Do not restate the master ceremony rows verbatim, and do not restate the
read budget here: it lives in frontmatter plus at most one Tool Policy mention.>

---

## Steps

<Numbered procedural steps (or `### Phase N:` groups for multi-phase agents).
Lead with the action, then a one-line outcome. Cite KB / skill / template
files by backtick-quoted path so `test_pointer_contracts.py` validates them.
Artifact-saving steps preview first and use the canonical artifact-approval
prompt (`CLAUDE.md` § Shared Rules § Approval gate).>

1. **<Action>**: <outcome>. Cite: `knowledge-base/<file>.md` § <Heading>.
2. **<Action>**: <outcome>.
3. **Handoff**: <the closing step: name the next agents, the exact
   "Say 'use <agent-id> for ...'" line the user should run, and any
   end-of-session offers (e.g. `skills/retrospective/SKILL.md`)>.

<Small agents keep Handoff as the final numbered step (diff-reviewer,
code-inspector); agents with a distinct closing sequence promote it to a
dedicated `## Handoff` section (xp-pair-programmer).>

---

## Tool Policy

See `knowledge-base/tool-policy.md` § Per-Agent Matrix. List only true deltas below; do not restate unchanged matrix cells.

- Read cap: <one prose mention at most, e.g. "read capped at N per session">.
- Write scope: <the directories/files this agent may write, or "none">.
- Additional operations: <only if this agent uses a skill not already covered by the matrix>.
- Denied actions: <role-specific anti-patterns, destructive actions, or external side effects>.

**Anti-pattern:** <one sentence: what this agent must NOT do. Use a
`AGENT_FORBIDDEN_PHRASES` entry in `tests/acceptance/contract_data.py` to
lock the anti-pattern with a reason.>

---

## Narrowing

<Bullet list of hard boundaries and edge-case rules: the "always / never"
lines that keep the agent inside its lane. Every shipped agent has this
section; keep each bullet to one bolded rule plus one sentence.>

- **<Rule>**: <one sentence of guidance>.
- **<Edge case>?**: <what to do>.

---

## When to go back

<OPTIONAL: include when this agent sits mid-chain and failure modes route to
other agents (release-captain, incident-responder, xp-pair-programmer use it).>

| Symptom | Go to |
|---|---|
| <observable symptom> | <agent-id or human, with the reason> |
