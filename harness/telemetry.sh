#!/bin/sh
# AI Playbook privacy-minimal local telemetry.
#
# Captures only:
#   - timestamp (UTC)
#   - source tool (claude or codex)
#   - approximate turn count (transcript line count)
#   - active playbook agent (best-effort marker lookup)
#
# Never stores or transmits session IDs, transcript paths/content, prompts,
# outputs, model names, token/cache counts, repository contents, or credentials.
# The transcript is read locally only to count lines and find the public
# `Active agent: <id>` marker. Failure never blocks the agent.
#
# Hook use:
#   Claude Stop:     harness/telemetry.sh
#   Codex SessionEnd: harness/telemetry.sh codex

set -u

SOURCE_TOOL="${1:-claude}"
case "$SOURCE_TOOL" in
  claude|codex) ;;
  *) exit 0 ;;
esac

if [ -n "${AI_PLAYBOOK_PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$AI_PLAYBOOK_PROJECT_DIR"
elif [ -n "${CLAUDE_PROJECT_DIR:-}" ]; then
  PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  PROJECT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
fi
USAGE_FILE="${PROJECT_DIR}/.${SOURCE_TOOL}/usage.jsonl"

# New names are tool-neutral; CLAUDE_* fallbacks preserve existing adopter
# configuration. A malformed threshold disables rotation instead of risking
# rotate-on-every-hook data loss.
USAGE_MAX_BYTES="${AI_PLAYBOOK_USAGE_MAX_BYTES:-${CLAUDE_USAGE_MAX_BYTES:-1048576}}"
USAGE_KEEP_ARCHIVES="${AI_PLAYBOOK_USAGE_KEEP_ARCHIVES:-${CLAUDE_USAGE_KEEP_ARCHIVES:-12}}"

mkdir -p "$(dirname "$USAGE_FILE")" 2>/dev/null || exit 0

_rotate_usage_log() {
  # A malformed threshold must disable rotation, never enable it. The
  # length cap keeps the value inside shell integer range: an overflowing
  # all-digit value would make the -le test error and rotate every Stop.
  case "$USAGE_MAX_BYTES" in ''|*[!0-9]*) return 0 ;; esac
  [ "${#USAGE_MAX_BYTES}" -le 15 ] || return 0
  case "$USAGE_KEEP_ARCHIVES" in ''|*[!0-9]*) USAGE_KEEP_ARCHIVES=12 ;; esac
  [ "${#USAGE_KEEP_ARCHIVES}" -le 6 ] || USAGE_KEEP_ARCHIVES=12
  [ "$USAGE_MAX_BYTES" = "0" ] && return 0
  [ -f "$USAGE_FILE" ] || return 0
  size="$(wc -c < "$USAGE_FILE" 2>/dev/null | tr -d ' ')"
  case "$size" in ''|*[!0-9]*) return 0 ;; esac
  [ "$size" -le "$USAGE_MAX_BYTES" ] && return 0

  archive_dir="$(dirname "$USAGE_FILE")"
  archive_name="usage-$(date -u +%Y%m%dT%H%M%SZ).jsonl"
  mv "$USAGE_FILE" "$archive_dir/$archive_name" 2>/dev/null || return 0
  if command -v gzip >/dev/null 2>&1; then
    gzip "$archive_dir/$archive_name" 2>/dev/null
  fi

  # Archive pruning intentionally needs `ls -t` modification-time ordering.
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
  TRANSCRIPT="$(printf '%s' "$PAYLOAD" | jq -r '.transcript_path // ""' 2>/dev/null || echo '')"
else
  TRANSCRIPT="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
fi

TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo unknown)"
TURNS=0
ACTIVE_AGENT="unknown"
if [ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ]; then
  TURNS="$(wc -l < "$TRANSCRIPT" 2>/dev/null | tr -d ' ' || echo 0)"
  if [ "$SOURCE_TOOL" = "claude" ] && command -v jq >/dev/null 2>&1; then
    ACTIVE_AGENT="$(jq -r '
        select(.type == "assistant") | .message
        | if type == "string" then . else ((.content // [])[]? | .text? // empty) end
      ' "$TRANSCRIPT" 2>/dev/null \
        | grep -oE 'Active agent: [a-z][a-z-]*' | tail -1 | sed 's/^Active agent: //' || echo '')"
  else
    ACTIVE_AGENT="$(grep -oE 'Active agent: [a-z][a-z-]*' "$TRANSCRIPT" 2>/dev/null | tail -1 | sed 's/^Active agent: //' || echo '')"
  fi
  if [ -z "$ACTIVE_AGENT" ]; then
    ACTIVE_AGENT="$(grep -ioE 'use[d ]+(the )?(story-refiner|slice-planner|xp-pair-programmer|diff-reviewer|release-captain|incident-responder|code-inspector|docs-maintainer)' "$TRANSCRIPT" 2>/dev/null | tail -1 | awk '{print tolower($NF)}' || echo unknown)"
  fi
fi

case "$TURNS" in
  ''|*[!0-9]*) TURNS=0 ;;
esac
[ -n "$ACTIVE_AGENT" ] || ACTIVE_AGENT="unknown"

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --arg timestamp "$TIMESTAMP" \
    --arg source "$SOURCE_TOOL" \
    --arg active_agent "$ACTIVE_AGENT" \
    --argjson turns "$TURNS" \
    '{timestamp:$timestamp,source:$source,turns:$turns,active_agent:$active_agent}' \
    >> "$USAGE_FILE" 2>/dev/null || true
else
  SAFE_ACTIVE_AGENT="$(printf '%s' "$ACTIVE_AGENT" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-64)"
  [ -n "$SAFE_ACTIVE_AGENT" ] || SAFE_ACTIVE_AGENT="unknown"
  printf '{"timestamp":"%s","source":"%s","turns":%s,"active_agent":"%s"}\n' \
    "$TIMESTAMP" "$SOURCE_TOOL" "$TURNS" "$SAFE_ACTIVE_AGENT" >> "$USAGE_FILE" 2>/dev/null
fi

exit 0
