# How to enable privacy-minimal agent telemetry

Goal: observe how often playbook agents run and how many transcript records a session produced, without retaining prompts, outputs, identifiers, model details, token counts, repository content, or credentials.

## Prerequisites

- The playbook is deployed to Claude Code or Codex.
- A POSIX shell is available for `harness/telemetry.sh`.
- `jq` is optional. The hook still writes its minimal event without it.

## What gets captured

Each session-end appends one JSON object to `.claude/usage.jsonl` or `.codex/usage.jsonl`:

| Field | Meaning |
|---|---|
| `timestamp` | UTC hook time |
| `source` | `claude` or `codex` |
| `turns` | Approximate transcript record count; `0` when unavailable |
| `active_agent` | Best-effort public `Active agent: <id>` marker; `unknown` when unavailable |

The hook never stores or transmits session IDs, transcript paths or content, prompts, outputs, model names, token/cache counts, repository content, or credentials. It reads the local transcript path only long enough to count records and locate an agent marker. It makes no network calls and never blocks the host tool.

This log is operational telemetry, not billing telemetry. Use `ai-playbook context-report` to measure the static playbook context surface. Use provider-native usage or billing exports for actual token and cost data.

## Steps

### 1. Deploy or enable the hook

Claude uses a `Stop` hook in `.claude/settings.json`:

```bash
ai-playbook deploy --agent all --tool claude
ai-playbook telemetry status --tool claude
```

Codex uses a `SessionEnd` hook in `.codex/hooks.json`:

```bash
ai-playbook deploy --agent all --tool codex
ai-playbook telemetry status --tool codex
```

Codex project hooks require explicit trust. Review the generated hook and approve it through `/hooks` before expecting events. Existing hook configuration is preserved. If the JSON is malformed, the CLI leaves it untouched, writes a `.broken-<timestamp>` copy, and reports the repair step.

If the harness was deployed separately, enable only the selected hook:

```bash
ai-playbook telemetry enable --tool <claude|codex>
```

### 2. Read the local log

Select the file for the active tool:

```bash
TELEMETRY_LOG=.claude/usage.jsonl  # use .codex/usage.jsonl for Codex

# Number of completed sessions per agent
jq -r '.active_agent' "$TELEMETRY_LOG" | sort | uniq -c | sort -rn

# Average approximate turns per agent
jq -r '[.active_agent, .turns] | @tsv' "$TELEMETRY_LOG" \
  | awk '{count[$1]++; sum[$1]+=$2} END {for (a in count) printf "%s\t%.1f\n", a, sum[a]/count[a]}'
```

Treat the files as machine-local state. `ai-playbook artifact-policy local` ignores both tools' current logs and rotated archives.

### 3. Rotate or disable it

The log rotates at 1 MiB and keeps 12 archives by default:

```bash
AI_PLAYBOOK_USAGE_MAX_BYTES=2097152
AI_PLAYBOOK_USAGE_KEEP_ARCHIVES=6
```

`CLAUDE_USAGE_MAX_BYTES` and `CLAUDE_USAGE_KEEP_ARCHIVES` remain compatibility aliases. Set the maximum bytes to `0` to disable rotation.

Disable collection without deleting existing local logs:

```bash
ai-playbook telemetry disable --tool <claude|codex>
```

Delete `.claude/usage*.jsonl*` or `.codex/usage*.jsonl*` separately when you no longer need the local aggregates.
