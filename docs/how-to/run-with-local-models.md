# How To Run the Playbook With Local / Open-Source Models

## Goal

Use the AI Playbook with locally-hosted, open-source models (Ollama, LM Studio, or any OpenAI-compatible endpoint) instead of a paid Claude / OpenAI / Gemini subscription. The playbook is model-agnostic: agents declare tier names (`advisor` / `executor`), not model IDs: so a config change is enough.

## Prerequisites

- AI Playbook deployed: `ai-playbook deploy --agent all --tool <tool>`
- A locally-hosted model server running (Ollama, LM Studio, or equivalent)
- An AI coding tool that can target a custom endpoint directly or through a protocol bridge.

| Tool | Local-model path |
|---|---|
| Ollama | OpenAI-compatible API at `http://localhost:11434/v1` |
| LM Studio | OpenAI-compatible API at `http://localhost:1234/v1` |
| llama.cpp `server` | OpenAI-compatible API at the configured port |
| Anything else | Any OpenAI-compatible `/v1/chat/completions` endpoint works |

## Steps

### 1. Pick Your Local Models

Pick one model for `advisor` (deeper reasoning) and one for `executor` (high-volume execution). They can be the same model: see `knowledge-base/model-tier.md` § Single-Model Setups.

| Tier | Suggested local models | Notes |
|---|---|---|
| `advisor` | Qwen3 32B, DeepSeek-R1 32B/70B, Llama 3.3 70B, gpt-oss 120B | Stronger reasoning; a 32B quantised fits ~24 GB VRAM, 70B+ needs ≥48 GB or Apple Silicon unified memory |
| `executor` | Qwen2.5-Coder 14B, Qwen3 8B, Devstral 24B, gpt-oss 20B | Faster, lower memory; coding-tuned models earn their keep here |
| Single-model | Whichever fits your hardware | Both tiers map to the same model: escalations route to a human checkpoint |

The pattern is *capability gap*, not specific brands: see `knowledge-base/model-tier.md` § Capability Mapping. Open-model releases date quickly: check the [Ollama library](https://ollama.com/library) for current versions; the tier contract stays the same regardless of which models you slot in.

### 2. Start Your Local Server

#### Option A: Ollama

```bash
# Install: https://ollama.com/download
ollama pull qwen3:32b               # advisor
ollama pull qwen2.5-coder:14b       # executor
ollama serve                        # default: http://localhost:11434
```

Test:

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:14b","messages":[{"role":"user","content":"hi"}]}'
```

#### Option B: LM Studio

1. Install: <https://lmstudio.ai/>
2. Download your chosen models from the LM Studio UI (Discover tab)
3. Start the local server (Developer tab → Start Server): defaults to `http://localhost:1234`

#### Option C: Other OpenAI-compatible servers

`llama.cpp`, `vllm`, `text-generation-inference`, and `litellm` all expose OpenAI-compatible endpoints. Configure the same way as Options A and B; only the port changes.

### 3. Connect Your AI Tool

Prefer native OpenAI-compatible configuration when your tool supports it. Use a bridge only when the tool's protocol differs from your local server.

| Path | Use when |
|---|---|
| Native OpenAI mode | Some tools (Continue, Aider) talk directly to OpenAI-compatible endpoints, no bridge needed |
| [`litellm`](https://docs.litellm.ai/) proxy | Translating between Anthropic / OpenAI / local: most flexible |
| Tool-specific bridge | Your coding tool only speaks a provider-specific protocol |

Tool-specific note for Claude-compatible clients:

```bash
export ANTHROPIC_BASE_URL=http://localhost:4000   # litellm proxy
export ANTHROPIC_API_KEY=local-no-auth-needed     # any non-empty string
```

Bridge installation is upstream-specific: follow the bridge's own quickstart and keep tokens local.

### 4. Configure `[model_tiers]`

Add or update `.ai-playbook.toml` in your project root. The tier-to-model mapping is declarative: agents read tier names (`advisor` / `executor`), not model IDs.

```toml
[model_tiers]
advisor  = "qwen3:32b"          # or whatever your bridge exposes
executor = "qwen2.5-coder:14b"
```

For single-model setups (one model serving both tiers):

```toml
[model_tiers]
advisor  = "qwen3:14b"
executor = "qwen3:14b"
```

`ai-playbook doctor` warns if `[model_tiers]` is missing or either tier is empty.

### 5. Verify

Start a small refinement task:

```text
Use story-refiner: Add input validation to get_user in src/users.py
```

Confirm the story file lands in `stories/STORY-NNN-*.md` with the standard structure (Intent / AC / Estimate / Boundaries). If the agent invents AC or skips research, you're hitting the model's reasoning ceiling: see Quality Floor below.

## Quality Floor

The tier split is a **cost / latency optimisation**, not a quality safety net. The same gates that protect paid setups protect local ones: see `knowledge-base/model-tier.md` § Quality Floor.

| Mechanism | Effect |
|---|---|
| Test discipline (`testing.md`) | RED-GREEN catches executor errors the same turn |
| Quality gates (`make quality`) | Lint, types, tests, secrets, architecture |
| Definition of Done (`CLAUDE.md` § Definition of Done) | Final checkpoint before commit |
| Cognitive Health Gates (`philosophy.md` § Cognitive Health) | Comprehension checkpoint + `Teach-back:` trailer |

**Single-model setups are stricter, not weaker.** Escalation triggers (e.g. xp-pair-programmer hits the 3-fix architectural stop rule) route to a **human review checkpoint** instead of a model swap: see `knowledge-base/model-tier.md` § Single-Model Setups. You read the diff yourself before continuing.

If the local model can pass the gates, the setup is safe. If it cannot, tighten the gates: do not blame the tier.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Tool reports `connection refused` | Local server not running, or wrong port | Run `curl <endpoint>/v1/models` to confirm; restart server |
| Tool ignores `[model_tiers]` | For non-Claude tools and for unrecognized values (such as `ollama:*`), the tier-to-model mapping lives in the AI tool's config, not the deployed files; the playbook passes the tier name through unchanged | Map your tier names to actual model IDs in your tool's settings. (For `--tool claude`, `deploy` materializes recognized values into agent frontmatter instead; local-model identifiers are not recognized and still pass through here.) |
| Agent invents acceptance criteria or skips research | Model is too small for advisor-tier reasoning | Drop to a smaller, simpler story; or upgrade the advisor tier; or accept the human-checkpoint escalation pattern |
| `make quality` fails on lint or types | Local model output doesn't follow project conventions | Lower the verbosity, lean on existing repo patterns, escalate to human review on repeat failures |
| Bridge throws `model not found` | Bridge expects an aliased name | Configure the bridge's model alias to point at your local model name |

## Related

- [Set Up Your Project Management Tool](setup-issue-tracker.md): adapter pattern for tracker config
- [Invoke Agents](invoke-agents.md): once your local-model setup works
- `knowledge-base/model-tier.md` § Single-Model Setups: escalation pattern when one model serves both tiers
- `knowledge-base/model-tier.md` § Quality Floor: what guards quality independent of model choice
- `templates/.ai-playbook.toml.example`: full config example
