#!/bin/sh
# AI Playbook read-budget enforcement — PreToolUse hook for the Read tool.
#
# Mechanizes the CLAUDE.md § Shared Rules read-budget protocol (report count,
# narrow at 80%, STOP at cap). Each agent declares `read-budget: <N>` (or
# `self-tracked`) in its frontmatter; agents print `Active agent: <id>` when
# adopting a role. This hook:
#   1. Reads the PreToolUse payload (session_id, transcript_path) from stdin.
#   2. Finds the most recent `Active agent: <id>` marker in the transcript.
#   3. Looks up that agent's `read-budget:` in .claude/agents/<id>.agent.md.
#   4. Counts Read calls per session AND agent in
#      .claude/read-budget/<session>.<agent>.count (one line appended per
#      allowed read; the count is the line count, so parallel Reads cannot
#      lose updates) — an agent switch resets the count so the new agent
#      never inherits the previous agent's reads.
#      Duplicate-read detection stays per-session (<session>.paths): a file
#      already in context is in context regardless of which agent read it.
#   5. At >=80% of cap: allows, emitting PreToolUse hook JSON on stdout
#      (hookSpecificOutput.additionalContext) so the MODEL sees the warning
#      (stderr on exit 0 is never shown to it). Over cap: exits 2, which
#      blocks the Read and tells the agent to stop and ask the user.
#
# Fail-open policy: no marker, no budget, `self-tracked`, unreadable
# transcript, or missing jq fallback data => allow silently (exit 0). This
# hook must never break a session it cannot attribute.
#
# Wire-up (opt-in — this hook BLOCKS tool calls at the cap, so it is never
# auto-merged by deploy): add to .claude/settings.json under
# hooks.PreToolUse with matcher "Read"; see harness/settings.example.json.
#
# Skip flag: CLAUDE_SKIP_READ_BUDGET=1 allows everything (bypass notice on
# stderr). Use sparingly — every skip is a deliberate exception.

set -u

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-.}"
STATE_DIR="${PROJECT_DIR}/.claude/read-budget"
AGENTS_DIR="${PROJECT_DIR}/.claude/agents"

PAYLOAD="$(cat 2>/dev/null || echo '{}')"

if command -v jq >/dev/null 2>&1; then
  SESSION_ID="$(printf '%s' "$PAYLOAD" | jq -r '.session_id // "unknown"' 2>/dev/null || echo unknown)"
  TRANSCRIPT="$(printf '%s' "$PAYLOAD" | jq -r '.transcript_path // ""' 2>/dev/null || echo '')"
  READ_PATH="$(printf '%s' "$PAYLOAD" | jq -r '.tool_input.file_path // ""' 2>/dev/null || echo '')"
else
  SESSION_ID="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"session_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  TRANSCRIPT="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"transcript_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  READ_PATH="$(printf '%s' "$PAYLOAD" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -1)"
  [ -n "$SESSION_ID" ] || SESSION_ID="unknown"
fi

# No transcript => cannot attribute => fail open.
[ -n "$TRANSCRIPT" ] && [ -f "$TRANSCRIPT" ] || exit 0

# Most recent agent marker wins (agents may switch mid-session). With jq,
# only assistant-message text is searched: tool results carry read-file
# contents, and any file containing the literal marker would otherwise flip
# attribution (and with it, whose budget is charged). Without jq the raw
# grep remains as a documented best-effort.
if command -v jq >/dev/null 2>&1; then
  AGENT="$(jq -r '
      select(.type == "assistant") | .message
      | if type == "string" then . else ((.content // [])[]? | .text? // empty) end
    ' "$TRANSCRIPT" 2>/dev/null \
      | grep -oE 'Active agent: [a-z][a-z-]*' | tail -1 | sed 's/^Active agent: //')"
else
  AGENT="$(grep -oE 'Active agent: [a-z][a-z-]*' "$TRANSCRIPT" 2>/dev/null | tail -1 | sed 's/^Active agent: //')"
fi
[ -n "$AGENT" ] || exit 0

AGENT_FILE="${AGENTS_DIR}/${AGENT}.agent.md"
[ -f "$AGENT_FILE" ] || exit 0

BUDGET="$(sed -n 's/^read-budget:[[:space:]]*//p' "$AGENT_FILE" | head -1 | tr -d ' ')"
case "$BUDGET" in
  ''|self-tracked) exit 0 ;;
  *[!0-9]*) exit 0 ;;  # malformed => fail open
esac

# Sanitize payload-derived values before using them in filesystem paths —
# same character allowlist telemetry.sh uses. A hostile transcript or payload
# must not be able to traverse out of the state directory.
SESSION_ID="$(printf '%s' "$SESSION_ID" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-128)"
AGENT="$(printf '%s' "$AGENT" | tr -cd 'A-Za-z0-9._:-' | cut -c 1-64)"
[ -n "$SESSION_ID" ] || SESSION_ID="unknown"
[ -n "$AGENT" ] || exit 0

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
# Prune stale per-session state — the directory otherwise grows forever
# (one .count plus one .paths file per session, on every adopter machine).
# 7 days comfortably outlives any resumable session.
find "$STATE_DIR" -type f -mtime +7 -exec rm -f {} + 2>/dev/null
# Keyed by session AND agent: a mid-session role switch starts the new agent
# at zero instead of inheriting the previous agent's read count.
COUNT_FILE="${STATE_DIR}/${SESSION_ID}.${AGENT}.count"
# One line is appended per allowed read; the count is the line count.
# O_APPEND appends are atomic, so parallel Read calls (Claude batches them)
# cannot lose updates the way a read-increment-rewrite cycle does.
COUNT="$(wc -l < "$COUNT_FILE" 2>/dev/null | tr -d '[:space:]')"
case "$COUNT" in *[!0-9]*|'') COUNT=0 ;; esac
NEXT=$((COUNT + 1))

# Accumulates warn-only notices; flushed as ONE PreToolUse hook JSON object
# on stdout before exit (two objects on stdout would be invalid hook output).
CONTEXT_NOTES=""

_append_note() {
  if [ -n "$CONTEXT_NOTES" ]; then
    CONTEXT_NOTES="${CONTEXT_NOTES} $1"
  else
    CONTEXT_NOTES="$1"
  fi
}

# Emit accumulated notices as PreToolUse hook JSON (schema: hookSpecificOutput
# with hookEventName + additionalContext; permissionDecision is deliberately
# omitted so the normal permission flow is untouched).
_flush_notes() {
  [ -n "$CONTEXT_NOTES" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    jq -nc --arg ctx "$CONTEXT_NOTES" \
      '{hookSpecificOutput:{hookEventName:"PreToolUse",additionalContext:$ctx}}' 2>/dev/null
  else
    # No jq: keep only JSON-safe characters (drops quotes, backslashes, and
    # control bytes) so the hand-built JSON below can never be malformed.
    SAFE_NOTES="$(printf '%s' "$CONTEXT_NOTES" | tr -cd 'A-Za-z0-9 ._:/,()-')"
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' \
      "$SAFE_NOTES"
  fi
}

if [ "${CLAUDE_SKIP_READ_BUDGET:-0}" = "1" ]; then
  printf '.\n' >> "$COUNT_FILE" 2>/dev/null
  echo "WARNING: CLAUDE_SKIP_READ_BUDGET=1 set — read-budget enforcement bypassed (read ${NEXT}, cap ${BUDGET} for ${AGENT})." >&2
  exit 0
fi

if [ "$NEXT" -gt "$BUDGET" ]; then
  # Blocked reads are not counted — the cap stays the cap on retry.
  cat >&2 <<EOF
ERROR: Read budget reached: ${AGENT} has used ${COUNT} of ${BUDGET} reads this session.
Per CLAUDE.md § Shared Rules (read budget), STOP and ask the user before
reading more. Narrow the question, cite what you already read, and either
finish with current context or ask the user to extend the budget
(CLAUDE_SKIP_READ_BUDGET=1 for this session).
EOF
  exit 2
fi

printf '.\n' >> "$COUNT_FILE" 2>/dev/null

# Duplicate-read detection: re-reading a file already read this session is
# pure budget waste (its content is in context). Warn-only — a re-read after
# an external change can be legitimate. Deliberately per-session, not
# per-agent: the file content is in the session context either way.
if [ -n "$READ_PATH" ]; then
  PATHS_FILE="${STATE_DIR}/${SESSION_ID}.paths"
  if [ -f "$PATHS_FILE" ] && grep -Fxq "$READ_PATH" "$PATHS_FILE" 2>/dev/null; then
    _append_note "Read budget: ${READ_PATH} already read this session — its content is in context; duplicate reads waste budget."
  else
    printf '%s\n' "$READ_PATH" >> "$PATHS_FILE" 2>/dev/null
  fi
fi

WARN_AT=$(( (BUDGET * 8 + 9) / 10 ))  # ceil(80%)
if [ "$NEXT" -ge "$WARN_AT" ]; then
  _append_note "Read budget: ${AGENT} at ${NEXT}/${BUDGET} reads — narrow focus (CLAUDE.md § Shared Rules)."
fi
_flush_notes
exit 0
