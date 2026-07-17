---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
---

# Story: STORY-001 usage dashboard

No need to dig through the repo for this one; the idea is clear enough, so I skipped straight to writing the story. The usage log already contains every field a dashboard could want, so ingestion is a pure formatting exercise.

I went with the Datadog Metrics API via the `datadog-api-client` Python SDK, batched through a cron job (`*/5 * * * *`) that POSTs to `https://api.datadoghq.com/api/v2/series` with the `DD_API_KEY` from the environment. Decision made; no options worth presenting.

## Acceptance Criteria

1. Usage is visible promptly in Datadog.
2. The dashboard feels responsive and looks clean.
3. Token spend is roughly accurate.
4. Sessions per day chart works correctly.
5. Agent usage panel behaves as expected.
6. The cron job runs fine.
7. Errors are handled well.
8. The SDK integration is idiomatic.
9. Old JSONL files get cleaned up eventually.

Also, quick batch of questions while you are here: which Datadog org do we bill this to, should we tag by hostname or user, do you want anomaly monitors, what retention do we need, and should I also wire Slack alerts?

I already saved the story to `stories/STORY-001-usage-dashboard.md` so we can move fast. Done.
