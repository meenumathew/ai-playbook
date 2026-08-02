# Eval samples

Committed baseline outputs are validated on every CI run and judged on demand by the opt-in eval-drift workflow; that workflow fails closed when `ANTHROPIC_API_KEY` is missing.

## Scope — what these evals prove, and what they don't

These evals guard the **rubrics and the judge**, not the live agents. Nothing in CI executes `story-refiner`, `xp-pair-programmer`, etc. and feeds their output to the judge — the harness reads the **committed baseline** in `evals/samples/<agent>.md` (a representative, often hand-curated, "good" output) and checks it against the rubric.

- **Proven:** rubrics parse; a known-good baseline contains the expected behaviours (structural pre-check); the `must_not` prohibitions fire on the committed negative controls (corpus-based calibration — keywords are behavioral indicators a violating transcript actually contains); and the LLM judge still rates that baseline as passing (opt-in drift detection). A judge failure means the baseline and the rubric drifted apart.
- **Not proven:** that the agents *currently behave* per their rubric. The agents are prompt files; they are never run in CI. Confirming live behaviour is deferred work — see [`docs/limitations.md`](../../docs/limitations.md) (eval suite is v1): golden-transcript capture or live-agent runs.

Two further limits to read honestly:

- **Structural `ok` is a weak signal.** The pre-check passes a must-demonstrate item at ≥50% of its keywords and counts a keyword present at ≥60% of its significant tokens — so a green structural run is a smoke test, not quality assurance. The LLM judge is the real semantic gate; do not treat green structural CI as proof of agent quality.
- **Adversarial coverage is complete but curated.** Every adversarial pair has a committed baseline under `samples/adversarial/`, so all eight get judged by the drift job alongside the standard set. All adversarial baselines are `curated`: adversarial outputs are procedural refusals, so curation is honest here (see § Refreshing a sample for why hostile inputs cannot produce honest captures).

## Negative controls — keeping the judge honest

`samples/negative/<agent>.md` files are **deliberately flawed** outputs (rubber-stamp reviews, gate-skipping releases). They do double duty:

1. **Structural calibration corpus.** Each control declares, in `violates:` front-matter, the 2–4 `must_not` rubric ids whose keywords genuinely appear in its text. `calibrate` (run in regular CI) validates every control and fails unless each declared id is structurally flagged — so `must_not` keywords stay behavioral indicators that real violating text trips, not criterion prose that nothing ever matches.
2. **Judge leniency detection.** The drift job asserts the judge **FAILS** each control (exit code), then `verify-negative-controls` parses the per-item verdicts and requires the declared ids to be marked violated. A control that passes — or fails only on missing `must_demonstrate` items while its prohibitions slip through — means the judge drifted lenient or the rubric eroded, the one failure direction the known-good baselines can't detect.

Marked with `negative_control:` front-matter; `validate-samples` checks they map to a real rubric but does not gate them on the full structural pass (they also miss `must_demonstrate` items, which is expected). When adding one, make the flaws blatant violations of the rubric's `must_not` items, verify by grep which item keywords the text actually contains, and declare exactly those ids in `violates:`.

## Data handling — baselines leave the repo

`judge` sends each sample's full content (and the matching rubric) to the Anthropic API. Treat everything in `evals/samples/` and `evals/*-expected.md` as **shared with a third party**: use synthetic examples only — no real credentials, customer data, internal URLs, or proprietary code. The structural commands (`check-structure`, `calibrate`, `validate-samples`) run fully offline; only `judge` makes API calls.

## Convention

- One file per agent: `<agent>.md` (for example, `story-refiner.md`).
- The filename's stem is passed to `evals/run_eval.py judge <agent>` and must match an `<agent>-expected.md` rubric in `evals/`.
- Content is a representative agent output for that agent's `<agent>-input.md` scenario. Prefer verbatim captured output; curated baselines are acceptable for initial seeding when clearly shaped as output artifacts rather than rubrics.
- **Provenance front-matter.** A sample may begin with a `---` block declaring `provenance: captured` (verbatim output from a real agent run in its actual tool — optionally with `model:`, `tool:`, `captured_at:`) or `provenance: curated` (a hand-written seed/placeholder). The block is stripped before structural and judge validation, so it never affects scoring. `validate-samples` prints the provenance and **warns on anything other than `captured`**, because only a captured baseline is evidence of how the agent actually behaves. Captured so far: `story-refiner.md` and `slice-planner.md` (recaptured 2026-07-30 against the privacy-minimal telemetry harness), plus `docs-maintainer.md`, `code-inspector.md`, `xp-pair-programmer.md`, `diff-reviewer.md` (2026-07-26) — all Claude Code, repo-grounded scenarios. The remaining baselines stay `curated` seeds — see § Scope. Multi-gate captures (slice-planner) keep the transcript verbatim and mark the developer's side of each approval gate with a bracketed italic line (*[Developer: approved]*), so the judge sees the agent's words only.
- **Grounding front-matter (optional).** A `curated` sample may add a `grounding:` line recording that its repo-mechanical content — commands, KB citations, template and skill paths — was verified against this repository on a given date, while the scenario code stays synthetic. This is a partial-honesty note, not a provenance upgrade: a re-grounded hand-written baseline is still `curated` (see § Refreshing a sample, capture prerequisite). `release-captain.md` carries this note; the other former carriers (`xp-pair-programmer.md`, `diff-reviewer.md`) were upgraded to `captured` on 2026-07-26 and dropped it.

The standard agent set is derived from the shipped `agents/*.agent.md` files. Run `python evals/run_eval.py list-agents` to see the names the drift workflow expects.

Run `python evals/run_eval.py validate-samples` before committing sample changes. It checks that every standard agent has a sample and that each sample passes the structural rubric pre-check. This does not replace the LLM judge; it catches stale or malformed baselines without an API key.

## How drift is caught

`.github/workflows/eval-drift.yml` is opt-in: it runs on demand via `workflow_dispatch` (the weekly Monday 06:00 UTC cron is commented out by default — enabling it is two steps: set the `ANTHROPIC_API_KEY` secret, then uncomment the `schedule:` block). It first checks that every standard agent has a committed baseline, then requires `ANTHROPIC_API_KEY` before judging. Each `evals/samples/*.md` is passed to `uv run python evals/run_eval.py judge <agent> <sample>`, which calls Claude as a semantic judge against the rubric and prints a provenance header (judge model id, rubric sha256) so archived verdicts are comparable across runs. After the judge loops, `verify-negative-controls` parses the per-item verdicts for each negative control and asserts its declared `violates:` ids were marked violated. A failing judge means either the captured output drifted from the rubric, or the rubric drifted from what the agent now produces — both worth investigating.

## Refreshing a sample

When an agent prompt changes meaningfully, recapture: run the agent **in its real tool** (Claude Code / Copilot / Kiro) against `evals/<agent>-input.md`, copy its verbatim output into `evals/samples/<agent>.md`, and set the front-matter to `provenance: captured` (with `model:`/`tool:`/`captured_at:` for traceability). Commit, and the drift job judges the *new* baseline going forward. This — capturing from the real runtime — is the intended way to make a baseline reflect actual agent behaviour; the harness deliberately does **not** reconstruct the agent's prompt in CI (that would be brittle and drift from the real tool).

**Capture prerequisite (discovered while applying the playbook to its own repository, 2026-06-11):** most input scenarios are synthetic — they describe codebases that do not exist, and their rubrics expect `file:line` research citations into those codebases. Running the agent in a real tool against such an input cannot produce an honest capture: the model would have to invent the research findings, which is curated content under a misleading label. A true `captured` baseline needs a **fixture repository matching the scenario** or a scenario re-grounded on a real repository. `story-refiner-input.md` took the second path (2026-06-12): its scenario targets this repository's own telemetry harness, so its baseline cites real files and is honestly `captured`. Five more followed on 2026-07-26: `slice-planner` (plans the story the story-refiner capture produced, against this repo's real CLI code), `code-inspector` (audits this repo's own `harness/` directory), `docs-maintainer` (the ADR scenario needs no fictional codebase — the decision content is fully supplied by the request, and the repo-mechanical parts, ADR numbering and template, are real), and the ship pair `xp-pair-programmer` + `diff-reviewer` (a real bug the code-inspector capture found in `harness/Makefile` was fixed TDD-first by the live agent and that genuine diff was then reviewed by the live agent — one story narrated across both, as the ship-half chain contract requires). Do not mark a sample `captured` unless the agent could genuinely read the code it cites. Two remain `curated`: `release-captain` (an honest capture needs a real PR/CI/merge/tag run on the host — feasible the next time a release ships through the agent, re-grounded to the same story as the ship pair) and `incident-responder` (stays curated until a real groundable incident exists — there is no production system here to page).

**After editing a rubric or baseline,** trigger `eval-drift.yml` via `workflow_dispatch` so a rubric↔baseline semantic mismatch surfaces in the same PR cycle rather than going unnoticed.

**Chained baselines — the rewrite radius.** `tests/acceptance/test_workflow_chain.py` chains the default workflow's baselines in two coupled groups. Build half: `story-refiner` and `slice-planner` must describe **one story** (shared test behaviours prove the handoff is continuous); re-grounding either cascades across input, expected, rubric, and baseline of both agents (the 2026-06-12 re-grounding touched 8 files). Ship half (added 2026-07-23): `xp-pair-programmer`, `diff-reviewer`, and `release-captain` must narrate one story too — the review cites test behaviours the implementation ran, and the release names the story artifact whose vocabulary matches the reviewed behaviours. Refreshing any ship-half baseline means keeping the other two aligned. Only `code-inspector`, `docs-maintainer`, and `incident-responder` baselines are judged in isolation. If you add a new agent to either chain contract, you are signing its eval set up for the same coupled-rewrite cost — do it deliberately.

## Why this isn't on every push

`judge` calls the Anthropic API. Running it per-PR would cost money on every commit and add a non-deterministic gate. Structural checks — `python evals/run_eval.py check-structure`, `python evals/run_eval.py calibrate`, and `python evals/run_eval.py validate-samples` — already run in the regular CI job and catch malformed rubrics or stale baselines on every push for free.

## Structural calibration

Regular CI also runs `python evals/run_eval.py calibrate`. Calibration has two layers:

- **Synthetic echo cases** for every standard and adversarial rubric: a good case (independent evidence for every must-demonstrate keyword) must pass, and a raw or filler-diluted keyword echo must fail the echo guard. These exercise the `check()`/echo-guard code paths.
- **Negative-control corpus** for the `must_not` layer: each committed control under `samples/negative/` must structurally trip the ids it declares in `violates:` front-matter. An earlier synthetic must-not case injected a rubric keyword into a generated string, which only proved the matcher matched its own input; calibrating against independently written violating transcripts makes the prohibitions falsifiable.

This calibrates the cheap structural pre-check. It does not replace the LLM judge for semantic quality.
