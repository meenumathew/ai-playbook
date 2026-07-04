---
provenance: curated
---

# Baseline Sample: diff-reviewer

## Verdict

Request changes.

## Acceptance Criteria Coverage

| AC | Test evidence | Status |
|---|---|---|
| AC1 shipment email happy path | `test_order_shipped_sends_email` | Covered |
| AC2 skip notification when no email | missing `test_order_shipped_skips_notification_when_no_email` | Gap |
| AC3 email failure logged without affecting order | missing `test_email_failure_is_logged_without_affecting_order` | Gap |

## Must Fix

1. `notification_service.py`: `logger.error(str(e))` violates `CLAUDE.md` § Security and `knowledge-base/security.md` § Data Handling. Use structured error logging with `exc_info=True`; stringifying the exception loses traceback and may leak unsafe text.

2. `tests/test_notifications.py`: the manual try/except assertion should be `pytest.raises(ValueError)` per `knowledge-base/testing.md` § Test Quality Rules. The current test has logic in the assertion path and can pass for the wrong reason.

3. AC2 and AC3 have no tests. Each acceptance criterion needs direct behavior coverage before this can merge.

4. `notification_service.py` uses `EmailNotification` without importing it, so the new path will fail at runtime.

## Should Fix

1. Hardcoded email subject/body strings should be constants or a template so the message contract has one owner.
2. `NotificationService` accepts a concrete `SendGridAdapter`; define a domain port and have infrastructure implement it.
3. The broad exception handler should catch the SendGrid failure type rather than all exceptions.
4. The same `logger.error(str(e))` issue also violates `knowledge-base/observability.md` § Structured Logging.

## Suggestions

- Validate email format before constructing the notification command.
- Split the domain/service/infrastructure work into separate logical commits if this grows further.

## Cognitive Debt Check

Before revising, please explain the key design decision: why does the service depend on an email port instead of importing the SendGrid adapter directly?

## Summary

Security and AC coverage gaps block approval. I did not rewrite the code; each finding is grounded in the project KB and should be fixed by the implementation agent.
