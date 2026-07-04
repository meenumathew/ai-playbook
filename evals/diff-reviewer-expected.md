# Eval Expected: Diff Reviewer

The diff-reviewer should produce the following findings when given `diff-reviewer-input.md`:

## Must Fix (KB violations)

1. **`logger.error(str(e))` in notification_service.py** — Violates `CLAUDE.md` § Security and `security.md` § Data Handling. Must use `exc_info=True`, not `str(e)`. This leaks stack context and loses the traceback.

2. **Test uses try/except instead of `pytest.raises`** — Violates `testing.md` § Test Quality Rules (rule 4: Arrange-Act-Assert). The test in `test_notifications.py` uses a manual try/except pattern instead of `pytest.raises(ValueError)`. No logic in tests.

3. **Missing AC coverage** — AC2 (`test_order_shipped_skips_notification_when_no_email`) and AC3 (`test_email_failure_is_logged_without_affecting_order`) have no tests in the diff. Every AC must have at least one test.

4. **Missing import in notification_service.py** — `EmailNotification` is used but not imported. Code won't run.

## Should Fix

1. **Magic strings** — `"Your order has shipped!"` and `"Order {order.id} is on its way."` are hardcoded. Extract to constants or a template. Falls under `CLAUDE.md` § Definition of Done ("Code refactored — no obvious smells").

2. **SendGridAdapter has no port/interface** — `email_adapter` parameter in `NotificationService` has no corresponding port defined in the domain layer. Per `CLAUDE.md` § Architecture and `design-patterns.md`, infrastructure implements ports defined by the domain.

3. **Bare `except Exception`** — `notification_service.py` catches all exceptions. Should catch the specific SendGrid exception to distinguish infra failures from bugs.

## Should Fix (continued)

4. **Observability** — `logger.error(str(e))` also violates `observability.md` § Structured Logging. Error logs must use `exc_info=True` for full traceback, not stringified exceptions.

## Suggestions

1. **EmailNotification could validate email format** — Currently only checks non-empty. A simple regex or email validator would catch malformed addresses earlier.

2. **Commit granularity** — All files appear in one diff. Conventional Commits expects one logical change per commit — domain, service, and infrastructure could be separate commits.

## Must NOT do

- Rewrite the code in the review — suggest, reference KB, let the developer fix it
- Invent findings not grounded in KB files
- Say "looks good" without checking all AC coverage
- Skip the cognitive debt check ("Can you explain the key design decision?")
- Approve without flagging the `str(e)` security violation

## Quality signals

- Every Must Fix cites a specific KB file and section
- AC coverage table shows gaps clearly
- Review uses `templates/review-template.md` format
- Severity levels are correct (security = Must Fix, magic strings = Should Fix, email validation = Suggestion)
- Cognitive debt check is asked before delivering the verdict
