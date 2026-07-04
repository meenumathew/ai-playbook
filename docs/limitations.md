# Known Limitations

System-wide limitations that affect what the playbook can and cannot support. Consult this registry before assuming a capability exists.

The registry mixes four categories: readers should treat them differently:

- **By design**: an intentional scope decision or safety boundary. Reversals need an explicit design decision; write an ADR only when the change meets the ADR criteria.
- **Inherent**: a property of the chosen architecture, for example copy-based deploy drift. Mitigated, not removed.
- **External**: bounded by third-party APIs, providers, or platforms outside project control.
- **Future work**: a real gap with a known shape; the team has sized the work but not scheduled it yet.

---

## When to Record

Add an entry when:

- A feature explicitly does not support something users might expect.
- A performance ceiling exists but nothing enforces it.
- An integration works only with specific providers or versions.
- A known gap requires a workaround.
- Implementation discovered a limitation.
- An intentional product boundary or safety choice exists that adopters might mistake for a missing capability.

After resolving a limitation, remove the entry and reference the commit that resolved it. Do **not** remove an entry just because the team is comfortable with the trade-off: adopters still need the contract documented.

---

## Limitation Registry

| Area | Category | Limitation | Impact | Workaround | Added |
|------|----------|-----------|--------|------------|-------|
| Governance | Future work | Single-maintainer project: no multi-maintainer voting model yet (transition criteria documented) | Routine decisions, RFC acceptance, and conflict resolution all rest with one person; adopters who disagree pin a version, open an RFC, or fork | Read [`GOVERNANCE.md`](../GOVERNANCE.md), [`docs/deprecation-policy.md`](deprecation-policy.md), and [`docs/rfcs/README.md`](rfcs/README.md); pin a major version; transition follows the criteria in `GOVERNANCE.md` § Transition | 2026-05-22 |
| Benchmarks | Future work | No published comparison against Cursor rules, Aider conventions, Cline, Continue, or other agent frameworks | Quality claims rest on this repo's tests and evals, not external baselines | Treat comparisons as local evaluation work: run the same task set through competing tools and record results in `research/` | 2026-05-22 |
| Security | Future work | No coverage-guided fuzzing yet: property-based fuzz targets exist (`tests/unit/test_fuzz_properties.py`, Hypothesis, deterministic in CI) for TOML config parsing and path safety, but there is no ClusterFuzzLite/OSS-Fuzz integration | Property tests catch contract violations on every push; coverage-guided fuzzing would explore deeper input space asynchronously | Extend the Hypothesis targets as new parsers appear; wire ClusterFuzzLite when the maintenance cost is justified | 2026-06-11 |
| Kiro | External | No slash command support: Kiro itself does not expose a slash-command surface | Cannot use `/agent-name` syntax in Kiro | Use natural language such as "Use story-refiner: <topic>" | 2026-05-12 |
| Languages | Future work | Python is the maintained reference implementation; other languages need team-owned conventions | Agents and the starter harness detect Go/Rust/Java/TypeScript project files, but deploy-time `--language` filtering only has maintained Python files today. `knowledge-base/languages/<lang>.md` starts from a blank template until a maintainer or adopter pack owns it. | Copy `templates/language-conventions-template.md` to `knowledge-base/languages/<lang>.md`; first-class support arrives via RFC + maintainer commitment | 2026-05-12 |
| Project-management tool / issue tracker | External | Work item fetch is best-effort across Jira / GitHub Issues/Projects / GitLab / Bitbucket SaaS / Linear and depends on third-party CLIs, APIs, and auth | External services bound true reliability; on failure the agent asks for a paste | Paste work item title, description, AC, and comments; provider diagnostics surface in agent output | 2026-05-12 |
| Host PR/MR | External | GitLab, Bitbucket, and Gitea lack per-line inline review via CLI: comments fall back to a single body comment | Bitbucket / GitLab / Gitea reviews are less granular than GitHub | Use `host.pr.review` body summary; cite line numbers in prose | 2026-05-20 |
| Host PR/MR | By design | Bitbucket Server / Data Center is not supported (SaaS only): see [ADR-0001](adr/0001-bitbucket-server-not-supported.md) | On-prem Bitbucket teams cannot use release-captain or diff-reviewer host mode | Use the Staged or Uncommitted review modes; PR/MR ops manual. Reversing this boundary should supersede ADR-0001. | 2026-05-20 |
| Release | By design | release-captain stops at "tag pushed": does not run deploy commands | Tag → deploy is the adopter's CI/CD responsibility, never the agent's. Avoids smuggling unaudited deploy capability into a release helper. | Configure CI/CD to deploy on tag push (`v*`) | 2026-05-20 |
| Release | By design | release-captain never auto-merges: every merge requires an explicit user signal | Cannot run unattended in production tier. Safety boundary: human approval is the merge contract. | Approve merges interactively. Auto-merge needs an explicit team decision, usually ADR-worthy because it changes the release safety contract. | 2026-05-20 |
| Incident response | By design | incident-responder only reads production: never executes mitigations | Cannot toggle flags, roll back deploys, or scale services. Safety boundary: agent investigates and documents; humans + release-captain execute. | Hand mitigation to humans; agent produces triage notes, ranked hypotheses, and the postmortem | 2026-05-20 |
| diff-reviewer | By design | Local review files are opt-in: host PR/MR thread or chat output is the canonical record | Default reviews avoid local file clutter; teams that need an audit-trail file must opt in | Set `[review].save_local = true` in `.ai-playbook.toml`, or ask explicitly ("save the review") | 2026-05-21 |
| Notifier | By design | Default provider is `none`: no notifications go out unless adopters opt in | No surprise outbound traffic. Teams that want Slack/email pings configure `.ai-playbook.toml [notifier]` and the matching env vars | Set `[notifier].provider = "slack"` and `SLACK_WEBHOOK_URL`; see `skills/notifier/SKILL.md` § Configuration | 2026-05-21 |
| Notifier | Future work | PagerDuty / Opsgenie / platform paging tools are not supported in v1 | Paging is a separate product surface from chat/email and ships behind a future RFC | Hand off SEV1 to your existing on-call system at the human layer; the notifier is for chat/email only | 2026-05-21 |
| Packs | Future work | Packs cannot ship *custom* `commands/` shim content: deploy auto-generates a standard slash-command shim for every pack agent, but the shim body is not customizable from a pack | Pack agents are slash-invocable like core agents; only bespoke shim prose (custom descriptions, extra prompt text) needs the core repo | Use the generated shim, or propose custom shim support via RFC | 2026-06-11 |
| Packs | Future work | No publishable packs, no pack dependency graph | Teams manage shared packs outside the CLI; package metadata, resolution rules, and version-conflict handling must exist before shipping | Vendor local pack directories, use a Git submodule, or package/sync packs with team-owned tooling | 2026-05-22 |
| Agent orchestration | By design | The CLI does not run automated multi-agent chains | Each agent is invoked deliberately so handoffs, cost, and approval gates stay visible to the human or hosting tool | Use the documented workflow paths to invoke one agent at a time; reversing this boundary needs an ADR because it changes safety and cost behavior | 2026-05-28 |
| Evals | Future work | Eval harness does not validate end-to-end artifact-handoff scenarios, multi-turn agent sessions, judge ensembles, or historical regression budgets | Single-run evals catch rubric drift and common behavior; longitudinal and multi-turn quality require a larger validation investment | Run representative manual workflow scenarios before major releases; record repeated failures as new eval samples. Artifact-handoff scenario validation is the smallest next slice. | 2026-05-22 |
| Evals | External | The opt-in LLM-as-judge drift job (`.github/workflows/eval-drift.yml`, manual `workflow_dispatch`) calls the Anthropic API exclusively and requires `ANTHROPIC_API_KEY`: agents themselves remain model-agnostic, but the judge is not | Forks without the secret cannot run the judge; teams that prefer a different judge model must edit `evals/run_eval.py` | Run the offline structural pass (`uv run python evals/run_eval.py check-structure`) which has no vendor dependency, or substitute a pinned judge implementation behind the same `judge` subcommand | 2026-05-29 |
| Telemetry | External | Session telemetry (`.claude/usage.jsonl`) is Claude-only: Copilot, Cursor, and Kiro do not expose an equivalent Stop hook | Cross-tool cost/token dashboards must merge external sources | Use `ai-playbook telemetry status` on Claude projects; load provider-native metrics out-of-band for Copilot, Cursor, and Kiro | 2026-05-22 |
| Deploy | Inherent | Copy-based deploy means deployed files drift from source whenever the playbook updates: there is no auto-pull | Inherent to the chosen deploy model: adopters can edit deployed files independently, which precludes silent updates. `ai-playbook doctor` (fingerprint warning) and `ai-playbook upgrade-check` (CI exit code) mitigate it. | Wire `ai-playbook upgrade-check --tool <tool>` into CI as a periodic job; non-zero exit means redeploy | 2026-05-22 |
| Deploy | Inherent | Deploy rewrites paths and rules-file references per tool (`CLAUDE.md` → `copilot-instructions.md` / `ai-playbook.mdc` / `rules.md`), but Claude-flavoured *terminology* survives in Copilot/Cursor/Kiro copies: for example "slash command" prose and the Stop-hook telemetry discussion in `observability.md` | A Copilot/Cursor/Kiro reader occasionally meets a concept their tool lacks; instructions stay followable because invoking agents by name always works | Read "slash command" as "invoke the agent by name"; ignore Stop-hook telemetry sections outside Claude. A full per-tool prose pass is RFC-scale work. | 2026-06-11 |
