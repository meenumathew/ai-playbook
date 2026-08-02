---
id: working-agreement
size: medium
tldr: AI is a peer programmer; review like a human PR; disagreement protocol; ownership stays with the human.
load_when: collaboration, review size, ownership, disagreement, escalation, agent workflow, operating model
audience: all
canonical_for: AI-as-peer norms, code review norms, disagreement protocol
cross_refs: philosophy.md, model-tier.md, security.md
verified: 2026-07-27
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

## Responding to Review Feedback

Treat review comments as hypotheses to evaluate, not instructions to apply
blindly.

1. Read the complete feedback and identify the requested behaviour. Ask only
   when an ambiguity could change scope, safety, or user-visible results.
2. Check the claim against the current code, tests, story requirements, and
   canonical knowledge-base guidance. Advice from a human, agent, or external
   source does not replace repository evidence.
3. Accept feedback that improves correctness or the agreed design. If it
   conflicts with requirements or introduces a regression, push back with the
   relevant code path, test result, or documented constraint.
4. Apply one independent item at a time and run its smallest meaningful
   verification before moving to the next. Re-read the resulting diff so a
   locally correct edit does not create a cross-file mismatch.
5. Report what changed and the verification evidence. Do not mark an item
   resolved when the supporting check has not run.

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
