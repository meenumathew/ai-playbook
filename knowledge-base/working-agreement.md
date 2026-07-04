---
id: working-agreement
size: medium
tldr: AI is a peer programmer; review like a human PR; disagreement protocol; ownership stays with the human.
load_when: collaboration, review size, ownership, disagreement, escalation, agent workflow, operating model
audience: all
canonical_for: AI-as-peer norms, code review norms, disagreement protocol
cross_refs: philosophy.md, model-tier.md, security.md
verified: 2026-05-19
---

# Working Agreement

## Agent Use

- **Read first:** AI as Peer Programmer, Code Review Norms, Disagreement Protocol.
- **Load deeper only on trigger:** Agent-First Automation and team operating model guidance.

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
| **Stuck** | Compare with last working version. If 3 attempts fail, stash and retry from last green commit. |
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

Optional operating-model guidance for teams with high agent throughput. Three patterns to encode once and run continuously:

| Pattern | What it does | When to apply |
|---------|--------------|---------------|
| **Teaching lint messages** | Every custom lint/architecture rule names the violation and the fix (cite KB section). Agents read the message and self-correct. | Any custom linter or CI check an agent might trigger |
| **Doc gardening** | Scheduled scan of docs/KB for dead references, stale cross-links, outdated examples; opens a fix-up PR per finding | Weekly for active repos, monthly for stable ones |
| **Quality sweeps (GC)** | Background agent scans for pattern violations (duplicate utils, raw exception logging, dead code, `Any` types) and opens small targeted refactors; auto-merge on green | When manual cleanup no longer scales |

**Lint message example:** instead of `"Import not allowed here"`, write `"Import from 'infrastructure' in 'domain' violates dependency direction: see design-patterns.md § Architecture Layers."` The 30 seconds spent writes the fix for every future occurrence.

**Scaling:**

| Team size | Automation level |
|-----------|------------------|
| Solo | Manual: run `code-inspector` when drift feels real |
| 2–4 | Monthly doc gardening + improve lint messages as you hit them |
| 5+ / high throughput | All three patterns automated on a schedule |

The patterns compound: teaching lint messages → fewer bad PRs → less GC needed → less doc drift.
