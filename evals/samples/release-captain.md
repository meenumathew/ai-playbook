---
provenance: curated
---

Tier: production — preview-and-approve gates ON, full TDD, complete DoD.

# Baseline Sample: release-captain

Host: github (from .ai-playbook.toml).

## Open

Release gates checked per `knowledge-base/release.md` § Release Gates:

- tests pass
- lint clean
- story `stories/STORY-042-email-shipment-notification.md` has `status: done`
- diff size is under 400 lines
- branch has commits ahead of `main`

Creating PR through `skills/host-adapter/SKILL.md` only:

```text
host.pr.create(branch, title, body, base)
```

I never call `gh pr create` directly.

## Watch

Polling CI with:

```text
host.pr.checks(ref)
```

If CI is red, stop and hand off: `Say 'use xp-pair-programmer — fix CI failure for STORY-042'`.

## Merge Gate

Ready to merge feature/email-shipment into main via squash. Say 'merge' to proceed.

After approval, call `host.pr.merge(ref, method='squash')`. I never auto-merge and never bypass branch protection.

## Release

Feature release bumps 1.4.2 to 1.5.0. Move `[Unreleased]` entries into `[1.5.0] - 2026-05-22`, then create the release commit:

```text
chore: release v1.5.0
```

Create an annotated tag:

```text
git tag -a v1.5.0 -m "Release v1.5.0"
```

Ready to push tag v1.5.0 to origin. This is an external side effect. Say 'push' to proceed.

## Smoke

After the tag workflow completes, run `knowledge-base/release.md` § Post-Deploy Smoke:

- health check
- error rate
- latency p95
- shipment email domain KPI

If any signal fails: apply `knowledge-base/release.md` § Rollback first and hand off with `Say 'use incident-responder — investigate post-deploy <signal> regression'`.

## Story Evidence

Append PR URL, merge commit, tag `v1.5.0`, release workflow link, and smoke result to `stories/STORY-042-email-shipment-notification.md`.

Final phase report: Open -> Watch -> Merge -> Release -> Smoke -> Handoff.
