<!--
Two uses for this template:

1. SHAPE OF EVERY REVIEW (always): diff-reviewer uses these section headings
   when delivering a review in chat, on a PR/MR, or to a file. Same structure
   so adopters can scan reviews consistently.

2. SAVED FILE (opt-in only): diff-reviewer does NOT save a review file by
   default. On a host PR/MR, the host comment thread is the canonical record.
   Save only when the user asks ("save the review", "write a review file") or
   when `.ai-playbook.toml [review].save_local = true` is set (compliance /
   audit-trail mode).

For audits across whole modules / repos, code-inspector saves to
`audits/AUDIT-NNN-*.md`: that is a separate flow with its own justification.
-->

# Code Review: STORY-NNN [Title]

**Reviewer:** [name or agent]
**Type:** diff-review | code-audit
**Date:** YYYY-MM-DD
**Story:** stories/STORY-NNN-slug.md | PROJ-NNNN

## Verdict

- [ ] Approved
- [ ] Approved with suggestions
- [ ] Request changes

---

## Acceptance Criteria Coverage

| Criterion | Covered | Test |
|-----------|---------|------|
| [criterion from story] | yes/no | `test_name` |

---

## Must Fix
<!-- Blocks approval: violates KB standards or acceptance criteria -->

**[Issue title]**

- File: `path/to/file.py` line NNN
- Rule: `knowledge-base/[file].md`
- Problem: [what is wrong]
- Suggestion: [what to do instead]

---

## Should Fix
<!-- Does not block but should be addressed -->

---

## Suggestions
<!-- Optional improvements -->

---

## Definition of Done

> Canonical source: `CLAUDE.md` § Definition of Done. Do not copy the checklist here; record review status and exceptions only.

- [ ] DoD met: yes / no
- [ ] Exceptions: none / [link to approved exception]
- [ ] Reviewer notes: [missing evidence, risks, or confirmation]

---

## Summary

[2-3 sentences: overall quality, key strengths, most important things to address]
