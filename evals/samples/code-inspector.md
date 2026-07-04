---
provenance: curated
---

# Baseline Sample: code-inspector

Report saved to `audits/AUDIT-042-auth.md`.

## Health Score

Fail. The module has multiple P0 security findings and P1 architecture violations.

## P0 Security

1. `db.py`: raw SQL strings concatenate user input. This is SQL injection risk; use parameterised queries. KB: `knowledge-base/security.md` § Input Validation.
2. `token_manager.py`: JWT validation has no tests. Token validation is a critical security path and needs 100% branch coverage. KB: `knowledge-base/testing.md` § Coverage Targets.
3. `auth_service.py`: `reset_password` and `change_email` have no tests. These are auth-critical flows; missing coverage is a release blocker. KB: `knowledge-base/testing.md` § Test Ordering.
4. `verify_webhook`: fetches a user-provided URL without host allowlisting or private-IP blocking. This is SSRF. KB: `knowledge-base/security.md` § Input Validation.

## P1 Domain

1. `auth_service.py` is about 450 lines and mixes login, password reset, token issuing, email change, and permission orchestration. Split into focused services. KB: `knowledge-base/design-patterns.md` § Anti-Patterns.
2. `permissions.py` reads `user.role.value` externally. Move permission logic onto the User entity as `user.has_permission(action)`. KB: `knowledge-base/design-patterns.md` § Anti-Patterns.
3. `auth_service.py` imports `db.py` directly. Service/domain code should depend on a repository port, not infrastructure. KB: `CLAUDE.md` § Architecture.
4. `auth_service.py` imports `email_sender.py` directly. Email sending should be behind a port. KB: `knowledge-base/design-patterns.md` § DDD Tactical Patterns.

## P5 Service

`auth_service.py` contains business rules for password validation and token expiry. Those rules belong in domain objects, not orchestration services. KB: `CLAUDE.md` § Architecture.

## Cross-File Pattern

The repeated direct imports from service code into infrastructure show a boundary rule gap. If this keeps recurring, record an ADR that service-layer code must use ports for persistence and email.

## Recommended Actions

1. Open a story for the P0 security fixes before feature work.
2. Use xp-pair-programmer to add JWT and account-management tests first.
3. Split `auth_service.py` into `AuthService`, `PasswordService`, and `UserManagementService` after characterization coverage exists.

No source or test code was written during this audit.
