# Eval Input: Story Refiner

## Feature Idea

"We want to see playbook usage on a dashboard — sessions per day, which agents actually get used, token spend per agent. The playbook already logs something locally when a Claude Code session ends, but nobody looks at JSONL files on individual laptops. We use Datadog for everything else, so just push it there."

## Grounding

This scenario targets the ai-playbook repository itself, so research findings cite real files — the precondition for a `provenance: captured` baseline (see `evals/samples/README.md` § Refreshing a sample). The relevant code is the session-telemetry harness (`harness/telemetry.sh`, `knowledge-base/observability.md` § Agent Telemetry).
