# Eval Input: Release Captain

## Context

Story `stories/STORY-002-fix-harness-makefile-stack-override.md` is complete. xp-pair-programmer has committed all task commits to the local branch `bugfix/harness-makefile-stack-override`. diff-reviewer has run and posted `Review complete — approved.` to the review record.

## Repository state

```text
Branch: bugfix/harness-makefile-stack-override (3 commits ahead of main)
Working tree: clean
Remote: origin → https://github.com/acme/orders-service.git
.ai-playbook.toml:
  [host]
  provider = "github"
  base_branch = "main"
```

## CHANGELOG.md (current)

```markdown
## [Unreleased]

### Fixed
- Build tooling honours per-project command overrides on unrecognised stacks (STORY-002)
```

## Project manifest

```toml
# pyproject.toml
[project]
name = "orders-service"
version = "1.4.2"
```

## User request

```text
Use release-captain — open the PR for STORY-002 and ship vNN when CI is green.
```
