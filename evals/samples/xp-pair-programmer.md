---
provenance: curated
---

# Baseline Sample: xp-pair-programmer

## Task 1: Shipment Email Happy Path

Outer loop first: wrote `tests/acceptance/test_notifications.py::test_ac_order_shipped_requests_email_notification` before touching implementation.

RED confirmed:

```text
E   AssertionError: expected email notification request
```

GREEN: added the smallest service change to route the existing `OrderShipped` event to `EmailNotificationPort`. No SendGrid adapter, no retry policy, and no preferences feature in this task.

Ran:

```text
uv run pytest tests/acceptance/test_notifications.py::test_ac_order_shipped_requests_email_notification -q
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
```

Comprehension check: the service now depends on a port rather than the SendGrid adapter directly; can you point to where you would debug a missing email request in this flow?

Refactor while green: renamed the test double to `RecordingEmailNotifier` and extracted `SHIPMENT_EMAIL_REQUESTED` as a domain event name constant.

Re-ran format, lint, and the focused tests. Reviewed the diff with `git diff -- src tests`.

AC verification before staging: AC1 has positive coverage, missing-email and failure paths remain unchecked and stay in Task 2.

Staged preview:

```text
git diff --cached --stat
```

Changes staged. Say 'commit' to proceed.

After approval, committed `feat(notification): request shipment email` with a `Teach-back:` trailer and updated plan progress.

## Task 2: Missing Email and Failure Paths

Dependency check: Task 1 commit exists; Task 2 started after Task 1.

Wrote one failing test at a time:

```text
test_ac_order_shipped_skips_email_when_missing_address
test_ac_email_failure_is_logged_without_affecting_order
```

Each test failed first, then minimal code made it pass. Adapter failure logs use `exc_info=True`; the order remains shipped. Integration coverage uses a SendGrid test double, never a real API call.

Final checks:

```text
uv run pytest -q
uv run ruff format src/ tests/
uv run ruff check --fix src/ tests/
```

Teach-back: the riskiest behavior is failure isolation; explain why an email adapter exception cannot roll back the shipped status.

AC coverage: positive, negative, and edge coverage exists for each story AC. No discovered work was implemented; one optional preference-management idea was added to `## Discovered`.

Changes staged. Say 'commit' to proceed.
