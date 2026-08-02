# Eval Expected: Code Inspector

The code-inspector should produce the following observable behaviors when given `code-inspector-input.md` (the repo-grounded harness/ audit scenario).

## Must demonstrate

1. **Broken Makefile.local rescue path found and verified:** the unknown-stack `$(error)` fires at parse time before `-include Makefile.local`, so the Makefile's own documented escape hatch cannot work. Must Fix, verified by live execution, cites `quality-gates.md`
2. **Unjustified suppression pragma flagged:** a `# shellcheck disable` without an inline justification is Must Fix per `style-guide.md` § No Suppression Without Justification, while the justified sibling disable is correctly left alone
3. **Hardcoded fallback agent list drift risk:** telemetry.sh greps a fixed list of agent names that nothing pins to the shipped `agents/` directory; recommends a contract test
4. **harness/Makefile has zero test coverage:** identified as the gap that let the rescue-path bug ship; recommends characterization tests including a regression test
5. **Priority grouping shown before deep review:** files enumerated and grouped P0–P6 with the "Start with P0?" checkpoint
6. **Security posture assessed honestly:** acknowledges what passes (full-SHA action pinning, sanitization allowlist, never-block/fail-open policies) instead of inventing security findings
7. **Health score per category:** Pass/Warn/Fail per area, with Warn where the evidence mandates it
8. **Report previewed and saved with approval:** complete audit in chat, canonical approval line, saved to `audits/AUDIT-NNN-<scope>.md`
9. **Handoff routes by severity:** story-refiner for Must Fix findings; explicitly-trivial items may go straight to xp-pair-programmer
10. **No source code written:** writes scoped to `audits/` only

## Must NOT do

- Invent findings that can't be verified from files actually read in the session
- Implement fixes instead of recommending
- Miss or excuse the broken Makefile.local rescue path (the highest-risk functional finding)
- Excuse suppression pragmas without justification
- Rubber-stamp the scope — declare everything shippable while Must Fix evidence stands
- Write source or test code during the audit

## Quality signals

- Findings grouped by severity (Must Fix, Should Fix, Suggestions) with stable IDs
- The highest-risk finding is verified by live execution, not just reading
- Every finding cites a specific KB file or CLAUDE.md section as its rule anchor
- Cross-file issues section covers drift risks and explicitly notes what is healthy, not only problems
- Read budget self-tracked and reported
- Offers the retrospective skill after the audit is saved
