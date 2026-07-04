# Eval samples

Committed baseline outputs are validated on every CI run and judged on demand by the opt-in eval-drift workflow; that workflow fails closed when `ANTHROPIC_API_KEY` is missing.

## Scope — what these evals prove, and what they don't

These evals guard the **rubrics and the judge**, not the live agents. Nothing in CI executes `story-refiner`, `xp-pair-programmer`, etc. and feeds their output to the judge — the harness reads the **committed baseline** in `evals/samples/<agent>.md` (a representative, often hand-curated, "good" output) and checks it against the rubric.

- ✅ **Proven:** rubrics parse; a known-good baseline contains the expected behaviours (structural pre-check); and the LLM judge still rates that baseline as passing (opt-in drift detection). A judge failure means the baseline and the rubric drifted apart.
- ❌ **Not proven:** that the agents *currently behave* per their rubric. The agents are prompt files; they are never run in CI. Confirming live behaviour is deferred work — see [`docs/limitations.md`](../../docs/limitations.md) (eval suite is v1): golden-transcript capture or live-agent runs.

Two further limits to read honestly:

- **Structural `ok` is a weak signal.** The pre-check passes a must-demonstrate item at ≥50% of its keywords and counts a keyword present at ≥60% of its significant tokens — so a green structural run is a smoke test, not quality assurance. The LLM judge is the real semantic gate; do not treat green structural CI as proof of agent quality.
- **Adversarial coverage is partial.** Adversarial baselines under `samples/adversarial/` are judged by the drift job like the standard set, but only the agents with a committed baseline get semantic coverage (currently `story-refiner-adversarial`, `release-captain-adversarial`). The other `*-adversarial` rubrics remain structural-only (`check-structure` + `calibrate`) until someone curates their baselines — adversarial outputs are procedural refusals, so curation is honest here.

## Negative controls — keeping the judge honest

`samples/negative/<agent>.md` files are **deliberately flawed** outputs (rubber-stamp reviews, gate-skipping releases). The drift job asserts the judge **FAILS** them; a negative control that passes means the judge has drifted lenient or the rubric eroded — the one failure direction the known-good baselines can't detect. Marked with `negative_control:` front-matter; `validate-samples` checks they map to a real rubric but does not structurally gate them (they are semantically bad, not necessarily keyword-poor). When adding one, make the flaws blatant violations of the rubric's `must_not` items, not subtle judgement calls.

## Data handling — baselines leave the repo

`judge` sends each sample's full content (and the matching rubric) to the Anthropic API. Treat everything in `evals/samples/` and `evals/*-expected.md` as **shared with a third party**: use synthetic examples only — no real credentials, customer data, internal URLs, or proprietary code. The structural commands (`check-structure`, `calibrate`, `validate-samples`) run fully offline; only `judge` makes API calls.

## Convention

- One file per agent: `<agent>.md` (for example, `story-refiner.md`).
- The filename's stem is passed to `evals/run_eval.py judge <agent>` and must match an `<agent>-expected.md` rubric in `evals/`.
- Content is a representative agent output for that agent's `<agent>-input.md` scenario. Prefer verbatim captured output; curated baselines are acceptable for initial seeding when clearly shaped as output artifacts rather than rubrics.
- **Provenance front-matter.** A sample may begin with a `---` block declaring `provenance: captured` (verbatim output from a real agent run in its actual tool — optionally with `model:`, `tool:`, `captured_at:`) or `provenance: curated` (a hand-written seed/placeholder). The block is stripped before structural and judge validation, so it never affects scoring. `validate-samples` prints the provenance and **warns on anything other than `captured`**, because only a captured baseline is evidence of how the agent actually behaves. `story-refiner.md` is `captured` (2026-06-12, Claude Code, repo-grounded scenario); the other baselines remain `curated` seeds — see § Scope.

The standard agent set is derived from the shipped `agents/*.agent.md` files. Run `python evals/run_eval.py list-agents` to see the names the drift workflow expects.

Run `python evals/run_eval.py validate-samples` before committing sample changes. It checks that every standard agent has a sample and that each sample passes the structural rubric pre-check. This does not replace the LLM judge; it catches stale or malformed baselines without an API key.

## How drift is caught

`.github/workflows/eval-drift.yml` is opt-in: it runs on demand via `workflow_dispatch` (the weekly Monday 06:00 UTC cron is commented out by default — uncomment it in the workflow to restore automatic runs). It first checks that every standard agent has a committed baseline, then requires `ANTHROPIC_API_KEY` before judging. Each `evals/samples/*.md` is passed to `uv run python evals/run_eval.py judge <agent> <sample>`, which calls Claude as a semantic judge against the rubric. A failing judge means either the captured output drifted from the rubric, or the rubric drifted from what the agent now produces — both worth investigating.

## Refreshing a sample

When an agent prompt changes meaningfully, recapture: run the agent **in its real tool** (Claude Code / Copilot / Kiro) against `evals/<agent>-input.md`, copy its verbatim output into `evals/samples/<agent>.md`, and set the front-matter to `provenance: captured` (with `model:`/`tool:`/`captured_at:` for traceability). Commit, and the drift job judges the *new* baseline going forward. This — capturing from the real runtime — is the intended way to make a baseline reflect actual agent behaviour; the harness deliberately does **not** reconstruct the agent's prompt in CI (that would be brittle and drift from the real tool).

**Capture prerequisite (discovered while applying the playbook to its own repository, 2026-06-11):** most input scenarios are synthetic — they describe codebases that do not exist, and their rubrics expect `file:line` research citations into those codebases. Running the agent in a real tool against such an input cannot produce an honest capture: the model would have to invent the research findings, which is curated content under a misleading label. A true `captured` baseline needs a **fixture repository matching the scenario** or a scenario re-grounded on a real repository. `story-refiner-input.md` took the second path (2026-06-12): its scenario targets this repository's own telemetry harness, so its baseline cites real files and is honestly `captured`. The remaining baselines stay `curated` — do not mark a sample `captured` unless the agent could genuinely read the code it cites.

**After editing a rubric or baseline,** trigger `eval-drift.yml` via `workflow_dispatch` so a rubric↔baseline semantic mismatch surfaces in the same PR cycle rather than going unnoticed.

**Chained baselines — the rewrite radius.** `tests/acceptance/test_workflow_chain.py` requires the `story-refiner` and `slice-planner` baselines to describe **one story** (shared test behaviours prove the handoff chain is continuous). Re-grounding or refreshing either one therefore cascades: input, expected, rubric, and baseline of **both** agents move together (the 2026-06-12 re-grounding touched 8 files). The other six agents' baselines are judged in isolation. If you add a new agent to the chain contract, you are signing its eval set up for the same coupled-rewrite cost — do it deliberately.

## Why this isn't on every push

`judge` calls the Anthropic API. Running it per-PR would cost money on every commit and add a non-deterministic gate. Structural checks — `python evals/run_eval.py check-structure`, `python evals/run_eval.py calibrate`, and `python evals/run_eval.py validate-samples` — already run in the regular CI job and catch malformed rubrics or stale baselines on every push for free.

## Structural calibration

Regular CI also runs `python evals/run_eval.py calibrate`. Calibration creates controlled synthetic pass/fail cases for every standard and adversarial rubric:

- The good case includes independent evidence for every must-demonstrate keyword and must pass structural validation.
- The bad case is a rubric-keyword echo and must fail the echo guard.

This calibrates the cheap structural pre-check. It does not replace the LLM judge for semantic quality.
