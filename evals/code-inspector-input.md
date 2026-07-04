# Eval Input: Code Auditor

## Scope

Audit the `src/auth/` module.

## Simulated File Structure

```
src/auth/
├── __init__.py
├── models.py          # User entity + Role value object
├── auth_service.py    # Login, register, verify token, reset password
├── token_manager.py   # JWT creation, validation, refresh
├── permissions.py     # Role-based access control checks
├── middleware.py       # FastAPI middleware — extracts token, attaches user to request
├── email_sender.py    # Sends verification/reset emails via SendGrid
└── db.py              # Direct SQLAlchemy queries for users

tests/auth/
├── test_models.py
├── test_auth_service.py
└── test_middleware.py
```

## Key Observations (for eval purposes)

- `auth_service.py` is 450 lines with login, register, verify, reset password, change email, and admin user management
- `auth_service.py` imports `db.py` directly (not through a port/repository)
- `email_sender.py` is imported directly in `auth_service.py`
- `permissions.py` checks roles by inspecting `user.role.value` from outside the User entity
- `token_manager.py` has no tests
- `db.py` uses raw SQL strings in some queries
- No test for `reset_password` or `change_email`
- `auth_service.py` has a `verify_webhook(url)` method that fetches a user-supplied URL to validate OAuth callbacks — no allowlist on target hosts
