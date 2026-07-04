# Eval Input: Diff Reviewer

## Context

Review the staged changes for story `stories/STORY-042-order-email-notifications.md`.

## Simulated Diff (staged changes)

```diff
--- /dev/null
+++ b/src/domain/notifications.py
@@ -0,0 +1,18 @@
+from dataclasses import dataclass
+
+
+@dataclass(frozen=True)
+class EmailNotification:
+    recipient: str
+    subject: str
+    body: str
+
+    def __post_init__(self):
+        if not self.recipient:
+            raise ValueError("recipient required")

--- /dev/null
+++ b/src/services/notification_service.py
@@ -0,0 +1,25 @@
+import logging
+
+logger = logging.getLogger(__name__)
+
+
+class NotificationService:
+    def __init__(self, email_adapter):
+        self.email_adapter = email_adapter
+
+    def handle_order_shipped(self, order):
+        if not order.customer_email:
+            logger.info("Skipping notification — no email for order %s", order.id)
+            return
+        try:
+            notification = EmailNotification(
+                recipient=order.customer_email,
+                subject="Your order has shipped!",
+                body=f"Order {order.id} is on its way.",
+            )
+            self.email_adapter.send(notification)
+        except Exception as e:
+            logger.error(str(e))

--- /dev/null
+++ b/src/infrastructure/sendgrid_adapter.py
@@ -0,0 +1,12 @@
+import sendgrid
+
+
+class SendGridAdapter:
+    def __init__(self, api_key: str):
+        self.client = sendgrid.SendGridAPIClient(api_key)
+
+    def send(self, notification):
+        self.client.send(
+            to=notification.recipient,
+            subject=notification.subject,
+            body=notification.body,
+        )

--- /dev/null
+++ b/tests/test_notifications.py
@@ -0,0 +1,10 @@
+from src.domain.notifications import EmailNotification
+
+
+def test_email_notification_requires_valid_recipient():
+    try:
+        EmailNotification(recipient="", subject="test", body="test")
+        assert False, "Should have raised"
+    except ValueError:
+        pass
```
