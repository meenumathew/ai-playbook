# ADR-0001: Bitbucket Server / Data Center is not supported

| Field | Value |
|-------|-------|
| **Status** | Active |
| **Date** | 2026-05-20 |
| **Supersedes** | N/A |

## Context

The host-adapter skill exposes vendor-neutral operation IDs (`host.pr.*`) backed by interchangeable CLIs: `gh` (GitHub), `glab` (GitLab), `tea` (Gitea), and Bitbucket REST. Bitbucket ships in two forms with different APIs and auth models: Bitbucket Cloud (SaaS) and Bitbucket Server / Data Center (self-hosted, on-prem). Supporting both multiplies the adapter surface and the test matrix.

## Decision

Support **Bitbucket Cloud only**. Bitbucket Server / Data Center is intentionally out of scope for the host-adapter, release-captain, and diff-reviewer host modes. On-prem Bitbucket teams use the Staged or Uncommitted review modes; PR/MR operations remain manual.

## Business Reason

The maintainer-funded test matrix cannot cover a second, diverging Bitbucket API surface without eroding the reliability of the SaaS backends the majority of adopters actually use.

---

*Reversing this boundary should supersede ADR-0001 with a new ADR. Referenced from [`README.md`](../../README.md), [`docs/limitations.md`](../limitations.md), [`docs/how-to/setup-issue-tracker.md`](../how-to/setup-issue-tracker.md), and [`skills/host-adapter/SKILL.md`](../../skills/host-adapter/SKILL.md).*
