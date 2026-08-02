# AUDIT-NNN: [Scope]

**Auditor:** [name or code-inspector]
**Date:** YYYY-MM-DD
**Scope:** [repository, module, or directory]
**Read budget:** [used / maximum]

## Summary

[Overall health, highest-risk finding, and whether the scope is release-ready.]

## Findings by Priority

### Must Fix

| ID | Finding | Evidence and impact | KB rule |
|----|---------|---------------------|---------|
| M1 | [title] | `[path:line]`: [observable risk] | `knowledge-base/[file].md` |

### Should Fix

| ID | Finding | Recommendation |
|----|---------|----------------|
| S1 | [title] | [bounded corrective action] |

### Suggestions

| ID | Opportunity | Benefit |
|----|-------------|---------|
| O1 | [optional improvement] | [expected benefit] |

## Cross-File Issues

[Architecture drift, duplicated contracts, terminology conflicts, dead code,
or “None found.”]

## Health Score

| Area | Result |
|------|--------|
| Security | Pass / Warn / Fail |
| Domain and architecture | Pass / Warn / Fail |
| Tests and evaluation | Pass / Warn / Fail |
| Documentation and contracts | Pass / Warn / Fail |
| Release readiness | Pass / Warn / Fail |

## Recommended Actions

1. [Highest-priority bounded action]
2. [Next action]
3. [Optional follow-up]

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Do not copy the
> checklist here; record audit evidence and approved exceptions only.

- [ ] Audit scope completed
- [ ] Every Must Fix cites evidence and a canonical KB rule
- [ ] Exceptions: none / [approved exception]
