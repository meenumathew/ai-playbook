---
provenance: curated
---

# Baseline Sample: xp-pair-programmer (adversarial input)

This plan is not executable as written. Three problems surface before any code, and one of them blocks the outer loop entirely.

## Ambiguous AC flagged: the outer loop is blocked

The story's only acceptance criterion is "discounts work correctly". That is not testable: the outer AT loop needs observable behaviour to assert at a system boundary, and "works correctly" asserts nothing (`knowledge-base/testing.md` § Test Quality Rules). I will not improvise AC or record an assumption and proceed.

Send this back to story-refiner to add 3-5 Given/When/Then criteria, or answer these to unblock: what discount rates apply, triggered by what order conditions, and what happens at the boundaries (zero-value order, discount exceeding order total, stacked discounts)? Concrete criteria would look like: Given an order over the qualifying threshold, when the discount is applied, then the total is reduced by the configured percentage. Each one maps to a named test.

## Execution order derived, misleading listing flagged

The plan lists Task 2 before Task 3, but the dependency chain is acyclic and only one order is valid: Task 2 depends on Task 3, Task 3 depends on Task 1, so execution must run **Task 1 → Task 3 → Task 2**. I will not execute Task 2 before Task 3, and I am flagging the listed order rather than silently reordering: the plan's sequence is misleading and should be corrected at the source per `knowledge-base/CHEATSHEET.md` § When to Go Back (plan defect → slice-planner).

## Vague test names rejected

`test_discount_works`, `test_endpoint_returns_discount`, and `test_service_applies_discount` do not follow `test_<what>_<condition>` (`knowledge-base/testing.md` § Test Quality Rules): none states a condition, so a failure tells the reader nothing. Once real AC exist, the names fall out of them, for example `test_discount_applies_10_percent_when_order_exceeds_threshold`, `test_discount_endpoint_returns_zero_for_order_below_threshold`, `test_discount_never_exceeds_order_total`.

## Goes back to slice-planner

Two of the three defects (untestable AC, misleading task order) are plan-level, so the route is:

1. story-refiner adds testable Given/When/Then AC (the AC gap is a story defect, not a plan defect).
2. slice-planner regenerates the plan with corrected dependency ordering and test names derived from the real AC.

Per `knowledge-base/CHEATSHEET.md` § When to Go Back, I stop here rather than build on a defective plan.

## TDD discipline preserved throughout

Nothing above changes the cycle: when the corrected plan arrives, every step is still test-first: one failing test per behaviour (RED with the failure shown), simplest code to pass (GREEN), refactor only on green, lint after GREEN and REFACTOR, one commit per task in dependency order. No production code was written in this session, and none will be until a failing test exists for it.

Say 'use story-refiner for the discount story' to fix the AC, then 'use slice-planner' to regenerate the plan.
