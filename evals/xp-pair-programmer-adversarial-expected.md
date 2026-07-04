# Eval Expected: XP Pair Programmer — Adversarial

The xp-pair-programmer should detect and flag problems in a malformed plan rather than blindly executing it.

## Must demonstrate

1. **Dependency cycle detected:** Task 2 depends on Task 3, Task 3 depends on Task 1, but Task 2 should logically depend on Task 3 (not vice versa) — flags that the dependency order means Task 2 cannot start until Task 3 is done, and the execution order should be Task 1 → Task 3 → Task 2
2. **Ambiguous AC flagged:** Flags that "discounts work correctly" is not testable — asks for specific `Given/When/Then` criteria or proposes concrete test cases per `testing.md`
3. **Vague test names rejected:** Does not accept `test_discount_works` — proposes specific names like `test_discount_applies_10_percent_when_order_exceeds_threshold` per `testing.md` § Test Quality Rules
4. **Still follows TDD:** Despite the malformed plan, writes tests before code for each step
5. **Goes back to slice-planner:** If the plan is too malformed to execute, recommends going back to `slice-planner` per `knowledge-base/CHEATSHEET.md` § When to Go Back

## Must NOT do

- Execute Task 2 before Task 3 (violates dependency order)
- Write code without a failing test
- Accept "discounts work correctly" as a testable acceptance criterion
- Silently reorder tasks without explaining why
- Invent AC that the user didn't provide (should ask, not assume)

## Quality signals

- References `testing.md` § Test Quality Rules when rejecting vague test names
- References `knowledge-base/CHEATSHEET.md` § When to Go Back when recommending backtrack to slice-planner
- Proposes concrete test names that follow `test_<what>_<condition>` convention
