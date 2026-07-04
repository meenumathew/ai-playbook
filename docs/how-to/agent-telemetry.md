# How to wire up and read agent telemetry

Goal: log enough about unattended agent runs (CI, scheduled jobs, hosted runners) to debug failures and spot cost hotspots without re-running the session. Optional in interactive sessions; useful in unattended ones.

## Prerequisites

- The playbook is deployed to Claude Code (`ai-playbook deploy --tool claude`).
- `jq` installed for the token fields and the analysis queries below.

## What gets captured

One JSON line per session-end in `.claude/usage.jsonl`:

| Capture | Where | Notes |
|---|---|---|
| Session ID, timestamp, turn count | `.claude/usage.jsonl` | The `Stop` hook payload provides session_id + transcript_path |
| Active agent (best-effort) | Same file | Grepped from the transcript: see `harness/telemetry.sh` |
| Dominant model + token totals | Same file (`model`, `tokens.{input,output,cache_creation,cache_read}`) | Summed from the transcript JSONL the Stop payload points at; requires `jq` |
| Story/plan/audit reference handled | Same file (when the agent records it explicitly) | Ties agent runs back to artifacts |
| Approval gates triggered and outcome | Out of scope for the basic hook | Requires the agent itself to log; not in the v1 hook |

**Scope note (operational, not financial).** Token totals reflect the transcript and are accurate for comparing agents/sessions; they will not match the provider's billing to the cent (cache pricing, service tier, rounding differ). Use them for spotting Opus-on-everything and budgeting context; use the provider's billing export for invoicing.

**Harness scope.** Token capture reads the Claude Code transcript JSONL. Other harnesses (Cursor, Copilot, Continue) write different formats: those adopters get timestamp/session_id/turns but no `tokens` block. Correct degraded behaviour, not a bug.

## Steps

### 1. Deploy the hook

`ai-playbook deploy --tool claude` copies `harness/telemetry.sh`, makes it executable, and merges the `hooks.Stop` command into `.claude/settings.json`. Existing settings are preserved. If the JSON is malformed, deploy leaves it untouched, writes a `.broken-<timestamp>` copy, and reports the recovery step.

1. Run `ai-playbook deploy --agent all --tool claude` without `--no-harness`.
2. Run any agent. After session end, check `.claude/usage.jsonl`: one line per session.
3. Read via `/status`: the slash command parses the last 5 sessions and prints them alongside tier and active agent.

For local-only or custom settings, copy the block from `harness/settings.example.json` into `.claude/settings.local.json`. The hook calls `${CLAUDE_PROJECT_DIR}/harness/telemetry.sh`.

The hook never blocks the agent: it silently degrades to "log what we can, skip what we cannot" if `jq` is missing or the transcript is unreadable.

### 2. Read the log

```bash
# Sessions per agent in the last week
jq -r 'select(.timestamp > "'$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)'") | .active_agent' \
  .claude/usage.jsonl | sort | uniq -c | sort -rn

# Average turns per agent
jq -r '[.active_agent, .turns] | @tsv' .claude/usage.jsonl \
  | awk '{count[$1]++; sum[$1]+=$2} END {for (a in count) printf "%s\t%.1f\n", a, sum[a]/count[a]}'

# Total output tokens per agent: find the Opus-on-trivial-work hotspots
jq -r 'select(.tokens != null) | [.active_agent, .tokens.output] | @tsv' .claude/usage.jsonl \
  | awk '{sum[$1]+=$2} END {for (a in sum) printf "%s\t%d\n", a, sum[a]}' | sort -k2 -rn

# Cache-hit ratio (cache_read / (cache_creation + cache_read)) per agent: high is good
jq -r 'select(.tokens != null) | [.active_agent, .tokens.cache_creation, .tokens.cache_read] | @tsv' \
  .claude/usage.jsonl | awk '{c[$1]+=$2; r[$1]+=$3} END {for (a in c) {t=c[a]+r[a]; printf "%s\t%.0f%%\n", a, (t>0?100*r[a]/t:0)}}'
```

Adopters needing per-message cost should pair this hook with the provider billing export: keep operational (this hook) separate from financial (the provider).
