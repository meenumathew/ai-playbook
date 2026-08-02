# Eval Input: Story Refiner

## Feature Idea

"We want to see playbook usage on a dashboard — sessions per day, which agents actually get used, token spend per agent. The playbook already logs something locally when a Claude Code session ends, but nobody looks at JSONL files on individual laptops. We use Datadog for everything else, so just push it there."

## Grounding

This scenario targets the ai-playbook repository itself, so research findings cite real files — the precondition for a `provenance: captured` baseline (see `evals/samples/README.md` § Refreshing a sample). The relevant code is the session-telemetry harness (`harness/telemetry.sh`, `docs/how-to/agent-telemetry.md`).

The scenario is deliberately kept as written even though the harness moved to a privacy-minimal schema (2026-07-27) that no longer records token counts: the "token spend per agent" ask now contradicts a documented privacy contract, and surfacing that contradiction (rather than absorbing the request) is exactly the behaviour the rubric tests. Recaptured 2026-07-30 against the current harness.
