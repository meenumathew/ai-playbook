# Eval Input: Release Captain

## Context

Story `stories/STORY-042-order-email-notifications.md` is complete. xp-pair-programmer has committed all task commits to the local branch `feature/order-email`. diff-reviewer has run and posted `Review complete — approved.` to the review record.

## Repository state

```text
Branch: feature/order-email (3 commits ahead of main)
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

### Added
- Order shipped email notifications (STORY-042)
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
Use release-captain — open the PR for STORY-042 and ship vNN when CI is green.
```
