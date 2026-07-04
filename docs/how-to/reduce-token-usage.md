# How to reduce token usage without losing quality

Goal: cut the playbook's per-session token cost while keeping the gates that protect quality.

The cost structure drives every lever below. The fixed per-session surface is the always-loaded rules file (~20 KB, capped by a ratcheted CI size gate) plus `CHEATSHEET.md` (the one KB file whose `load_when:` is `always`); together they are paid on **every turn**. Agent files load once per invocation, and an agent's `preload:` frontmatter inlines the named KB files with it, so an agent's real cost is its file plus its preloads. Every other knowledge-base file loads only when its `load_when:` keywords fire, with `INDEX.md` loaded on a CHEATSHEET miss to route the lookup.

## Prerequisites

- The playbook is deployed (`ai-playbook deploy --tool <tool>`).
- You know which agents and languages your team actually uses.

## Steps

### 1. Deploy less surface

```bash
ai-playbook deploy --agent all --tool claude --language python   # only your language's KB files
ai-playbook deploy --agent story-refiner,xp-pair-programmer,diff-reviewer --tool claude
ai-playbook disable incident-responder --tool claude             # reversible trial
```

Skip what you do not use: `--no-mcp` when you have no issue tracker, `--no-harness` when your repo already has its own hooks.

### 2. Use the built-in loading discipline

The knowledge base is designed for on-demand loading: agents try `CHEATSHEET.md` first, escalate through `INDEX.md`, and stop when the rule is actionable. Do not paste knowledge-base files into prompts: the `load_when:` routing makes that redundant and doubles the cost. The one sanctioned exception is agent `preload:` frontmatter, which inlines a KB file an agent needs on effectively every run; treat each preload as a per-invocation cost you are choosing to pay, and keep the list minimal.

### 3. Keep the always-loaded prefix stable

Prompt caching discounts repeated context heavily, but only while the prefix is unchanged. Batch your edits to the rules file and `CHEATSHEET.md`: every edit invalidates the cache for every team member's next session. The rules-file size budget helps both size and cache stability.

### 4. Match the model tier to the step

Map `executor` tier to a fast model for the edit/test loop and reserve the stronger `advisor` model for refining, planning, and review: see `knowledge-base/model-tier.md` § Capability Mapping. Check `.claude/usage.jsonl` (or `/status`) for token totals per agent to spot an over-provisioned tier.

### 5. Use the tier and lane switches for low-stakes work

Set `quality-tier: prototype` for spikes and experiments: narrow read budgets, lean artifacts, save-and-summarize. Use the fast lane for urgent small fixes (`docs/how-to/choose-workflow-path.md` § Use the Fast Lane for Urgent Small Fixes). Both reduce tokens by design while keeping security checks and verification.

### 6. Enforce read budgets by mechanism (Claude Code, opt-in)

Each agent declares `read-budget:` in its frontmatter, and `harness/read-budget.sh` (a PreToolUse hook) counts Read calls per session against the active agent's cap: it warns at 80% and blocks over-cap reads with a stop-and-ask message. Wire it up by copying the `PreToolUse` block from `harness/settings.example.json` into `.claude/settings.json`. It is opt-in because it blocks tool calls at the cap; escape hatch: `CLAUDE_SKIP_READ_BUDGET=1`. Attribution comes from the `Active agent: <id>` marker each agent prints on role adoption; the same marker gives `usage.jsonl` reliable per-agent rows, so you can see which agent or tier is over-provisioned.

### 7. Practice session hygiene (the biggest lever the playbook cannot automate)

Long sessions dominate real-world spend: past ~150k context every turn is expensive even when cached, and 8-hour sessions compound it. The playbook's workflow gives you natural cut points: use them.

- **Story boundary = `/clear`.** A finished story's context is sunk cost; the artifacts (story, plan, code, commits) carry everything forward. Start the next story clean.
- **Agent switch = `/compact` candidate.** The one-agent-at-a-time rule already checkpoints on switch; compacting there keeps the checkpoint and drops the transcript bulk.
- **Long implementation = `/compact` mid-task.** The plan file's `## Progress` section exists precisely so a compacted (or fresh) session can resume at Task N, Step M without re-reading history.

### 8. Spend subagents deliberately

Subagent fan-out multiplies requests: each subagent pays its own context. Two rules of thumb:

- **Fan out for audits and research** (parallel reviewers earn their cost by coverage); **stay inline for implementation** (TDD needs the accumulated context a subagent lacks).
- **Route exploratory/mechanical subagents to a cheaper model** where your tool supports per-subagent model config: the advisor/executor tier logic (`knowledge-base/model-tier.md`) applies to subagents too: deep judgment gets the strong model, file-finding and summarising do not.

### 9. Avoid the common waste patterns

Trends seen across AI-assisted teams, and the counter-practice this playbook (or plain discipline) already provides:

| Waste pattern | Why it burns tokens | Do instead |
|---|---|---|
| Pasting whole files or logs into chat | The agent pays for every pasted line, then often re-reads the file anyway | Give the path; let the agent read selectively under its read budget |
| Re-explaining the project every session | Context rebuilt from scratch daily | Durable rules file + KB; session facts belong in artifacts (story, plan `## Progress`), not chat history |
| Letting the agent re-discover the codebase per session | Exploration is the most expensive read pattern | Resume from artifacts: `Loaded: story, research, plan` replaces hours of re-exploration |
| Retrying a failed fix by repeating the prompt | Each thrash loop replays the full context | The 3-fix stop rule (`knowledge-base/debugging.md`): stop, question the design, escalate |
| Dumping full test/CI output into the conversation | A 2,000-line log to find one failure | Pipe through `tail`/filters; paste the failing test and its traceback only |
| Asking the LLM to do what deterministic tools do free | Formatting, import sorting, license headers, scaffolding | `make format`, linters, codegen: the agent runs tools, it should not *be* the tool |
| Reviewing generated diffs by AI | Lockfiles and snapshots are noise at token prices | Exempt generated/mechanical lines (the 400-line rule § Code Review Norms counts hand-written only) |
| Every subagent and session on the top model | Flat pricing for non-flat work | Tier routing (`knowledge-base/model-tier.md`); cheap models for mechanical subagents |
| Kitchen-sink MCP/tool attachment | Every attached tool's schema rides in every request | Attach the servers this project uses (`--no-mcp` exists for a reason); prune unused ones |
| Debugging by conversation | Long speculative ping-pong about what code *might* do | Run the command, read the output: evidence is cheaper than dialogue |
| Never clearing between tasks | Yesterday's story taxes today's turns | § 7 session hygiene: story boundary = `/clear` |

## What not to cut

Research depth, validation runs, security checks, and approval gates. Their token cost is small next to the always-loaded prefix, and removing them converts token savings into rework. The Concise Communication rule in the rules file draws this line: compress output verbosity, never compress checks.

## Verification

After trimming, run `ai-playbook doctor --tool <tool>`: a healthy report confirms the reduced deployment is still complete for the agents you kept.
