---
id: style-guide
size: medium
tldr: Universal naming, file organisation, comments; no suppression without justification; language-specific in languages/.
load_when: naming, file structure, comments, suppression, lint, format, dead code, refactor commit
audience: all
canonical_for: naming conventions, no-suppression rule, refactoring commit discipline, comment policy
cross_refs: refactoring.md, languages/python.md, doc-linting.md
verified: 2026-07-17
---

# Code Style Guide

Language-specific conventions: `languages/`.

## Agent Use

- **Read first:** Naming, File and Module Organisation, Dead Code, Comments, No Suppression Without Justification.
- **Load deeper only on trigger:** language-specific style lives in `knowledge-base/languages/<lang>.md`.

---

## Naming

| Construct | Convention | Example |
|-----------|-----------|---------|
| Functions/methods | Verbs | `calculateTotal()`, `validateInput()` |
| Classes/types | Nouns | `UserAccount`, `OrderProcessor` |
| Booleans | Questions | `isValid`, `hasPermission`, `canEdit` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |

**Agent enforcement during review:**

- Flag version suffixes (`v1`, `v2`, `new`, `old`): delete the old version instead
- Flag generic suffixes (`Manager`, `Handler`, `Helper`, `Util`): name the behaviour

---

## File and Module Organisation

| Rule | Agent action |
|------|-------------|
| One primary concept per file | `order.py` contains `Order` + closely-related types, not unrelated utilities |
| Public interface at the top | Public functions/classes first, private/internal implementation below |
| Files under ~300 lines | Longer → extract. The file is doing too much. |
| Group by feature/domain, not by type | `src/checkout/` beats `src/models/` + `src/services/` + `src/repos/` |
| No barrel files *(JS/TS only)* | Avoid `index.ts` re-exporting everything: implicit coupling, hidden dependency direction. Exception: explicit public package boundary. Override in the project's JS/TS language file if your framework requires it (Next.js, NestJS). |

---

## Dead Code

| Rule | Agent action |
|------|-------------|
| Delete unused code immediately | Never comment out, never `# TODO: remove`. Version control is the history. |
| Uncertain if anything calls the code | Search with grep. Still uncertain → delete and let CI confirm. |
| Deprecated public library API | Mark with deprecation notice. Remove in next major version. |

---

## Comments

Comments explain *why*, not *what*. Don't explain obvious code, don't apologise for quality.

Docstrings/JSDoc format: see `languages/`.

### Ticket Context Belongs in Commits, Not Code

Core rule (always in context): `CLAUDE.md` § Code Quality. The full surface list it covers: production code, tests, comments, docstrings, TODOs, public strings, generated contract names, migration names, telemetry/event names. Operational metadata decays; code explains *why* a technical choice exists, tickets explain *why* the feature was built. Allowed places: workflow artifacts, commit messages, PR/MR descriptions, release notes, and test fixtures explicitly exercising artifact handling.

**Anti-patterns (flag in review):**

- `# See STORY-123, AC #2`, `TODO: implement per TICKET-ID`, `# ISSUE-99: workaround for X`: move to the commit body or a tracked task
- `test_story_001_ac5_rejects_empty_name`: name the behaviour, not the temporary story/AC number
- `raise ValueError("STORY-001 AC5 failed")` / `order_export_plan_001_event`: runtime strings and generated names must describe the user-visible error or domain contract, never a workflow artifact

### TODO Annotations

| Annotation | Priority | Meaning |
|-----------|----------|---------|
| `TODO(0)` | Critical | Must fix before merge: never ship this |
| `TODO(1)` | High | Architectural issue: fix this sprint |
| `TODO(2)` | Medium | Minor bug or improvement: schedule it |
| `TODO(3)` | Low | Polish, docs, nice-to-have |
| `PERF` |: | Performance opportunity: profile before optimising |

Format: `TODO(N): description: TICKET-ID if tracked`. No priority = TODO(3). Ticket reference is optional; use only if the TODO *cannot be resolved without tracking*. Prefer describing the issue itself (`TODO(1): handle timeout on payment retry`) over ticket coupling (`TODO(1): TICKET-567`). When ticket reference is needed, include a line explaining why (e.g., `TODO(0): blocked on external API stable. See TICKET-567 for schedule`).

---

## Refactoring Commit Discipline

Full guide: `refactoring.md`.

**Structural and behavioural changes go in separate commits.** Tidying (rename, extract, simplify) is structural. Adding or modifying features is behavioural. Never mix: reviewers can't distinguish behaviour changes from reorganisation.

**Over-engineering signals: flag in review:**

| Signal | Agent action |
|--------|-------------|
| Abstract base with one implementation | Inline it: extract only at Rule of Three |
| Config flag never false in prod | Remove the flag: it's dead code |
| Premature optimisation | Profile first (`performance.md` § Profile First Rule) |
| Framework used in one place | Replace with direct code |

---

## Formatting and Linting

When to run: `CLAUDE.md` § Code Quality. Per-language commands and detection rules: `quality-gates.md` § Per-Language Formatter & Lint Defaults. If the project has a local config file, use it; CI enforces the same rules. Language-specific details: `languages/`.

### No Suppression Without Justification

When a lint, type-check, or test failure blocks progress, **fix the code**: do not silence the tool.

**Banned without explicit code-review approval and an inline comment explaining why:**

| Suppression | What it hides |
|-------------|---------------|
| `# noqa` (blanket) | Any lint violation: use `# noqa: RULE` with reason if truly needed |
| `# type: ignore` | Type errors: add the correct type or narrow the union |
| `pytest.skip()` without reason | Untested code: use `pytest.xfail` with a ticket reference |
| `--no-verify` | Pre-commit failures: fix the hook, don't bypass it |
| `@pytest.mark.skip` without reason | Same as `pytest.skip()` |
| `# pragma: no cover` | Untested branches: delete the dead branch or add the test |
| `cast()` to silence a type error | Wrong type, not wrong checker: fix the type |

**Agent enforcement:**

- **xp-pair-programmer:** if you add any suppression pragma, you must include a comment with the reason AND log it in the plan's `## Discovered` section. Blanket `# noqa` (without a rule code) is never acceptable.
- **diff-reviewer / code-inspector:** every suppression pragma in the diff is a **Must Fix** unless the inline comment explains why the fix is impossible (not just inconvenient). "I don't know how to fix this" is not a justification: ask for help instead.
