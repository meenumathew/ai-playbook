# Eval Expected: Story Refiner

The story-refiner should produce the following observable behaviors when given `story-refiner-input.md` (a request to push session telemetry to a vendor dashboard, grounded on this repository).

## Must demonstrate

1. **Intent anchors captured:** Problem, desired outcome, why now, key constraint, and smallest useful change — all five present before any research, with inferred anchors stated as assumptions
2. **Objective research questions:** Questions framed as "what exists?" not "how to build?" (e.g., "What does the session-telemetry hook currently capture, and where does it write?" not "How should we push usage data to Datadog?")
3. **Codebase research with citations:** Every finding cites `file:line` — never claims something exists without proof (e.g. `harness/telemetry.sh:108-114` for the recorded field set, `docs/how-to/agent-telemetry.md` for the no-network contract, `CHANGELOG.md` for the privacy-minimal schema decision)
4. **Contradictions surfaced:** Flags that "token spend per agent" contradicts the privacy-minimal telemetry schema (token/cache counts are deliberately never persisted — an explicit documented exclusion, not a gap) and that "just push it there" contradicts the session-end hook's no-network, never-block contract — does not absorb either request silently
5. **Descope proposed, not assumed:** Recommends descoping the token-spend ask to a follow-up decision (reversing a documented privacy contract needs its own story and ADR), asks the developer, and records the answer — does not quietly drop or quietly include it
6. **Design questions with trade-offs:** Prioritizes unresolved questions, asks one question at a time with a recommended answer, and grounds each trade-off in codebase findings rather than generic options
7. **Story written using template:** Uses `templates/story-template.md` format with all sections populated
8. **Prefer 3–5 AC, never 8+:** Each AC follows `Given [precondition], when [action], then [expected outcome]` per `skills/story-writing/SKILL.md` § Acceptance Criteria; each AC has a matching `test_<what>_<condition>` name
9. **Domain language used:** Uses the repo's telemetry terms — `usage log`, `session-end hook`, `usage event` — and names the export target by capability (`metrics backend`), not vendor, in AC per `knowledge-base/design-patterns.md` § Vendor-Neutral by Design; the vendor appears only in Constraints
10. **Preview before save:** Shows the story and research and waits for explicit approval before writing files; research file written first

## Must NOT do

- Skip research and jump to writing the story
- Assume the usage log already contains every field the dashboard needs without checking
- Write implementation details (which exporter library, which API endpoint, which cron syntax)
- Write AC that can't be tested (vague outcomes like "usage is visible promptly")
- Produce 8+ acceptance criteria instead of splitting/trimming
- Pick the final design approach — present options, slice-planner owns the decision
- Dump multiple unrelated design questions at once
- Save files without showing a preview and getting approval

## Quality signals

- Research file saved to `research/` with findings, design options, ADR candidates, and scope exclusions
- Story file saved to `stories/` with intent anchors, AC, constraints, and sizing
- Handoff message mentions slice-planner as next step
- ADR candidate recorded for the network-free-recording boundary and handed to docs-maintainer (story-refiner never writes ADR files), noting the advisor-tier re-escalation
- Scope exclusions explicit ("What We're NOT Doing" — e.g., no token or cost capture, no schema expansion, no per-developer attribution, no dashboard-as-code)
- Read budget reported at end of research phase (e.g. `Reads used: 15 / 20`)
