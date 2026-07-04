#!/bin/sh
# AI Playbook session telemetry — Stop-hook driven append-only log.
#
# What this captures (honest list — what we can derive from the Stop payload
# plus the transcript file the payload points at):
#   - timestamp (UTC)
#   - session_id
#   - turn_count (line count of the transcript file = approx assistant+user turns)
#   - active_agent (best-effort grep of the last agent role from transcript)
#   - model (dominant model by output_tokens across the session)
#   - tokens (sum of input/output/cache_creation/cache_read across all
#     assistant messages in the transcript)
#
# Token capture requires `jq` and a readable transcript file; without either,
# the row degrades gracefully — `model` becomes "unknown" and tokens are
# omitted.
#
# Wire-up: add to .claude/settings.json under hooks.Stop. Path is resolved
# relative to the repo root; adopters who deploy elsewhere should set
# `CLAUDE_PROJECT_DIR` or use an absolute path in the hook config.
#
# Failure policy: this script never blocks the agent. Errors silently degrade
# to "log what we can, skip what we cannot".

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
USAGE_FILE="${PROJECT_DIR}/.claude/usage.jsonl"

# Rotate usage.jsonl when it exceeds CLAUDE_USAGE_MAX_BYTES (default 1 MiB).
# Industry-standard logrotate-style policy — keeps the live file small enough
# for adopters to grep, while preserving history in compressed archives. Set
# CLAUDE_USAGE_MAX_BYTES=0 to disable rotation.
USAGE_MAX_BYTES="${CLAUDE_USAGE_MAX_BYTES:-1048576}"
USAGE_KEEP_ARCHIVES="${CLAUDE_USAGE_KEEP_ARCHIVES:-12}"

mkdir -p "$(dirname "$USAGE_FILE")" 2>/dev/null || exit 0

_rotate_usage_log() {
  [ "$USAGE_MAX_BYTES" = "0" ] && return 0
  [ -f "$USAGE_FILE" ] || return 0
  size="$(wc -c < "$USAGE_FILE" 2>/dev/null | tr -d ' ' || echo 0)"
  [ "$size" -le "$USAGE_MAX_BYTES" ] && return 0

  archive_dir="$(dirname "$USAGE_FILE")"
  archive_name="usage-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
  mv "$USAGE_FILE" "$archive_dir/$archive_name" 2>/dev/null || return 0

  if command -v gzip >/dev/null 2>&1; then
    gzip "$archive_dir/$archive_name" 2>/dev/null
  fi

  # Prune old archives — keep most recent USAGE_KEEP_ARCHIVES.
  # `ls -t` newest-first; tail -n +<keep+1> drops the survivors.
  # Quoted glob expansion is intentional — ls handles missing files quietly.
  # shellcheck disable=SC2012
  ls -t "$archive_dir"/usage-*.jsonl* 2>/dev/null \
    | tail -n +"$((USAGE_KEEP_ARCHIVES + 1))" \
    | while IFS= read -r stale; do
        [ -n "$stale" ] && rm -f "$stale" 2>/dev/null
      done
}

_rotate_usage_log

PAYLOAD="$(cat 2>/dev/null || echo '{}')"

if command -v jq >/dev/null 2>&1; then
  SESSION_ID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)"
  TRANSCRIPT="$(printf '%s' "$PAYLOAD" | jq -r '.transcript_path // ""' 2>/dev/null || echo '')"
else
  SESSION_ID="unknown"
  TRANSCRIPT=""
fi

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"

TURNS=0
ACTIVE_AGENT="unknown"
MODEL="unknown"
TOKENS_OBJECT=""
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  TURNS="$(wc -l < "$TRANSCRIPT" 2>/dev/null | tr -d ' ' || echo 0)"
  # Attribution, most reliable first:
  #   1. The deterministic `Active agent: <id>` marker every agent prints on
  #      role adoption (CLAUDE.md § Shared Rules, One agent at a time) — the
  #      most recent marker wins on mid-session switches.
  #   2. Fallback heuristic: the most recent "Use <agent>" invocation phrase.
  #      -i matters: the documented style is capitalised ("Use story-refiner:").
  ACTIVE_AGENT="$(grep -oE 'Active agent: [a-z][a-z-]*' "$TRANSCRIPT" 2>/dev/null | tail -1 | sed 's/^Active agent: //' || echo '')"
  if [ -z "$ACTIVE_AGENT" ]; then
    ACTIVE_AGENT="$(grep -ioE 'use[d ]+(the )?(story-refiner|slice-planner|xp-pair-programmer|diff-reviewer|release-captain|incident-responder|code-inspector|docs-maintainer)' "$TRANSCRIPT" 2>/dev/null | tail -1 | awk '{print tolower($NF)}' || echo unknown)"
  fi
  [ -z "$ACTIVE_AGENT" ] && ACTIVE_AGENT="unknown"

  # Token roll-up — only when jq is available. Sums across every assistant
  # message that carries .message.usage in the transcript JSONL. Dominant
  # model = the model with the most output_tokens.
  if command -v jq >/dev/null 2>&1; then
    TOKEN_SUMS="$(jq -r -s '
      map(select(.type == "assistant" and .message.usage != null)) as $msgs
      | {
          input:          ($msgs | map(.message.usage.input_tokens // 0)                | add // 0),
          output:         ($msgs | map(.message.usage.output_tokens // 0)               | add // 0),
          cache_creation: ($msgs | map(.message.usage.cache_creation_input_tokens // 0) | add // 0),
          cache_read:     ($msgs | map(.message.usage.cache_read_input_tokens // 0)     | add // 0)
        }
      | "\(.input) \(.output) \(.cache_creation) \(.cache_read)"
    ' "$TRANSCRIPT" 2>/dev/null || echo "0 0 0 0")"
    MODEL="$(jq -r -s '
      map(select(.type == "assistant" and .message.model != null and .message.usage != null))
      | sort_by(.message.model)
      | group_by(.message.model)
      | map({model: .[0].message.model, out: (map(.message.usage.output_tokens // 0) | add // 0)})
      | sort_by(.out)
      | reverse
      | .[0].model // "unknown"
    ' "$TRANSCRIPT" 2>/dev/null || echo unknown)"
    [ -z "$MODEL" ] && MODEL="unknown"

    # shellcheck disable=SC2086
    set -- $TOKEN_SUMS
    if [ "$#" -eq 4 ]; then
      TOKENS_OBJECT="$(jq -nc \
        --argjson input "$1" \
        --argjson output "$2" \
        --argjson cache_creation "$3" \
        --argjson cache_read "$4" \
        '{input:$input,output:$output,cache_creation:$cache_creation,cache_read:$cache_read}' \
        2>/dev/null || echo '')"
    fi
  fi
fi

case "$TURNS" in
  ''|*[!0-9]*) TURNS=0 ;;
esac

if command -v jq >/dev/null 2>&1; then
  if [ -n "$TOKENS_OBJECT" ]; then
    jq -nc \
      --arg timestamp "$TIMESTAMP" \
      --arg session_id "$SESSION_ID" \
      --arg active_agent "$ACTIVE_AGENT" \
      --arg model "$MODEL" \
      --argjson turns "$TURNS" \
      --argjson tokens "$TOKENS_OBJECT" \
      '{timestamp:$timestamp,session_id:$session_id,turns:$turns,active_agent:$active_agent,model:$model,tokens:$tokens}' \
      >> "$USAGE_FILE" 2>/dev/null || true
  else
    jq -nc \
      --arg timestamp "$TIMESTAMP" \
      --arg session_id "$SESSION_ID" \
      --arg active_agent "$ACTIVE_AGENT" \
      --arg model "$MODEL" \
      --argjson turns "$TURNS" \
      '{timestamp:$timestamp,session_id:$session_id,turns:$turns,active_agent:$active_agent,model:$model}' \
      >> "$USAGE_FILE" 2>/dev/null || true
  fi
else
  SAFE_SESSION_ID="$(printf '%s' "$SESSION_ID" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-128)"
  SAFE_ACTIVE_AGENT="$(printf '%s' "$ACTIVE_AGENT" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-64)"
  SAFE_MODEL="$(printf '%s' "$MODEL" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-128)"
  [ -n "$SAFE_SESSION_ID" ] || SAFE_SESSION_ID="unknown"
  [ -n "$SAFE_ACTIVE_AGENT" ] || SAFE_ACTIVE_AGENT="unknown"
  [ -n "$SAFE_MODEL" ] || SAFE_MODEL="unknown"
  printf '{"timestamp":"%s","session_id":"%s","turns":%s,"active_agent":"%s","model":"%s"}\n' \
    "$TIMESTAMP" "$SAFE_SESSION_ID" "$TURNS" "$SAFE_ACTIVE_AGENT" "$SAFE_MODEL" >> "$USAGE_FILE" 2>/dev/null
fi

exit 0
