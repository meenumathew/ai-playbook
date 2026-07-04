# Eval Input: XP Pair Programmer — Adversarial

## Plan (malformed — missing dependencies, ambiguous AC)

**Story:** Add discount calculation to orders

### Task 1: Add discount logic
> Implement discounts

**Layer:** Domain
**Depends on:** Nothing

TDD Steps:
- [Unit] test_discount_works → implement → refactor → commit

### Task 2: Add discount API endpoint
> Wire it up

**Layer:** Infrastructure
**Depends on:** Task 3

TDD Steps:
- [Integration] test_endpoint_returns_discount → implement → refactor → commit

### Task 3: Add discount service
> Service layer

**Layer:** Service
**Depends on:** Task 1

TDD Steps:
- [Unit] test_service_applies_discount → implement → refactor → commit

Note: The AC says "discounts work correctly" — no specific Given/When/Then criteria.
