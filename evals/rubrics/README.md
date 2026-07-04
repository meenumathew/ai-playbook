# Eval rubric schemas

Schema-backed rubrics are the durable source for eval criteria. Every standard shipped agent has a JSON rubric; legacy `evals/*-expected.md` files remain as human-readable contracts and as a compatibility fallback for custom or older evals.

## Format

Each file is JSON at `evals/rubrics/<agent>.json`:

```json
{
  "agent": "xp-pair-programmer",
  "version": 1,
  "must_demonstrate": [
    {
      "id": "XP-MUST-001",
      "criterion": "Observable behavior the agent must demonstrate",
      "keywords": ["terms", "used by structural validation"],
      "evidence": "What the semantic judge should look for"
    }
  ],
  "must_not": [],
  "quality_signals": []
}
```

## Rules

- `id` values must be unique within each section.
- `version` must be `1`.
- `keywords` are for cheap structural validation only; the LLM judge evaluates semantic compliance.
- Keep `evidence` concrete so judge prompts ask for behavior, not rubric echoes.

## Updating the Judge Model

`evals/run_eval.py` pins the eval judge to the **most specific stable model id** Anthropic publishes for it (default: see the `EVAL_JUDGE_MODEL` line). When a model has a date-suffixed release id (for example, Sonnet 4.5, `claude-sonnet-4-5-20250929`), pin that. Some models — including the current default Sonnet 4.6 (`claude-sonnet-4-6`) — ship as an **alias only, with no date-suffixed form**; for those the alias is the most specific stable id available, so pin the alias. Either way the id is version-stable, so a verdict change in `eval-drift.yml` is signal — the agent regressed — rather than noise from a silent judge rotation.

**When to rotate:**

- A new judge release ships and Anthropic deprecates the prior release.
- An ADR records that the rubric language has evolved and the previous judge no longer scores correctly.
- A deliberate experiment compares two judges on the same rubrics.

**How to rotate:**

1. Run the full eval suite with `EVAL_JUDGE_MODEL=<new-pinned-id>` and confirm verdicts match the prior judge on the committed `evals/samples/*.md` baselines (or document the deltas in an ADR).
2. Update the default in `evals/run_eval.py` and note the rotation in `CHANGELOG.md` under `### Changed`.
3. If the rotation breaks any verdicts, file the rubric updates and the model bump in the same release.

Never use a **floating family** alias (`claude-sonnet`, `claude-opus`) as the default — those resolve to whatever generation Anthropic serves that day, so adopters running the cron will see noisy week-over-week deltas with no way to tell which side moved. A **version-specific** alias like `claude-sonnet-4-6` is fine when that version has no dated id: it is stable across the model's lifetime and only moves when you deliberately rotate.
