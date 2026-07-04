---
id: feature-flags
size: small
tldr: Default-OFF flags with owner and cleanup date in the registry; eval in service layer; test both states.
load_when: dark launch, gradual rollout, kill switch, A/B test, percentage rollout, flag cleanup, flag registry
audience: story-refiner, slice-planner, xp-pair-programmer, diff-reviewer
canonical_for: flag lifecycle, flag evaluation layer, flag test isolation, flag registry process
cross_refs: security.md, testing.md
verified: 2026-07-17
---

# Feature Flags

## Agent Use

- **Read first:** When to Use, Business Behaviour, Flag Registry, Acceptance Criteria Pattern, Evaluation Layer, Test Isolation.
- **Load deeper only on trigger:** naming conventions and lifecycle cleanup details.

---

## When to Use

**Use when:** dark-launch, gradual rollout, toggle without deployment, A/B test.

**Do NOT use for:** bug fixes, internal refactors with no user-visible change, features already behind auth/permissions.

---

## Flag Categories

Classify every flag at creation (Hodgson taxonomy, martinfowler.com/articles/feature-toggles): longevity and cleanup follow the category:

| Category | Purpose | Expected lifetime | Cleanup |
|----------|---------|-------------------|---------|
| **Release** | Dark launch, gradual rollout, decouple deploy from release | Days–weeks | Remove once rollout hits 100%: this is the default category and the cleanup-date rule below applies strictly |
| **Experiment** | A/B test, canary comparison | Weeks: until results are statistically significant | Remove after the experiment concludes; keep the winning path |
| **Ops** | Kill switch, load shedding, circuit breaker | Long-lived by design | Review periodically; document in `docs/limitations.md` if permanent |
| **Permission** | Entitlement / plan gating per user or segment | Permanent | Not a temporary flag: model it as authorisation, not a toggle, when it stabilises |

Only **Ops** and **Permission** flags may outlive a release cycle. A "release" flag still alive after two cycles is cleanup debt: flag it in review.

---

## Business Behaviour

Every flag must define:

| Question | Agent enforcement |
|----------|------------------|
| **Default state** | Always OFF on first deploy |
| **Who sees it?** | All users / segment / internal only |
| **Rollout plan** | Full / percentage / phased |
| **Kill switch?** | Must be yes: ops can turn off instantly |
| **Owner** | Named person or team in the registry: owns rollout and cleanup |
| **Cleanup date** | Required for release and experiment flags (they are short-lived by definition); ops and permission flags are legitimately long-lived and instead record an owner + annual review date in the registry. Cleanup is part of the DoD. |

---

## Flag Lifecycle

```text
Create (off) → Dark launch → Enable for QA → Gradual rollout (10→50→100%) → Full launch → Remove flag (cleanup)
```

---

## Flag Registry

Project flags live in `knowledge-base/feature-flag-registry.md`: seed from `templates/feature-flag-registry-template.md` on first use and announce the seed (`CLAUDE.md` § Shared Rules, Progressive KB files). This file owns the rules; the registry owns the state.

| When | Registry action |
|------|----------------|
| Flag created | Add row: name, category, default OFF, owner, story, created date, cleanup-due date. Same commit as the flag's first test; required by `CLAUDE.md` § Definition of Done |
| Rollout advances | Update Status (dark-launch → 10% → 50% → 100%) |
| Flag removed | Move the row to Removed Flags with date and outcome |
| Review / audit | Past-due cleanup date, or a flag past its § Flag Categories lifetime, = cleanup debt → diff-reviewer / code-inspector finding |

A flag in a diff with no registry row is a **Must Fix** review finding.

---

## Acceptance Criteria Pattern

Write AC as business behaviour, never tool commands:

```text
- [ ] Feature not visible when flag disabled
- [ ] Feature visible and functional when flag enabled
- [ ] Disabling mid-session → graceful fallback, no error
- [ ] Flag default state is OFF on first deploy
```

TDD test names:

```text
test_feature_hidden_when_flag_disabled
test_feature_visible_when_flag_enabled
test_graceful_fallback_when_flag_toggled_mid_session
```

---

## Evaluation Layer

In a layered codebase, flag evaluation belongs in the **service layer**. Infrastructure wraps the SDK, service calls it. Domain objects receive pre-evaluated booleans or strategy objects: they never call the flag service. Unlayered code keeps the same spirit: evaluate once at the entry point, pass the result down. See `design-patterns.md` § Architecture Layers.

---

## Test Isolation

| Rule | Agent action |
|------|-------------|
| Never use real flag SDK in unit tests | Pass the boolean or strategy object directly |
| Never hardcode flag keys as string literals | Read from a shared constant |
| Cover both states | Flag-on and flag-off as independent tests |
| Mock at service boundary | Flag evaluation is infrastructure: stub/mock there, not inside domain tests |

---

## Naming

Format: `kebab-case`. Short, meaningful, tied to the feature: not the team or sprint.

| Avoid | Use instead | Agent enforcement |
|-------|-------------|------------------|
| `enable_new_feature` | `new-checkout-flow` | Name the capability, not the action |
| `team_alpha_experiment` | `ml-recommendations` | Feature name, not team name |
| `temp_fix_for_bug_123` | (no flag) | Flags are for features, not bug fixes |
| `flag_on` / `flag_off` | (any meaningful name) | Must be readable in logs and dashboards |
