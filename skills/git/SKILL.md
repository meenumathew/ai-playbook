---
name: git
description: 'Complete git workflow: Conventional Commits, branching (GitHub Flow), squashing, merge conflict resolution. Use when user asks to commit, branch, squash, merge, or manage PRs.'
user-invocable: false
license: MIT
---

# Git Workflow

Approval gate: `CLAUDE.md` § Shared Rules applies to all commits and merges. NEVER skip hooks (`--no-verify`) unless user asks.

## Repository Rules

- Default branch: `main` (branch from it)
- One branch per feature/bugfix/task
- Merge via PR only (never push direct to `main`)

## Branch Naming

Format: `{type}/{short-description}`. With issue tracker: `{type}/PROJ-1234-{short-description}`.

| Type | When |
|------|------|
| `feature/` | New feature |
| `fix/` | Bug fix |
| `hotfix/` | Urgent production fix: branch off main, merge back immediately |
| `refactor/` | Code refactor |
| `test/` | Add/update tests |
| `docs/` | Documentation |
| `chore/` | Maintenance/dependencies |

## Worktrees (parallel / isolated sprints)

Use when sessions run in parallel or branch switching is expensive.

```bash
git worktree add ../proj-feature-x feature/feature-x   # new branch, sibling dir
git worktree list                                       # see all
git worktree remove ../proj-feature-x                   # clean up after merge
```

One worktree per active branch. Tests/deps/env per worktree. Remove after merge.

## Conventional Commit Format

```text
<type>(optional scope): <description>

[optional body: explain WHY, not what]

[optional footer(s)]
```

### Commit Types

| Type | Purpose |
|------|---------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting/style (no logic) |
| `refactor` | Code refactor (no feature/fix) |
| `perf` | Performance improvement |
| `test` | Add/update tests |
| `build` | Build system/dependencies |
| `ci` | CI/config changes |
| `chore` | Maintenance/misc |
| `revert` | Revert commit |

### Scope

Optional. Short lowercase token for the affected module (`auth`, `api`, `db-migrations`). Hyphens allowed. Omit if no meaningful label.

**Reserved scopes**: keep consistent across the playbook:

| Scope | Used for | Example |
|---|---|---|
| `kb` | Knowledge-base updates from `skills/retrospective/SKILL.md` | `docs(kb): add retry pattern to design-patterns` |
| `release` | Version bumps and tag commits from `agents/release-captain.agent.md` | `chore(release): v1.4.0` |
| `adr` | New or superseded ADRs under `docs/adr/` | `docs(adr): record auto-merge policy` |

### SemVer Correlation

The point of the types (Conventional Commits 1.0.0 § relation to SemVer): `fix:` → PATCH, `feat:` → MINOR, any `!`/`BREAKING CHANGE:` → MAJOR. Release tooling and humans both read version impact straight off the log.

### Breaking Changes

```text
feat!: remove deprecated endpoint

feat: allow config to extend other configs

BREAKING CHANGE: `extends` key behavior changed
```

## Commit Workflow

1. **Stage**: `git add` specific files (never `-A` without reviewing)
2. **Message**: determine type, optional scope, description (present tense, imperative, <72 chars)
3. **Commit**: use HEREDOC for multi-line messages:

   ```bash
   git commit -m "$(cat <<'EOF'
   <type>(optional scope): <description>

   <optional body: explain WHY, not what>
   EOF
   )"
   ```

### Message Rules

| Rule | Agent action |
|------|-------------|
| One logical change per commit | Split unrelated changes into separate commits |
| Present tense, imperative mood | "add feature" not "added" or "adds" |
| Description under 72 characters | Overflow goes in body |
| Body explains **why**, not what | The diff shows what changed |

### Teach-back Trailer

Canonical home for the trailer format, required-type list, and skip list: `CLAUDE.md` § Definition of Done, agent files, and `knowledge-base/philosophy.md` cite this section instead of restating the lists. The lists here and in `harness/check-teachback.sh` must match; a contract test pins them in sync.

Required on `feat`, `fix`, `refactor`, `perf`, `test` commits: one line in the body:

```text
Teach-back: <one sentence: what the change does and where to debug it>
```

Example:

```text
feat(auth): add JWT refresh endpoint

Rotates the access token without forcing a re-login. Closes the
30-day-stale-session report from #214.

Teach-back: adds /v1/auth/refresh in apps/api/auth/handlers.py; failures surface as 401 with code "refresh.expired".
```

**Skip list**: no trailer required for `chore`, `docs`, `style`, `build`, `ci`, `revert`. The diff already explains these.

**Enforcement.** `harness/check-teachback.sh` is the `commit-msg` hook (wired in `harness/pre-commit-config.yaml`). Blocks commits with missing/empty trailers for non-skip-list types. Emergency override: `CLAUDE_SKIP_TEACHBACK=1 git commit ...`: every skip is a DoD exception.

**Why it exists.** `CLAUDE.md` § Definition of Done already requires teach-back. The trailer turns the checkbox into mechanism: one line in history that survives review six months later.

## Squashing Commits

**When:** user asks: never automatically.

```bash
git log --oneline main..HEAD        # branch commits
git reset --soft HEAD~N             # squash N commits
git commit -m "<type>(scope): <description>"
```

- Squashed message describes completed behaviour, not TDD steps.
- Run tests before and after squashing.
- Post-review: keep review-fix commits during review; squash only after approval.

## Merge Conflict Resolution

### 1. Assess

```bash
git status && git branch --show-current
```

If no merge in progress and user wants to merge:

```bash
git fetch origin <branch>
git log --oneline --graph HEAD..origin/<branch> -10
```

Ask: "Ready to merge? This brings in X commits."

### 2. Start merge and show conflicts

```bash
git merge origin/<branch>
git diff --name-only --diff-filter=U   # conflicting files
```

For each: offer keep-ours, keep-theirs, or manual merge. Wait for user direction. Never auto-resolve.

### 3. Resolve (user-directed)

```bash
# ours
git checkout --ours <file> && git add <file>

# theirs
git checkout --theirs <file> && git add <file>

# manual: edit file, then git add <file>
```

Bulk resolve if user says "take theirs/ours for all":

```bash
git diff --name-only --diff-filter=U | while read file; do
  git checkout --theirs "$file" && git add "$file"
done
```

### 4. Verify and test

```bash
git diff --check              # no conflict markers remain
git diff --staged --stat      # what will be committed
```

Run tests. If failing: stop, show failures, then fix or stop the merge (`git merge --abort`).

### 5. Commit (only on approval)

Show `git diff --staged --stat`, summarize changes. Wait per `CLAUDE.md` § Shared Rules § Approval gate.

```bash
git commit -m "$(cat <<'EOF'
Merge branch '<source>' into <target>

<explain what conflicts were resolved and how>
EOF
)"
```

### Stopping a Merge

If user asks to stop or cancel: `git merge --abort && git status`

### Error Recovery

If committed too early, prefer `git revert`. Use history-rewrite (reset/amend) only with explicit user instruction.
