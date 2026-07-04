#!/bin/sh
# AI Playbook — Teach-back trailer enforcement.
#
# Pre-commit framework `commit-msg` hook. Reads the commit message file
# (passed as $1 by pre-commit / git) and rejects the commit if it uses an
# unsupported Conventional Commit type or if a non-trivial commit type is
# missing a `Teach-back:` trailer.
#
# Why: the playbook's Definition of Done already requires teach-back ("the
# developer can explain what the code does, where to debug it, and how it
# would change"). This hook turns the DoD checkbox into mechanism — one line
# in the commit body, enforced at the seam where prose meets git history.
#
# Skip list (no trailer required): `chore`, `docs`, `style`, `build`, `ci`,
# `revert`. Commits with `!` for breaking changes are
# treated as their underlying type (e.g. `feat!:` requires the trailer).
#
# Skip flag: set CLAUDE_SKIP_TEACHBACK=1 to bypass for emergencies (incident
# rollback, automated revert). Use sparingly — every skip is a DoD exception.
#
# Failure policy: prints a one-line error and the suggested trailer format,
# exits 1 to abort the commit. Never modifies the message.

set -eu

MSG_FILE="${1:-}"
if [ -z "$MSG_FILE" ] || [ ! -f "$MSG_FILE" ]; then
  # Pre-commit framework always passes the path; if it's missing assume the
  # caller invoked us wrong and pass through rather than blocking.
  exit 0
fi

if [ "${CLAUDE_SKIP_TEACHBACK:-0}" = "1" ]; then
  exit 0
fi

# Truncate at the scissors line `git commit -v` inserts — the staged diff
# below it is not part of the message — then strip comment lines. `|| true`
# keeps set -e happy when every line is a comment.
CONTENT="$(sed -n '/^# -\{1,\} >8 -\{1,\}$/q;p' "$MSG_FILE" | { grep -v '^#' || true; })"

# Subject = first non-blank, non-comment line. (Skipping leading blank lines
# matters: git strips them during cleanup, so the landed subject must be the
# one validated here.)
SUBJECT="$(printf '%s\n' "$CONTENT" | sed '/^[[:space:]]*$/d' | head -1)"
[ -z "$SUBJECT" ] && exit 0  # empty message — let git's own check fail it

# Git's generated merge/revert subjects and autosquash fixup!/squash!/amend!
# subjects are not Conventional Commit subjects, but they are low-value to
# block and are created by tooling (fixup commits are ephemeral — the rebase
# folds them into a commit that was already validated).
case "$SUBJECT" in
  [Mm]erge\ *|[Rr]evert\ *|fixup!\ *|squash!\ *|amend!\ *)
    exit 0
    ;;
esac

if ! printf '%s' "$SUBJECT" | grep -Eq '^[A-Za-z]+(\([^)]+\))?!?:'; then
  cat >&2 <<EOF
✗ Unsupported commit message format.

Use Conventional Commits:

    <type>(optional-scope): <description>

Allowed types: feat, fix, refactor, perf, test, chore, docs, style, build, ci, revert.
Why: CLAUDE.md § Commits.
EOF
  exit 1
fi

# Extract the Conventional Commit type and normalize case. Breaking-change
# markers (`!`) and scopes are intentionally ignored for type classification.
TYPE="$(printf '%s' "$SUBJECT" | sed -E 's/^([A-Za-z]+)(\([^)]+\))?!?:.*/\1/' | tr '[:upper:]' '[:lower:]')"

case "$TYPE" in
  chore|docs|style|build|ci|revert)
    exit 0  # skip-list type — trailer not required
    ;;
  feat|fix|refactor|perf|test)
    # Trailer required. `Teach-back:` must sit inside the trailing block of
    # `Key: value` trailer lines. This keeps it a durable git trailer (a stray
    # mention mid-body still fails) while allowing tool-appended trailers
    # after it — `git commit -s` adds Signed-off-by and Claude Code adds
    # Co-Authored-By as the final line.
    TRAILER_BLOCK="$(printf '%s\n' "$CONTENT" | sed '/^[[:space:]]*$/d' | awk '
      { lines[NR] = $0 }
      END {
        for (i = NR; i >= 1; i--) {
          if (lines[i] !~ /^[[:space:]]*[A-Za-z][A-Za-z0-9-]*:[[:space:]]*[^[:space:]]/) break
          print lines[i]
        }
      }')"
    if printf '%s\n' "$TRAILER_BLOCK" | grep -qiE '^[[:space:]]*Teach-back:[[:space:]]*[^[:space:]]'; then
      exit 0
    fi
    cat >&2 <<EOF
✗ Missing final Teach-back trailer.

This commit type ($TYPE) requires one line in the body explaining
WHAT the change does and WHERE to debug it. It must be part of the
final trailer block (other trailers like Signed-off-by / Co-Authored-By
may follow it):

    Teach-back: <one sentence — what + where to debug>

Example:

    feat(auth): add JWT refresh endpoint

    Teach-back: rotates the refresh token in the auth service; failures surface as 401s in apps/api/auth/handlers.py.

Skip list (no trailer needed): chore, docs, style, build, ci, revert.
Emergency override: CLAUDE_SKIP_TEACHBACK=1 git commit ...

Why: CLAUDE.md § Definition of Done. Honor-system became mechanism.
EOF
    exit 1
    ;;
  *)
    cat >&2 <<EOF
✗ Unsupported commit type: $TYPE.

Allowed types: feat, fix, refactor, perf, test, chore, docs, style, build, ci, revert.
Why: CLAUDE.md § Commits.
EOF
    exit 1
    ;;
esac
