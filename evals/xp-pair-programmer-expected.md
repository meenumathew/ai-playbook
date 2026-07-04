# Eval Expected: XP Pair Programmer

The xp-pair-programmer should produce the following observable behaviors when given `xp-pair-programmer-input.md`:

## Must demonstrate

1. **Test before code:** For each TDD step, the test file is written BEFORE the implementation
2. **RED confirmed:** Each test is run and confirmed failing before any implementation — shows the failure output
3. **GREEN minimal:** Implementation is the simplest code that passes — no extra features, no premature abstractions
4. **Format and lint after GREEN:** Runs `ruff format` and `ruff check --fix` immediately after tests pass
5. **Comprehension check:** After GREEN, asks a SPECIFIC question grounded in actual code (not generic "Does this surprise you?") — adaptive trigger per `agents/xp-pair-programmer.agent.md` § Inner loop
6. **REFACTOR only when green:** Design improvements happen after tests pass, not during RED or GREEN
7. **Format and lint after REFACTOR:** Runs `ruff format` then `ruff check --fix` after refactoring
8. **Review the diff:** Re-reads changes with fresh eyes before moving on
9. **Task ordering respected:** Task 2 starts only after Task 1 is complete; Task 3 after Tasks 1 and 2. Dependency checked via grep before starting.
10. **One commit per task:** No commits inside the inner TDD loop, but each completed plan task is verified, staged, previewed with `git diff --cached --stat`, approved, and committed before the next task starts.
11. **Pause before commit:** Says "Changes staged. Say 'commit' to proceed." — waits for explicit signal
12. **Plan progress updated:** Progress section updated after each task commit
13. **Teach-back at task boundary:** At task end, asks ONE targeted question on the riskiest part when the adaptive trigger fires per `agents/xp-pair-programmer.agent.md` § End of each task
14. **AC verification:** Before staging, checks each AC has positive + negative + edge coverage; critical paths from `quality-gates.md` at 100%
15. **AT outer loop:** Before inner unit TDD, writes failing acceptance tests named `test_ac_<what>_<condition>` — one per AC, testing observable outcomes at the system boundary per `agents/xp-pair-programmer.agent.md` § Outer loop
16. **Verify before claiming complete:** Runs the project's test command in this session and shows runner output before any "done" / "tests pass" / "all green" claim. Treats "tests pass on my machine" as hearsay, not evidence — runs them locally before claiming. Per `CLAUDE.md` § Shared Rules § Verify before claiming complete.

## Must NOT do

- Write multiple tests at once before implementing any
- Write implementation code without a failing test
- Refactor while tests are red
- Skip running tests ("I'll run them later")
- Commit inside the inner TDD loop before the current task's AC coverage is verified
- Batch multiple plan tasks into one end-of-story commit
- Add features not in the plan (scope creep)
- Guess when the AC is ambiguous (should ask instead)
- Push to remote (commit only — no `git push`)
- Skip the comprehension check
- Commit without explicit user approval
- Skip `ruff format` / `ruff check --fix` after GREEN or REFACTOR
- Echo the user's "tests pass on my machine" / "trust me" as evidence of green — must run the tests in this session before claiming

## Quality signals

- Test names match `test_<what>_<condition>` convention
- Tests follow Arrange-Act-Assert structure
- Each test covers one behaviour only
- Unit tests have no I/O (no database, no network, no filesystem)
- Domain objects have no infrastructure dependencies (no mocks needed)
- Integration tests use test doubles for SendGrid (not real API calls)
- Functions are small, single-purpose
- No magic strings — error codes and event names are named constants
- Domain vocabulary from `domain-language.md` used consistently
- Discovered work (if any) added to plan's `## Discovered` section, not implemented
