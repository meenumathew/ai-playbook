# Eval Expected: Code Auditor

The code-inspector should produce the following findings when given `code-inspector-input.md`:

## Must identify (by priority)

### P0 — Security

1. **Raw SQL strings in db.py** — SQL injection risk. Must use parameterised queries. Cites `security.md` § Input Validation.
2. **token_manager.py has no tests** — JWT handling is a critical security path. 100% branch coverage required per `testing.md` § Coverage Targets.
3. **No tests for reset_password or change_email** — Critical auth paths without test coverage. Cites `testing.md` § Test Ordering (coverage completeness check).
4. **SSRF in verify_webhook** — Fetches user-supplied URL with no host allowlist. Must validate target hosts and block internal/private IPs. Cites `security.md` § Input Validation (SSRF).

### P1 — Domain

1. **auth_service.py is a Large Class (450 lines, 6+ responsibilities)** — Violates single responsibility. Cites `design-patterns.md` § Anti-Patterns (Large Class). Recommend splitting into focused services (AuthService, PasswordService, UserManagementService).
2. **permissions.py inspects `user.role.value` from outside** — Inquisitive code. The User entity should own its permission logic (`user.has_permission(action)`). Cites `design-patterns.md` § Anti-Patterns (Inquisitive Code).
3. **auth_service.py imports db.py directly** — Domain/service layer depends on infrastructure. Should use a repository port. Cites `CLAUDE.md` § Architecture.
4. **auth_service.py imports email_sender.py directly** — Same issue. Email sending is infrastructure; should be behind a port. Cites `design-patterns.md` § DDD Tactical Patterns (Port).

### P5 — Service

1. **auth_service.py mixes orchestration with business rules** — Business rules (password validation, token expiry logic) should live in domain objects. Cites `CLAUDE.md` § Architecture ("Business rules live in domain objects, not services").

## Health Score

**Fail** — Multiple P0 (security) and P1 (domain) findings. Auth module has critical coverage gaps and architectural violations.

## Must NOT do

- Invent findings that can't be verified from the file structure and observations
- Suggest fixes beyond what's needed — recommend, don't implement
- Miss the SQL injection risk (P0 security finding)
- Miss the SSRF risk in verify_webhook (P0 security finding)
- Miss the Large Class in auth_service.py
- Rate this module as "Pass" or "Warn" — the security gaps mandate "Fail"
- Write source code or test code

## Quality signals

- Report saved to `audits/AUDIT-NNN-auth.md`
- Findings grouped by priority (P0 first, then P1, P2, P3, P4, P5, P6)
- Every finding cites a specific KB file and section
- Recommended actions are concrete (split auth_service.py into X, Y, Z — not "consider refactoring")
- Cross-file issues section identifies the architecture violation pattern (multiple direct infrastructure imports)
- Optional learning loop: suggests recording the "no direct infrastructure imports in service layer" rule as an ADR under `docs/adr/` if it's a recurring pattern
- Handoff message mentions xp-pair-programmer for fixing findings
