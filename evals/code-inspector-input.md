# Eval Input: Code Inspector

## Request

"use code-inspector: inspect the harness/ directory (the shell-based session harness: telemetry.sh, read-budget.sh, check-teachback.sh, settings.example.json, and the CI/config templates in that folder). Deep audit, all priority groups."

## Grounding

This scenario targets the ai-playbook repository itself, so audit findings cite real files — the precondition for a `provenance: captured` baseline (see `evals/samples/README.md` § Refreshing a sample, capture prerequisite). The scope is the shipped session harness: POSIX shell scripts (`harness/telemetry.sh`, `harness/read-budget.sh`, `harness/check-teachback.sh`) plus the CI/config templates (`harness/ci.yml`, `harness/security.yml`, `harness/Makefile`, `harness/pre-commit-config.yaml`, `harness/dependabot.yml`, `harness/settings.example.json`). The rubric's expected findings were verified against these files at capture time (2026-07-26); if the harness changes materially, recapture rather than patching the baseline.
