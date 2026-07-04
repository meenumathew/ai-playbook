# How to scale agent-first automation

Goal: encode quality feedback once so agents self-correct continuously, instead of relying on humans to repeat the same review comments. Operating-model guidance for teams with high agent throughput.

## Prerequisites

- The playbook is deployed and the team runs agents regularly.
- Custom lint or CI rules exist (or are planned) for project conventions.

## The three patterns

| Pattern | What it does | When to apply |
|---------|--------------|---------------|
| **Teaching lint messages** | Every custom lint/architecture rule names the violation and the fix (cite the KB section). Agents read the message and self-correct. | Any custom linter or CI check an agent might trigger |
| **Doc gardening** | Scheduled scan of docs/KB for dead references, stale cross-links, outdated examples; opens a fix-up PR per finding | Weekly for active repos, monthly for stable ones |
| **Quality sweeps (GC)** | Background agent scans for pattern violations (duplicate utils, raw exception logging, dead code, `Any` types) and opens small targeted refactors; auto-merge on green | When manual cleanup no longer scales |

**Lint message example:** instead of `"Import not allowed here"`, write `"Import from 'infrastructure' in 'domain' violates dependency direction: see design-patterns.md § Architecture Layers."` The 30 seconds spent writes the fix for every future occurrence.

## Scaling by team size

| Team size | Automation level |
|-----------|------------------|
| Solo | Manual: run `code-inspector` when drift feels real |
| 2–4 | Monthly doc gardening + improve lint messages as you hit them |
| 5+ / high throughput | All three patterns automated on a schedule |

The patterns compound: teaching lint messages → fewer bad PRs → less GC needed → less doc drift.
