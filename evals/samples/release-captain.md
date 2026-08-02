---
provenance: curated
grounding: repo-grounded 2026-07-25 — gates, operation IDs, and KB citations verified against this repository; the orders-service repo state is synthetic (see README.md § Refreshing a sample, capture prerequisite)
---

Tier: production — preview-and-approve gates ON, full TDD, complete DoD. (`CLAUDE.md` § Quality Tier)

# Baseline Sample: release-captain

Host: github (from .ai-playbook.toml). Detected via `.ai-playbook.toml [host]` per `skills/host-adapter/SKILL.md` § Configuration.

Loaded: story (STORY-002, with its `## Implementation` section via the small-story shortcut), review record (approved).

## Open

Release gates checked per `knowledge-base/release.md` § Release Gates:

- tests pass (`make test` green in this session)
- lint clean (`make lint`, `make format-check`)
- story `stories/STORY-002-fix-harness-makefile-stack-override.md` has `status: done`
- diff size is under 400 hand-written lines
- branch `bugfix/harness-makefile-stack-override` has commits ahead of `main` — no empty PR

Creating PR through `skills/host-adapter/SKILL.md` only:

```text
host.pr.create(branch, title, body, base)
```

I never call `gh pr create` directly — the vendor-neutral operation ID is the contract.

## Watch

CI watch loop, re-polling every 60 seconds for up to 30 minutes:

```text
host.pr.checks(ref)
```

No merge while any check is pending or red. If CI is red, stop and hand off: `Say 'use xp-pair-programmer — fix CI failure for STORY-002'`. release-captain does not patch CI from this role.

## Merge Gate

Per-merge approval gate (`CLAUDE.md` § Shared Rules § Approval gate):

Ready to merge bugfix/harness-makefile-stack-override into main via squash. Say 'merge' to proceed.

After the explicit signal, call `host.pr.merge(ref, method='squash')`. I never auto-merge and never bypass branch protection.

## Release

Bug fix → PATCH bump per `knowledge-base/release.md` § Version Bump and Tag: 1.4.2 to 1.4.3 in `pyproject.toml`. Move `[Unreleased]` entries in `CHANGELOG.md` into `[1.4.3] - 2026-07-25`, add a fresh `[Unreleased]` heading, then create the release commit:

```text
chore(release): 1.4.3
```

Push `release/v1.4.3` only after its external-side-effect approval, then open
a release PR with `host.pr.create`. Watch `host.pr.checks`, require review, and
use the per-merge approval gate before `host.pr.merge` — the release PR precedes tagging.

After the release PR merges, fetch `origin/main`, verify the remote
default-branch commit contains version `1.4.3` and the new changelog section,
then create the annotated tag on that exact commit:

```text
git tag -a v1.4.3 <verified-origin-main-commit> -m "Release v1.4.3"
```

Ready to push tag v1.4.3 to origin. This is an external side effect. Say 'push' to proceed.

## Smoke

After the tag workflow completes, run `knowledge-base/release.md` § Post-Deploy Smoke (first run seeds `docs/runbooks/post-deploy.md` from `templates/runbook-template.md`):

- health endpoint
- error rate
- latency p95
- deploy smoke: `ai-playbook doctor` on a sample project

If any signal fails: apply `knowledge-base/release.md` § Rollback first, emit `smoke_fail` via `skills/notifier/SKILL.md`, and hand off with `Say 'use incident-responder — investigate post-deploy <signal> regression'`.

## Story Evidence

Append PR URL, merge commit, tag `v1.4.3`, release workflow link, and smoke result to `stories/STORY-002-fix-harness-makefile-stack-override.md`; emit `release_shipped` via `skills/notifier/SKILL.md` on a clean run.

```text
Released v1.4.3. Merged bugfix/harness-makefile-stack-override, tagged v1.4.3, smoke PASS.
```

Final phase report: Open -> Watch -> Merge -> Release -> Smoke -> Handoff. Offered `skills/retrospective/SKILL.md` to capture KB lessons from this release.
