# Eval Input: XP Pair Programmer

## Grounding

This scenario targets the ai-playbook repository itself: the bug is real (found by the repo's own code-inspector audit and reproduced live), the files are shipped harness sources, and the tests land in the repo's own acceptance suite — the precondition for a `provenance: captured` baseline (see `evals/samples/README.md` § Refreshing a sample, capture prerequisite).

## Story

**Type:** bug (regression-test-first: slice 1 is the failing regression test encoding the reproduction; the fix turns it green)

**The bug (verified live):** `harness/Makefile` tells adopters on unrecognised stacks to "set STACK and *_CMD vars in Makefile.local", but the unknown-stack `$(error)` fires at parse time before `-include Makefile.local` is reached, so the documented rescue path can never work. Reproduced: a `Makefile.local` defining `STACK` and all five `*_CMD` vars still exits 2. A related audit finding: the `# shellcheck disable=SC2086` in `harness/telemetry.sh` carries no inline justification, violating the no-suppression-without-justification rule.

### Acceptance Criteria

1. Given an unrecognised stack and a `Makefile.local` defining `STACK` and command vars, when a quality target runs, then the overrides are used and no unknown-stack error fires
   - Test: `test_makefile_local_rescues_unknown_stack`
2. Given a recognised stack sentinel (for example `pyproject.toml`), when a quality target runs, then stack detection still selects it and behaves as before
   - Test: `test_stack_detection_still_selects_known_stack`
3. Given the harness shell scripts, when suppression pragmas are scanned, then every `shellcheck disable` carries an inline justification comment
   - Test: `test_shellcheck_disables_carry_justification`

### Constraints

- No behaviour change for recognised stacks; unknown stack with no override must still fail with the guidance message
- Tests follow the repo's acceptance-suite conventions (`tests/acceptance/`, `repo_contract` marker, sandboxed `make` runs)
- One commit per task, approval-gated; no pushes
