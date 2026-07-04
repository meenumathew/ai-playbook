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
#   4. Counts Read calls per session in .claude/read-budget/<session>.count.
#   5. At >=80% of cap: allows with a stderr warning. Over cap: exits 2,
#      which blocks the Read and tells the agent to stop and ask the user.
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

# Most recent agent marker wins (agents may switch mid-session).
AGENT="$(grep -oE 'Active agent: [a-z][a-z-]*' "$TRANSCRIPT" 2>/dev/null | tail -1 | sed 's/^Active agent: //')"
[ -n "$AGENT" ] || exit 0

AGENT_FILE="${AGENTS_DIR}/${AGENT}.agent.md"
[ -f "$AGENT_FILE" ] || exit 0

BUDGET="$(sed -n 's/^read-budget:[[:space:]]*//p' "$AGENT_FILE" | head -1 | tr -d ' ')"
case "$BUDGET" in
  ''|self-tracked) exit 0 ;;
  *[!0-9]*) exit 0 ;;  # malformed => fail open
esac

mkdir -p "$STATE_DIR" 2>/dev/null || exit 0
COUNT_FILE="${STATE_DIR}/${SESSION_ID}.count"
COUNT="$(cat "$COUNT_FILE" 2>/dev/null || echo 0)"
case "$COUNT" in *[!0-9]*|'') COUNT=0 ;; esac
NEXT=$((COUNT + 1))

if [ "${CLAUDE_SKIP_READ_BUDGET:-0}" = "1" ]; then
  printf '%s\n' "$NEXT" > "$COUNT_FILE" 2>/dev/null
  echo "⚠ CLAUDE_SKIP_READ_BUDGET=1 set — read-budget enforcement bypassed (read ${NEXT}, cap ${BUDGET} for ${AGENT})." >&2
  exit 0
fi

if [ "$NEXT" -gt "$BUDGET" ]; then
  # Blocked reads are not counted — the cap stays the cap on retry.
  cat >&2 <<EOF
✗ Read budget reached: ${AGENT} has used ${COUNT} of ${BUDGET} reads this session.
Per CLAUDE.md § Shared Rules (read budget), STOP and ask the user before
reading more. Narrow the question, cite what you already read, and either
finish with current context or ask the user to extend the budget
(CLAUDE_SKIP_READ_BUDGET=1 for this session).
EOF
  exit 2
fi

printf '%s\n' "$NEXT" > "$COUNT_FILE" 2>/dev/null

# Duplicate-read detection: re-reading a file already read this session is
# pure budget waste (its content is in context). Warn-only — a re-read after
# an external change can be legitimate.
if [ -n "$READ_PATH" ]; then
  PATHS_FILE="${STATE_DIR}/${SESSION_ID}.paths"
  if [ -f "$PATHS_FILE" ] && grep -Fxq "$READ_PATH" "$PATHS_FILE" 2>/dev/null; then
    echo "⚠ Read budget: ${READ_PATH} already read this session — its content is in context; duplicate reads waste budget." >&2
  else
    printf '%s\n' "$READ_PATH" >> "$PATHS_FILE" 2>/dev/null
  fi
fi

WARN_AT=$(( (BUDGET * 8 + 9) / 10 ))  # ceil(80%)
if [ "$NEXT" -ge "$WARN_AT" ]; then
  echo "⚠ Read budget: ${AGENT} at ${NEXT}/${BUDGET} reads — narrow focus (CLAUDE.md § Shared Rules)." >&2
fi
exit 0
