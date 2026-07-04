---
id: model-tier
size: small
tldr: Agents declare advisor or executor tier; tier names are the contract, not model IDs.
load_when: model tier, advisor, executor, model config, escalation, single model setup
audience: all
canonical_for: tier definitions, escalation triggers, single-model setups, quality floor
cross_refs: working-agreement.md
verified: 2026-07-02
---

# Model Tier

## Agent Use

- **Read first:** Tier Definitions, Escalation Triggers, Single-Model Setups, Quality Floor.
- **Load deeper only on trigger:** provider examples and cost/latency background.

---

## Why Tier Names, Not Model IDs

Each agent declares `model: advisor` or `model: executor` in its frontmatter. These names are the contract: agents never reference Opus, Sonnet, GPT-4, or any specific model. The mapping from tier to actual model lives in `.ai-playbook.toml` and the AI tool's config.

Tier-based abstraction means:

- Swapping models is a config change, not a repo edit
- The same agent files work on Anthropic, OpenAI, Google, or local models
- Free, paid, mixed-provider, and local-only setups all use identical agents

---

## Tier Definitions

| Tier       | Role                                              | Used by                                                  |
|------------|---------------------------------------------------|----------------------------------------------------------|
| `advisor`  | Deeper reasoning; planning, review, audit, ship/incident judgement | story-refiner, slice-planner, diff-reviewer, code-inspector, release-captain, incident-responder |
| `executor` | High-volume execution; TDD cycles, drafting docs  | xp-pair-programmer, docs-maintainer                                 |

Per-agent assignment lives in each agent file's frontmatter (`agents/<name>.agent.md`).

---

## Configuration

Declare the intended tier-to-model mapping in the adopter project root:

```toml
[model_tiers]
advisor = "strong-reasoning-model"
executor = "fast-execution-model"
```

`ai-playbook doctor` warns when the table is missing or when either tier is empty. Single-model setups are valid: set both tiers to the same model name and route escalation triggers to a human review checkpoint.

Ollama-backed tools fit the same contract. Use the model identifiers your AI tool expects for its Ollama provider:

```toml
[model_tiers]
advisor = "ollama:strong-local-model"
executor = "ollama:fast-local-model"
```

If the tool exposes only one Ollama model, set both tiers to the same identifier and follow the single-model rules below.

---

## Deploying to Claude Code

`ai-playbook deploy --tool claude` materializes the `[model_tiers]` mapping into deployed agent frontmatter: `model: advisor`/`model: executor` becomes `model: opus`/`model: sonnet`/`model: haiku`/`model: inherit` (or a full `claude-*` model ID) wherever the configured value is one Claude Code understands natively. Source files under `agents/` always keep the tier name: only the deployed copy in `.claude/agents/` is rewritten, and only the frontmatter `model:` line, never prose.

Values Claude Code can't interpret directly (e.g. `ollama:qwen3:32b`) are left as the tier name in the deployed copy, and `deploy` prints a note explaining why: those adopters' tools do their own tier-to-model mapping, same as before this feature existed. `diff` and `doctor` apply the identical rewrite when checking for drift, so a clean deploy always reports up to date. Other targets (copilot, cursor, kiro) have no per-agent model field and are never rewritten.

---

## Reference Notes

The sections below explain deployment choices. Load only when configuring models, costs, escalation, or single-model setups.

### Capability Mapping

| Tier | Minimum capability | Cost / latency bias | Red flags |
|------|--------------------|---------------------|-----------|
| `advisor` | Handles ambiguity, multi-file reasoning, security tradeoffs, and long-context synthesis | Spend more when the decision can reshape scope or architecture | Invents requirements, misses contradictions, or cannot explain tradeoffs |
| `executor` | Follows existing patterns, writes tests, applies small refactors, and fixes focused failures | Optimize for speed and cost on repeated edit-test loops | Repeats failed fixes, weakens tests, or needs broad context to make small edits |

The pattern is *capability gap*, not specific brands. Any stronger / faster pairing works: cloud-only, local-only, mixed cloud/local, or free/single-model.

---

### Escalation Triggers

When an executor-tier agent hits one of these, stop the current session and re-run the agent on the advisor tier: no silent model switching mid-session:

- **xp-pair-programmer:** 3 failed fix attempts (`debugging.md` § Iron Law + § 3-Fix Architectural Stop Rule) before attempting fix #4
- **docs-maintainer:** writing an ADR or architecture-level doc
- **Any executor agent:** "I don't know" twice in one session on the same question

---

### Single-Model Setups (Free Tier, Local-Only)

If your AI tool runs one model for everything (no advisor/executor distinction available), declare both tiers with the same model name:

```toml
[model_tiers]
advisor = "same-local-model"
executor = "same-local-model"
```

Then:

- Agents still work: the workflow honours tier names even if both resolve to the same model
- Escalation triggers route to a **human review checkpoint** instead of a model switch: pause, surface the blocker, ask the user before proceeding
- This is *stricter* than the paid path, not weaker: TDD red-green, quality gates, and Definition of Done remain unchanged

---

### Quality Floor

The tier split is a **cost / latency optimisation**, not a quality safety net. These mechanisms enforce quality:

- Test discipline (`testing.md`): RED-GREEN catches executor errors the same turn
- Quality gates: lint, types, tests, secrets, architecture
- Definition of Done (`CLAUDE.md` § Definition of Done)
- Cognitive Health Gates (`philosophy.md` § Cognitive Health): comprehension checkpoint + `Teach-back:` trailer with decision rationale

If the underlying model is competent enough to pass these gates, the tier split is safe. If it is not, tighten the gates: do not blame the tier.
