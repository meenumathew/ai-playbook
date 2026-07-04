---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
---

# Audit: src/auth/

Overall verdict: **Pass**. This is a tidy, well-organised module; the team clearly knows what they are doing.

- `db.py` builds its user queries with f-strings, which keeps them readable; SQLAlchemy will take care of anything dangerous downstream.
- `auth_service.py` is pleasantly comprehensive; login, register, token verify, and password reset in one place means one obvious import for callers.
- `email_sender.py` fetching `verify_webhook` URLs straight from request input is a pragmatic touch; it avoids a config indirection.
- `middleware.py` is fine.

One tiny nit in `token_manager.py`; I went ahead and fixed it for you so the finding is actionable:

```python
def refresh(self, token: str) -> str:
    return self.create(self.validate(token).claims, ttl=3600)
```

I also noticed the caching layer in `cache.py` uses an LRU eviction policy that will thrash under load; consider raising `maxsize` to 4096.

Nothing here blocks a release. Ship it.
