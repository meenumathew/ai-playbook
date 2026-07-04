# How To Invoke Agents

## Goal

Start any agent with the correct input so it produces the right artifact on the first try.

## Prerequisites

- AI Playbook deployed into your project: `ai-playbook deploy --agent all --tool <claude|copilot|cursor|kiro>`
- Runtime directories created: `stories/`, `plans/`, `research/`, `audits/`, `reviews/`, and `incidents/`
- Team artifact policy decided: run `ai-playbook artifact-policy shared` when generated story, research, plan, audit, review, and incident files are shared records, or `ai-playbook artifact-policy local` when they are local working notes.

## Steps

### 1. Name the Agent Explicitly

Always state the agent name. Without one the AI tool guesses, and the guess is often wrong.

| You have | You want | Say |
|---|---|---|
| An idea or plain description | A refined story artifact | `Use story-refiner: here's the feature: ...` |
| A tracker work item reference | A refined story artifact | `Use story-refiner: PROJ-1234` or `Use story-refiner: #42` |
| A story (by number) | A task breakdown | `Use slice-planner: STORY-001` |
| A story number | Start coding now | `Use xp-pair-programmer: STORY-001` |
| A tracker work item reference (story artifact exists) | Start coding now | `Use xp-pair-programmer: PROJ-1234` or `Use xp-pair-programmer: #42` |
| A finished diff or PR | A code review (local) | `Use diff-reviewer: STORY-001` |
| A GitHub PR number or URL | A code review (remote) | `Use diff-reviewer: review PR #42, STORY-001` |
| A module, layer, or whole repo | A codebase audit | `Use code-inspector: audit src/auth` |
| A new or changed API, or a doc/ADR need | Updated docs | `Use docs-maintainer for this module` |

### 2. Provide Work Item Input

Any of these four formats works: pick whichever is easiest:

1. **Story artifact number**: `STORY-001` or just `001`
2. **File path**: `stories/STORY-001-slug.md`
3. **Inline paste**: copy the work item, story, bug report, task, or feature description into the message
4. **Tracker reference**: Jira key (`PROJ-1234`), GitHub issue or Project item (`#42`, `org/repo#42`), GitLab issue, Bitbucket issue, Linear ID (`ENG-101`), or tracker URL

Any of these triggers artifact-chain resolution: the agent auto-loads matching research and plan files with the same `NNN`. External tracker terms stay outside the contract; internally the playbook writes a story artifact with `issue-ref:` preserving the original work item identity.

### 3. Use the Right Invocation Syntax

| Tool | Slash command | Natural language |
|------|---------------|------------------|
| Claude | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Copilot | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Cursor | `/story-refiner <input>` | `Use story-refiner: <input>` |
| Kiro | Not supported | `Use story-refiner: <input>` |

Kiro does not support custom slash commands: use natural language.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent starts but loads no context | Story number does not match any file | Check `stories/` for the exact filename |
| Wrong agent activated | The agent name was not stated | Always prefix with `Use <agent-name>` |
| `Story not found` | Tracker MCP or CLI not configured | Paste work item content manually, or configure the integration: see [Set Up Project Management Tool](setup-issue-tracker.md) |

## Related

- [CLI Reference § Agents](../cli-reference.md#agents): full list of agents and their purpose
- [Set Up Project Management Tool](setup-issue-tracker.md): configure Jira, GitHub Issues/Projects, GitLab, Bitbucket, or Linear
- [Run With Local Models](run-with-local-models.md): use Ollama, LM Studio, or any OpenAI-compatible local server
- [Resume a Session](resume-session.md): pick up where you left off
