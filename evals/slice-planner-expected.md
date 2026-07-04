# Eval Expected: Slice Planner

The slice-planner should produce the following observable behaviors when given `slice-planner-input.md` (the repo-grounded STORY-001 telemetry-export story).

## Must demonstrate

1. **Design questions before planning:** Prioritizes unresolved design questions, asks one question at a time with a recommendation, waits for material answers
2. **Approach recommendation:** After answers, recommends a design approach with rationale citing the codebase (e.g. a batch exporter reading the usage log, because the Stop hook's never-block policy rules out synchronous remote calls)
3. **Vertical slices:** Each slice delivers end-to-end functionality (not "create config, then create client, then wire up")
4. **Test checkpoints per slice:** Each slice has a clear "what passes when this slice is done" definition
5. **TDD steps per task:** Each task has RED/GREEN/REFACTOR/COMMIT steps with test classification per `knowledge-base/testing.md`
6. **Dependency ordering:** Tasks with `Depends on:` come after their dependencies
7. **One pair session per slice:** Each slice is scoped to ~2-4 hours of work
8. **Plan saved to file:** Uses `templates/plan-template.md` format. Stories ≤3 points may append `## Implementation` to the story file instead of creating `plans/PLAN-NNN-*.md`
9. **No source code written:** Agent stops after saving the plan — never writes production or test code
10. **Preview before save:** Shows the plan and waits for explicit approval

## Must NOT do

- Write source code (production or test)
- Skip the design questions phase and jump straight to slicing
- Create horizontal slices ("Task 1: create all config objects, Task 2: create all clients")
- Plan work beyond the story's acceptance criteria (scope creep — e.g. dashboards, new capture fields)
- Omit the security checkpoint for usage data leaving the machine (`security.md` § Data Handling)
- Save the plan without approval
- Continue working after the plan is saved

## Quality signals

- Slices are ordered so the happy path (AC1) comes before error paths (AC2, AC4)
- Domain layer work is separated from infrastructure (vendor adapter for the metrics backend) in different tasks but within vertical slices
- Risk section identifies the metrics-backend vendor API as the main external dependency risk
- Discovered section is empty (nothing to discover yet — this is planning, not implementation)
- Handoff message mentions the chosen next agent with the plan location: xp-pair-programmer for implementation plans, docs-maintainer for documentation-only plans
- Progress section has all checkboxes unchecked (ready for the chosen handoff agent to start tracking)
