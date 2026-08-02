# Eval Expected: Slice Planner

The slice-planner should produce the following observable behaviors when given `slice-planner-input.md` (the repo-grounded STORY-001 usage-export story with its research file).

## Must demonstrate

1. **Artifact chain loaded:** Reports loading the story and its research file; skips redundant codebase exploration because research exists, but spot-checks the load-bearing citations against the live repo
2. **Design questions before planning:** Resolves the one material design choice the research left open (shipping mechanism) with a recommendation grounded in codebase facts, and waits for the answer before structuring
3. **Approach recommendation:** After the answer, recommends the design in one paragraph citing existing patterns (opt-in adapter precedent, ADR-0002 layering) and naming the main trade-off in business terms (dashboard freshness vs a private, offline-safe session end)
4. **Vertical slices:** Each slice delivers end-to-end functionality (not "create config, then create client, then wire up"); safety guarantee (nothing transmitted when unconfigured) front-loaded
5. **Test checkpoints per slice:** Each slice has a clear "what passes when this slice is done" definition using the story's AC test names
6. **TDD steps per task:** RED/GREEN/REFACTOR/COMMIT steps with test classification (Unit | AT | Integration) and a pyramid balance statement
7. **Dependency ordering:** Slices with `Depends on:` come after their dependencies
8. **One pair session per slice:** Each slice scoped to ~2-4 hours
9. **Security checkpoint:** STRIDE-lite for usage data leaving the machine — credential handling, TLS, pinned exported field set, no retry storms
10. **Plan saved to file:** Story is 5 points (>3), so the plan goes to `plans/PLAN-001-*.md` via `templates/plan-template.md`, previewed and saved only after approval
11. **No source code written:** Stops after saving the plan
12. **Preview before save:** Shows the complete plan and waits for explicit approval

## Must NOT do

- Write source code (production or test)
- Skip the design questions phase and jump straight to slicing
- Create horizontal slices ("Task 1: create all domain objects, Task 2: create all services")
- Plan work beyond the story's acceptance criteria (scope creep — e.g. dashboards-as-code, token capture, doctor checks)
- Omit the security checkpoint for usage data leaving the machine
- Name the vendor above the adapter boundary (port, config keys, CLI text stay capability-named)
- Save the plan without approval
- Continue working after the plan is saved

## Quality signals

- Slices are ordered so the safety path (AC3) and happy path (AC1) come before error paths (AC2, AC4)
- Dedup mechanism reasoned from the rotation behaviour (content-hash ledger because rotation renames and gzips files), recorded as a reversible assumption
- Risk section identifies dedup-across-rotation as the hardest part with a stop-per-debugging-discipline note
- The follow-up ADR (network-free recording, opt-in export) routes to docs-maintainer, not planned as a task
- Discovered section is empty (nothing to discover yet — this is planning, not implementation)
- Handoff message mentions xp-pair-programmer as next step with the plan file path
- Progress section has all checkboxes unchecked
- Read budget self-tracked and reported (e.g. `Read budget: 15/15`)
