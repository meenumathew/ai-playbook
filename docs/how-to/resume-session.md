# How To Resume a Session

## Goal

Pick up exactly where you left off after a context reset, tool switch, or new session: without re-explaining the story or codebase.

## Prerequisites

- A plan file at `plans/PLAN-NNN-*.md` (created by slice-planner), **or**
- A story file at `stories/STORY-NNN-*.md` with an `## Implementation` section (small-story shortcut)

## Steps

### 0. Find the Artifact When You Do Not Know the Path

```bash
ai-playbook artifacts --query user-validation
```

The command searches story, research, plan, audit, review, and incident artifacts by path and file contents.

### 1. Point the Agent at the Plan

```text
Use xp-pair-programmer: plan is at plans/PLAN-001-user-validation.md
```

The agent reads the plan's `## Progress` section and resumes at the first incomplete task.

### 2. Specify a Task When No Progress Section Exists

On the first session a plan has no `## Progress` section yet. Tell the agent which task to start at:

```text
Use xp-pair-programmer: plan is at plans/PLAN-001-user-validation.md: we are on Task 3
```

### 3. Switch AI Tools Mid-story

Artifacts are plain markdown files in the repo, not stored under `~/.claude/` or any tool-specific location. To switch tools mid-story:

1. Commit or stash in-progress work.
2. Open the new AI tool.
3. Point it at the same plan file.

### 4. Verify the Agent Loaded Context

After invocation, the agent reports what it found:

```text
Loaded: story (STORY-001), research (RESEARCH-001), plan (PLAN-001).
Resuming at Task 3: "Add email validation".
```

If no `Loaded:` line appears, re-check file naming: `STORY-NNN`, `PLAN-NNN`, and `RESEARCH-NNN` must share the same `NNN`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Agent starts from scratch | Plan path is wrong or the file is empty | Verify with `ai-playbook artifacts --query <slug>` |
| Agent repeats completed work | `## Progress` section not updated | Mark completed tasks in the plan |
| `No matching story` | Numbering mismatch between story and plan | Align the `NNN` across files |
| Research not loaded | Research file uses a different `NNN` | Rename to `RESEARCH-NNN-*.md` |

## Related

- [Architecture § File-based Resumability](../architecture.md#4-file-based-resumability): why this design works
- [Invoke Agents](invoke-agents.md): start a fresh session
