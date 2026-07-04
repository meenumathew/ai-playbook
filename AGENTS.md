# AGENTS.md

This file is a tool-agnostic entry point for AI coding tools that read `AGENTS.md` first (Cursor, Cline, Aider, OpenAI Codex, and several emerging tools follow this convention).

**Canonical rules live in [`CLAUDE.md`](CLAUDE.md).** That file is the single source of truth for the playbook's workflow, quality tiers, approval gates, and shared rules: for every tool, not only Claude Code. The filename is a historical artefact; the content is universal.

## Why CLAUDE.md, not AGENTS.md

The repository pre-dates the `AGENTS.md` convention. Re-canonicalising would invalidate every adopter's deployed `CLAUDE.md` (a covered surface under [`docs/deprecation-policy.md`](docs/deprecation-policy.md)). Instead, this `AGENTS.md` exists as a stable bridge: when a future tool agrees on `AGENTS.md` discovery, it lands here and is told where to read further.

If a future RFC migrates the canonical filename, this bridge stays as the redirect.

## Multi-tool deployment

The playbook ships a CLI that writes the right files into the right places for each supported tool:

| Tool             | Rules file                      | Agents directory       | Slash commands           |
|------------------|----------------------------------|------------------------|--------------------------|
| Claude Code      | `CLAUDE.md`                      | `.claude/agents/`      | `.claude/commands/`      |
| GitHub Copilot   | `.github/copilot-instructions.md`| `.github/agents/`      | `.github/prompts/`       |
| Cursor           | `.cursor/rules/ai-playbook.mdc`  | `.cursor/agents/`      | `.cursor/commands/`      |
| Kiro             | `.kiro/steering/rules.md`        | `.kiro/agents/`        | (no slash commands)      |

Run:

```bash
ai-playbook deploy --agent all --tool <claude|copilot|cursor|kiro>
```

Additional tool targets (Cline, Continue, Aider, Goose, Cody, Gemini CLI) are candidates for a future release and not yet supported by the CLI.

## Invoking an agent

How you trigger an agent depends on the tool:

- **Claude Code**: slash commands from `.claude/commands/` (for example `/story-refiner`), or natural language.
- **GitHub Copilot**: prompt files in `.github/prompts/`, or natural language.
- **Cursor**: slash commands from `.cursor/commands/`, or natural language.
- **Kiro, and `AGENTS.md`-only tools (Cline, Aider, Ollama-backed tools, OSS/local models)**: no slash commands; invoke by name in natural language, for example "Use the story-refiner agent to refine this story." The behaviour comes from the deployed `agents/<id>.agent.md` file, not from a command shim.

Agent files sometimes use shorthand such as `use slice-planner: STORY-NNN`; read it as "invoke that agent for that artifact" by whatever mechanism your tool offers. Approval gates are tool-neutral: where an agent pauses for explicit approval (commit, merge, tag push, artifact save), give that approval in plain language the same way on every tool: see [`CLAUDE.md`](CLAUDE.md) § Shared Rules § Approval gate.

## What an AI tool should read first

1. [`CLAUDE.md`](CLAUDE.md): always loaded; the universal rules.
2. [`knowledge-base/CHEATSHEET.md`](knowledge-base/CHEATSHEET.md): one-line digest covering ~80% of cases.
3. [`knowledge-base/INDEX.md`](knowledge-base/INDEX.md): routing table for every other knowledge-base file (load on demand only).

The `agents/` directory is a workflow vocabulary, not a hardcoded pipeline. See `CLAUDE.md` § Workflow for which agent fits which task.

## What this file does NOT do

- It does not duplicate the rules from `CLAUDE.md`. Duplication would drift; canonical-with-pointer is the durable shape.
- It does not replace `CLAUDE.md`. Tools that already read `CLAUDE.md` continue to do so.
- It does not register new agent definitions. Agents live in [`agents/`](agents/) and deploy via the CLI above.

If you are reading this manually because your tool found `AGENTS.md` and not `CLAUDE.md`, follow the link above. Everything else flows from there.
