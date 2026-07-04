---
id: release
size: medium
tldr: Open PR/MR via host-adapter, wait for green CI, request reviewers, merge only on explicit approval, tag, smoke-test post-deploy; rollback before debugging if user impact is active.
load_when: release, ship, merge, deploy, post-deploy, smoke test, rollback, version bump, tag, branch protection
audience: release-captain, xp-pair-programmer (hotfix path), incident-responder (rollback)
canonical_for: release gates, merge strategies, post-deploy smoke checklist, rollback rules
cross_refs: incident-response.md, observability.md, security.md, skills/git/SKILL.md, skills/host-adapter/SKILL.md
verified: 2026-06-10
---

# Release Workflow

Source of truth for the post-merge path. Cited from `agents/release-captain.agent.md`.

## Agent Use

- **Read first:** Release Gates, Merge Strategies, Post-Deploy Smoke.
- **Load deeper only on trigger:** rollback, hotfix, version bump rules.

The playbook does not ship code to production by itself. release-captain orchestrates the path; humans approve the irreversible steps. **Auto-merge and auto-deploy are off by default; teams must not turn them on without an ADR documenting the trade-off.**

---

## Release Gates

Before opening a PR/MR for review:

| Gate | Verify |
|---|---|
| All tests pass locally | `make test` or project equivalent: green |
| Lint, format, type check | `make lint`, `make format-check`, `make typecheck`: clean |
| Security scan | Run project-specific secret, dependency, and static-analysis checks; this repo uses `gitleaks`, `detect-private-key`, `pip-audit`, and Bandit in CI |
| Quality gates | `knowledge-base/quality-gates.md`: all marked Pass |
| Story `status: done` | Set by xp-pair-programmer on completion |
| Diff size ≤ 400 hand-written lines | Generated content (lockfiles, codegen, snapshots), mechanical renames/moves, and deletions do not count. Larger PRs split per `working-agreement.md` § Code Review Norms |

Before requesting merge:

| Gate | Verify |
|---|---|
| diff-reviewer approved | Review record saved or `gh pr review --approve` posted |
| Required reviewers approved | Per host branch-protection rules |
| CI green | `host.pr.checks(ref)` all passing |
| No unresolved review threads | All Must Fix items resolved |
| Conflicts resolved | Branch up-to-date with base |

If any gate fails, fix the underlying issue. Never bypass with `--admin`, `--no-verify`, or branch-protection overrides without explicit user instruction.

---

## Merge Strategies

| Strategy | When |
|---|---|
| **Squash** | Default for feature branches; collapses TDD-cycle commits into one logical change |
| **Rebase + merge** | When commit history is already clean and each commit stands alone (refactors, multi-step migrations) |
| **Merge commit** | Long-lived release branches merging into main; preserves shared history. Avoid for feature → main. |

Set the default in `.ai-playbook.toml` under `[host].merge_strategy` if your team prefers a non-default. Override per-PR only with explicit user signal.

---

## Branch Protection (Recommended)

The playbook does not enforce branch protection: the host does. Recommended settings on the default branch:

- Require PR/MR for all changes (no direct push).
- Require at least one approving review.
- Require CI to pass before merge.
- Require branch to be up-to-date before merge.
- Restrict force-push and deletion.

If branch protection is missing, release-captain warns at session start: `Branch protection not detected on <base>. Recommend enabling: see knowledge-base/release.md.`

---

## Version Bump and Tag

Apply Semantic Versioning (`semver.org`):

| Bump | When |
|---|---|
| **PATCH** (0.0.x) | Bug fixes, doc-only changes, internal refactors |
| **MINOR** (0.x.0) | Backward-compatible new features |
| **MAJOR** (x.0.0) | Breaking changes: deprecation note required |

Steps:

1. Update version in the project's manifest (`pyproject.toml`, `package.json`, `Cargo.toml`, `pom.xml`).
2. Move `[Unreleased]` content in `CHANGELOG.md` to a new `[X.Y.Z] - YYYY-MM-DD` section, grouped under the six Keep-a-Changelog categories in canonical order: Added, Changed, Deprecated, Removed, Fixed, Security (omit empty ones). Add a fresh `[Unreleased]` heading.
3. Commit: `chore: release vX.Y.Z`. Approval gate applies.
4. Tag: `git tag vX.Y.Z`. Annotated tags preferred (`git tag -a vX.Y.Z -m "..."`).
5. Push tag: `git push origin vX.Y.Z`. Approval gate applies: pushing a tag is an external side effect.

Adopters with a custom release process (`RELEASING.md` at repo root) follow that file's steps; this section is the default when none exists.

---

## Post-Deploy Smoke

After deploy lands in the target environment, run the smoke checklist before declaring release complete:

| Check | Default signal |
|---|---|
| Service health endpoint | `GET /health/ready` returns 200 |
| Error rate | No new ERROR-level surge in the 10 minutes post-deploy |
| Latency p95 | Within ±20% of pre-deploy baseline |
| Critical user journey | One scripted journey passes (login, primary action, logout, or equivalent) |
| Domain signal | One business KPI (orders placed, predictions served, etc.) ticking as expected |

Define environment-specific signals in the project's runbook (`docs/runbooks/post-deploy.md`). The preceding defaults are starting points, not a substitute for a thought-through smoke set.

If any signal fails, **roll back first, debug second**.

---

## Rollback

Rollback is the lowest-risk action when production has degraded. Apply before investigating, unless the rollback itself would cause more harm (rare: usually only when a data migration ran).

| Rollback type | When | How |
|---|---|---|
| Revert deploy | Code change broke production | Redeploy previous artifact / image / tag |
| Revert commit | Bad commit on main but not yet promoted | `git revert <sha>` + new release |
| Toggle feature flag off | Feature has a flag | Flip flag in flag store; no redeploy needed |
| Database rollback | Migration broke writes | **Do not** auto-rollback migrations: coordinate with DBA / data team |

After rollback, open an incident record (`incident-response.md` § Triage Flow) and trace the cause before re-attempting the release.

---

## Hotfix

A hotfix is a minimal, audited change that ships outside the normal release cadence to resolve an active incident.

| Rule | Why |
|---|---|
| Branch off the production tag, not `main` | Avoids dragging in untested intermediate work |
| One commit, one fix, one test | Minimises scope; reviewable in seconds |
| Same diff-reviewer + release-captain path, accelerated | Speed comes from small scope, not skipped gates |
| Forward-merge into `main` immediately after deploy | Prevents needing the same fix twice |
| Postmortem follows | Even if the hotfix worked: see `incident-response.md` § Blameless Postmortem |

Branch name: `hotfix/<incident-ref>-<short-slug>` (`skills/git/SKILL.md` § Branch Naming).

---

## Delivery Metrics (DORA)

The four DORA metrics are the industry-standard health check for this whole workflow. The playbook's artifacts already produce the raw data: adopters instrument the measurement in their own analytics:

| Metric | Source in this playbook |
|--------|------------------------|
| Deployment frequency | Tags pushed by release-captain (`git tag` history) |
| Lead time for changes | First story commit → release tag (`git log`) |
| Change failure rate | Incidents whose postmortem names a release as the trigger (`incidents/`) |
| Time to restore service | Postmortem timeline, detection → resolution: see `incident-response.md` |

A degrading metric is a signal to inspect the workflow (slice size, review latency, smoke coverage), not to skip gates.

---

## What release-captain Does

- Opens PR/MR via `host.pr.create`.
- Watches CI via `host.pr.checks` until it reports green or failure.
- Surfaces review status; requests merge approval from the user.
- Performs version bump, tag, and push on explicit approval.
- Runs the post-deploy smoke checklist.

## What release-captain Does NOT Do

- Auto-merge. Merge requires the explicit user signal in `CLAUDE.md` § Shared Rules.
- Auto-deploy. Deploy commands (`kubectl`, `terraform`, `ansible`, etc.) are out of scope; the agent stops at "tag pushed" and reports.
- Skip CI. If CI reports red, the agent stops and asks: never with `--admin` or `--no-verify`.
- Run database migrations independently of the deploy. Migrations are part of the deploy and follow the team's migration runbook.
