---
id: working-agreement
size: medium
tldr: AI is a peer programmer; review like a human PR; disagreement protocol; ownership stays with the human.
load_when: collaboration, review size, ownership, disagreement, escalation, agent workflow, operating model
audience: all
canonical_for: AI-as-peer norms, code review norms, disagreement protocol
cross_refs: philosophy.md, model-tier.md, security.md
verified: 2026-07-17
---

# Working Agreement

## Agent Use

- **Read first:** AI as Peer Programmer, Code Review Norms, Disagreement Protocol.
- **Load deeper only on trigger:** team operating-model guidance (`docs/how-to/scale-agent-automation.md`).

---

## AI as Peer Programmer

The AI agent is a **peer programmer**: it challenges unclear requirements, says "I don't know" rather than guessing, and refuses to skip tests. You review its work the same way you'd review a human's PR.

**Peer does NOT mean:** accepting output without review, blaming the agent for bugs you didn't catch, or skipping refinement.

---

## Pairing Modes

| Mode | How it works | When to use |
|------|-------------|-------------|
| **Human + AI pair** | Human navigates (intent, decisions, domain knowledge), AI drives (writes code, runs tests) | Default: everyday development |
| **Solo + AI review** | Build alone, then hand to diff-reviewer agent | Solo developers: agent is the second pair of eyes |

Sustainable pace: ~4 hours active pairing/day ceiling. Mix pairing and solo work.

---

## Collective Code Ownership

Anyone: human or AI agent: can change any part of the codebase. No one "owns" a module.

**This only works when:**

- Knowledge base defines how the team writes code (style, patterns, testing)
- diff-reviewer enforces consistency regardless of who wrote it
- Every change follows the same workflow path: refine → plan → build → review

---

## Shared Values

| Situation | Agent action |
|-----------|-------------|
| **Stuck** | Compare with the last working version. If 3 fix attempts fail: STOP per `debugging.md` § 3-Fix Architectural Stop Rule: reset to the last green commit and question the design before any fix #4. |
| **Succeed** | Update knowledge base with the lessons. Use `skills/retrospective/SKILL.md` for structured process. |

---

## Code Review Norms

**Author responsibilities:**

| Rule | Agent action |
|------|-------------|
| PRs ≤ 400 hand-written changed lines | Count the lines a human must actually review: lockfiles, generated code, snapshots, mechanical renames/moves, and deletions are exempt. If larger, split the work: reviewers can't effectively review big diffs |
| Story/issue reference in PR description | No context → no approval |
| Self-review first | Read your own diff before requesting review |

**Reviewer responsibilities:**

| Rule | Agent action |
|------|-------------|
| First response within 1 business day | Don't block the author |
| Comment on the code, not the author | "This function" not "you wrote" |
| Distinguish severity | Must Fix / Should Fix / Suggestion (see `agents/diff-reviewer.agent.md` § Severity) |
| Approve when Must Fix resolved | Don't hold merge over style preferences |

---

## Disagreement Protocol

| Situation | Agent action |
|-----------|-------------|
| AI pushes back | Human explains context AI doesn't have → AI adapts or flags the constraint explicitly |
| Human overrides | AI records the override in the plan's `## Discovered` section: never silently accepted |
| "Just trust me" | Neither side accepts this: disagreements surface missing context worth capturing |

---

## Reference: Agent-First Automation

Operating-model guidance for teams with high agent throughput (teaching lint messages, doc gardening, quality sweeps, scaling by team size): `docs/how-to/scale-agent-automation.md`. One rule worth keeping in-session: custom lint/CI messages should name the violation **and** the fix with a KB citation, so agents self-correct.
