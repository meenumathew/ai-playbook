# Eval Expected: Diff Reviewer

The diff-reviewer should produce the following observable behaviors when given `diff-reviewer-input.md` (the repo-grounded STORY-002 harness-Makefile review scenario).

## Must demonstrate

1. **Explicit review scope:** names the in-scope hunks and explicitly excludes the unrelated uncommitted hunks sharing the same files
2. **Verification run in this session:** re-runs the story's tests itself and reports the observed result; does not take the implementer's word
3. **Behavioural regression found by probing, not just reading:** reproduces the partial-override clobbering empirically (sandbox probe comparing old and new Makefile behaviour) and files it as Must Fix with the story constraint it violates
4. **Second behaviour change flagged with a concrete direction:** the environment-variable origin issue, anchored to the story constraint, with a specific mechanism proposed and test hardening for hermeticity
5. **AC coverage table:** every AC mapped to its covering test with a status column, including honest partial status where a constraint case is uncovered
6. **Findings anchored to KB files:** Must Fix / Should Fix / Suggestions each cite a specific knowledge-base file or CLAUDE.md section; domain correctness = Must Fix
7. **Cognitive debt check before the verdict:** targeted question on the key design decision, developer's answer recorded, assessment of what the mental model covers and misses
8. **Explicit verdict release-captain can gate on:** a ## Verdict section stating Approve or Request changes tied to evidence
9. **Acknowledges what is good:** names the correct root-cause mechanism and genuine test-quality strengths
10. **Read-only role respected:** no files modified, nothing committed; hands off fixes to xp-pair-programmer

## Must NOT do

- Rewrite the code in the review — suggest, reference KB, let the developer fix it
- Invent findings not grounded in KB files
- Rubber-stamp: approve without verifying tests or probing the behaviour change
- Skip the cognitive debt check
- Trust the implementer's pass claims instead of re-running verification

## Quality signals

- Probes compare HEAD behaviour against the new behaviour, isolating the regression to the change under review
- Commit hygiene flagged when story hunks are interleaved with unrelated work
- Suggestions distinguish acceptable-for-now from must-change, with the tightening condition stated
- The verdict separates AC compliance from constraint compliance
- Read budget self-tracked and reported
- Handoff names the exact follow-up invocation with the finding IDs
