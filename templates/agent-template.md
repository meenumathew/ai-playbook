---
# REQUIRED machine-readable contract: every key below must be present and non-empty.
# Validated by `tests/acceptance/test_agent_contracts.py`
# § test_every_agent_declares_required_frontmatter_keys.

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
Do not restate the master ceremony rows verbatim.>

---

## Steps

<Numbered procedural steps. Lead with the action, then a one-line outcome.
Cite KB / skill / template files by backtick-quoted path so
`test_pointer_contracts.py` validates them.>

1. **<Action>**: <outcome>. Cite: `knowledge-base/<file>.md` § <Heading>.
2. **<Action>**: <outcome>.
3. ...

---

## Tool Policy

This agent inherits `knowledge-base/tool-policy.md` § Per-Agent Matrix. List only true deltas below; do not restate unchanged matrix cells.

- Read/write caps: <only if different from the matrix or agent default>.
- Additional operations: <only if this agent uses a skill not already covered by the matrix>.
- Denied actions: <role-specific anti-patterns, destructive actions, or external side effects>.

**Anti-pattern:** <one sentence: what this agent must NOT do. Use a
`AGENT_FORBIDDEN_PHRASES` entry in `tests/acceptance/contract_data.py` to
lock the anti-pattern with a reason.>

---

## Failure modes

| Symptom                                    | Likely cause                            | Action                                       |
|--------------------------------------------|-----------------------------------------|----------------------------------------------|
| <observable failure>                       | <root cause>                            | <recovery, escalation, or KB pointer>        |

---

## Approval gate

This agent follows `CLAUDE.md` § Shared Rules § Approval gate. Specifically:

- <list the artifacts / actions this agent gates on approval: preview-only
  by default at production tier; save-and-summarize at prototype tier>.
