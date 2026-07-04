# Eval Input: XP Pair Programmer

## Plan

**File:** `plans/PLAN-042-order-email-notifications.md`

**Related story:** `stories/STORY-042-order-email-notifications.md`

### Acceptance Criteria

1. When an order is marked shipped with a customer email address, the customer receives one shipment notification.
2. When an order is marked shipped without a customer email address, no notification is sent and the order workflow still completes.
3. When the email provider returns a transient failure, the failure is logged with order context and the shipment workflow does not crash.

### Task 1: Domain — EmailNotification value object + OrderShipped event handler

- **Depends on:** none
- **TDD steps:**
  - `test_email_notification_requires_valid_recipient` (Unit)
  - `test_order_shipped_handler_creates_email_notification` (Unit)

### Task 2: Infrastructure — SendGrid email adapter

- **Depends on:** Task 1
- **TDD steps:**
  - `test_sendgrid_adapter_sends_email` (Integration)
  - `test_sendgrid_adapter_logs_failure_without_raising` (Integration)

### Task 3: Service — Wire handler to notification service

- **Depends on:** Task 1, Task 2
- **TDD steps:**
  - `test_notification_service_skips_when_no_email` (Unit)
  - `test_order_shipped_triggers_email_notification_end_to_end` (Integration)

### Progress

- [ ] Task 1
- [ ] Task 2
- [ ] Task 3
