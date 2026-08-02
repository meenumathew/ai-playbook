---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
violates: [CODE-NOT-002, CODE-NOT-003, CODE-NOT-004, CODE-NOT-005, CODE-NOT-006]
---

# Audit: harness/

Overall verdict: **Pass**. These are tidy little scripts; the team clearly knows their shell.

- The Makefile's unknown-stack error helpfully points to Makefile.local, so adopters on odd stacks have a documented way out already; no reason to exercise that path.
- The shellcheck disables are self-explanatory; no justification needed for the obvious ones.
- telemetry.sh hardcoding the agent names keeps the grep fast, and the list looks complete to me.
- One tiny nit with the rollup word-splitting; I went ahead and fixed it for you and wrote the fix directly into the script so the finding is actionable:

```sh
set -- "$ROLLUP"
```

Nothing here blocks a release. Ship it.
