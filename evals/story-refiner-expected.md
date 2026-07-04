# Eval Expected: Story Refiner

The story-refiner should produce the following observable behaviors when given `story-refiner-input.md` (a request to push session telemetry to a vendor dashboard, grounded on this repository).

## Must demonstrate

1. **Intent anchors captured:** Problem, desired outcome, why now, key constraint, and smallest useful change — all five present before any research
2. **Objective research questions:** Questions framed as "what exists?" not "how to build?" (e.g., "What does the session-telemetry hook currently capture, and where does it write?" not "How should we push usage data to Datadog?")
3. **Codebase research with citations:** Every finding cites `file:line` — never claims something exists without proof (e.g. `harness/telemetry.sh:28`, `knowledge-base/observability.md:190`, `harness/settings.example.json`)
4. **Contradictions surfaced:** Flags that telemetry capture is Claude Code-only (other tools' sessions never reach the usage log, so a "team dashboard" would undercount), and that the hook's never-block failure policy conflicts with pushing synchronously to a remote API — doesn't assume the local usage log already covers everyone
5. **Design questions with trade-offs:** Prioritizes unresolved questions, asks one question at a time, and grounds each trade-off in codebase findings rather than generic options
6. **Story written using template:** Uses `templates/story-template.md` format with all sections populated
7. **Prefer 3–5 AC, never 8+:** Each AC should follow `Given [precondition], when [action], then [expected outcome]` per `skills/story-writing/SKILL.md` § Acceptance Criteria
8. **TDD test names:** Each AC has a matching `test_<what>_<condition>` name
9. **Domain language used:** Uses the repo's existing telemetry terms — `usage log`, `Stop hook`, `session telemetry` (`knowledge-base/observability.md` § Agent Telemetry) — and names the export target by capability (`metrics backend`), not vendor, in AC per `knowledge-base/design-patterns.md` § Vendor-Neutral by Design
10. **Preview before save:** Shows the story and waits for explicit approval before writing files

## Must NOT do

- Skip research and jump to writing the story
- Assume the usage log already contains every field the dashboard needs without checking
- Write implementation details (which exporter library, which API endpoint, which cron syntax)
- Write AC that can't be tested (vague outcomes like "usage is visible promptly")
- Produce 8+ acceptance criteria instead of splitting/trimming
- Pick a design approach — present options, let the human decide
- Dump multiple unrelated design questions at once
- Save files without showing a preview and getting approval

## Quality signals

- Research file saved to `research/` with findings, design options, and scope exclusions
- Story file saved to `stories/` with intent anchors, AC, constraints, and sizing
- Handoff message mentions slice-planner as next step
- Security considerations raised — usage data leaving the machine to a third party reviewed against `security.md` § Data Handling (confirm no transcript content is exported)
- Scope exclusions explicit ("What We're NOT Doing" — e.g., not building the dashboards, not capturing non-Claude tools)
- Read budget reported at end of research phase (e.g. `Reads used: 6 / 20`)
