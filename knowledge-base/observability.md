---
id: observability
size: medium
tldr: Structured logs with correlation IDs; never log str(e); mask sensitive data at the boundary.
load_when: logging, metrics, tracing, health check, correlation ID, error reporting, external call
audience: all
canonical_for: log levels, structured logging, correlation IDs, health check pattern, sensitive data masking patterns, deploy-time signals, incident telemetry
cross_refs: security.md, performance.md, release.md, incident-response.md
verified: 2026-06-10
---

# Observability Conventions

## Agent Use

- **Read first:** Log Levels, What to Log, Structured Logging, Correlation IDs.
- **Load deeper only on trigger:** metrics, tracing, health checks, and sensitive-data masking.

---

## Log Levels

| Level | Agent action |
|-------|-------------|
| `DEBUG` | Detailed diagnostics: not in production by default |
| `INFO` | Normal events worth recording (startup, key operations) |
| `WARNING` | Unexpected but recoverable: include the expected value vs. the actual value |
| `ERROR` | Operation failed: include the attempted action, failure details, relevant IDs. Never log `str(e)`: see `security.md` § Data Handling for the canonical rule. |
| `CRITICAL` | System may not continue: alert-worthy |

---

## What to Log

| Event | Agent action |
|-------|-------------|
| Startup / shutdown | Log config summary (sanitized: no secrets) |
| Key business events | Log event type, resource ID, outcome |
| All errors | Log the attempted action, failure details, relevant IDs, correlation ID |
| External calls | Log target, duration, success/fail |
| Auth events | See `security.md` § Authentication & Authorisation |

**What NOT to log:** sensitive data: rules in `security.md` § Data Handling. No noise without diagnostic value. Never silently swallow exceptions: every `except` must log or re-raise.

---

## Structured Logging

Use structured logging (JSON) in production. Include key=value context, not just message strings.

```python
# Bad: no context
logger.error("Payment failed")

# Good: structured key-value fields the log pipeline can index
logger.error(
    "operation_failed",
    extra={"resource_id": resource.id, "provider": provider_name},
    exc_info=True,
)
# (with structlog: log.error("operation_failed", resource_id=resource.id, provider=provider_name))
```

Tools: `structlog`/`loguru` (Python), `pino`/`winston` (Node/TypeScript).

---

## Correlation IDs

Every request must carry a unique ID that propagates through all log entries and outbound calls.

| Rule | Agent action |
|------|-------------|
| Generate on inbound request | Middleware sets a UUID; bind to log context for the request lifetime |
| Propagate outbound | Forward as `X-Correlation-ID` header on all outbound HTTP calls |
| Log with every entry | Use context-aware logging (`structlog.contextvars` or equivalent) |

---

## Metrics

Metrics answer "is the system healthy?" and "where is it getting worse?" Use low-cardinality labels; never attach user IDs, emails, request bodies, or unbounded values as metric labels.

| Metric | Agent action |
|--------|-------------|
| Request rate | Track by route, method, status family, and service |
| Error rate | Alert on sustained 5xx and critical domain failures |
| Latency | Track p50, p95, and p99 for public entry points and external calls |
| Saturation | Track queue depth, connection pools, worker utilisation, memory, CPU |
| Business health | Track domain signals that reveal silent failure, such as payments authorised, jobs completed, or model predictions served |

This table implements the four golden signals (Google SRE: latency, traffic, errors, saturation): equivalently RED (rate, errors, duration) for request paths and USE (utilisation, saturation, errors) for resources: plus a business-health signal. Use those names when wiring dashboards or talking to SRE tooling.

Prefer OpenTelemetry metrics, Prometheus, CloudWatch, Datadog, or the platform standard already used by the project. Do not invent a second metrics stack without a reason.

---

## SLOs & SLIs

Turn the metrics above into **SLIs** (service-level indicators: success rate, p95 latency for a key journey) and set an **SLO** (the target, for example 99.5% success over a rolling 28-day window). Anchor alerts and the Deploy-Time Signals below to **SLO / error-budget breach**, not to absolute numbers in isolation: a 10% error-rate jump means something very different at a 99.9% SLO than at a 95% one. Where the project has no SLO yet, treat the absolute thresholds in the Deploy-Time Signals section below as an interim default and graduate to error-budget-based alerting as the journey matures.

---

## Tracing

Distributed traces connect one request across services, queues, databases, third-party calls. Use when requests cross process boundaries or when logs alone can't support latency / root-cause analysis.

| Rule | Agent action |
|------|-------------|
| Propagate trace context | Preserve W3C `traceparent` / `tracestate` or the platform equivalent across HTTP, queues, and async jobs |
| Name spans by operation | Use stable names such as `checkout.authorize_payment`, not raw URLs or user input |
| Add useful attributes | Include service, route, dependency name, status, retry count, and sanitized IDs |
| Avoid sensitive data | Never attach PII, tokens, full prompts, request bodies, or documents to spans |
| Sample intentionally | Use higher sampling for errors and critical flows; document the production sampling policy |

---

## Sensitive Data Masking

This section covers the HOW. For the WHAT (rules about what's sensitive): `security.md` § Data Handling.

| Pattern | Agent action |
|---------|-------------|
| Opaque IDs only | `user_id=user.id`: OK. `email=user.email`: flag as PII risk. |
| Truncate payment data | `card_last4=card[-4:]`: OK. Full card number: never. |
| Request bodies | Never log raw `request.body`: may contain secrets |
| Masking location | Apply in a shared log processor, not scattered across call sites: one miss exposes data |

---

## Health Checks

Every service must expose:

| Endpoint | Purpose | Agent action |
|----------|---------|-------------|
| `GET /health/live` | Is the process running? | Always return `200` if process is up |
| `GET /health/ready` | Are dependencies available? | Return `200` only if DB, cache, external services respond |

Rules: read-only (no mutations), respond in < 500ms, return `{"status": "ok"}` or `{"status": "degraded", "reason": "..."}`.

---

## Local Development

| Setting | Local | Production |
|---------|-------|------------|
| Log level | `DEBUG` | `INFO`+ |
| Format | Human-readable | JSON |
| Toggle | `LOG_LEVEL` env var | `LOG_LEVEL` env var |

---

## Deploy-Time Signals

What to watch in the 10–30 minutes after a deploy lands. Used by `release.md` § Post-Deploy Smoke and the release-captain agent.

| Signal | Healthy | Investigate | Roll back |
|---|---|---|---|
| Error rate (5xx + critical domain failures) | Within ±10% of pre-deploy baseline | 10–50% above baseline, sustained 5+ minutes | > 50% above baseline, or any new class of error |
| Latency p95 | Within ±20% of pre-deploy baseline | 20–50% above baseline | > 50% above baseline |
| Saturation (queue depth, pool usage, worker utilisation) | Within ±10% of baseline | 10–25% above baseline | > 25% above baseline, sustained |
| Domain KPI (orders, jobs completed, predictions served) | Trending as expected | Flat or declining vs same time-of-day last week | Zero, when non-zero is expected |
| Health endpoint | `200` consistently | Intermittent `503` | Sustained `503` or process restart loop |

**Rules:**

- Compare to a **same-time-of-day** baseline, not "last hour": traffic patterns vary.
- Hold the post-deploy watch window until at least one full request cycle for the slowest critical journey has completed.
- If a signal pegs to `Roll back`, apply `release.md` § Rollback first, then investigate.

---

## Incident Telemetry

What to capture during and after a SEV1/SEV2 incident so the postmortem has evidence. Used by `incident-response.md` § Blameless Postmortem.

| Capture | Why |
|---|---|
| Timestamps for: detection, ack, mitigation start, mitigation effective, resolution | Builds the postmortem timeline |
| Correlation IDs of representative failed requests | Links logs across services |
| Snapshot of the dashboard at the worst point | Postmortem evidence; survives metric retention windows |
| Every command run in production, with operator role and timestamp | Reproduces the response; survives shift handover |
| Recent deploys, config changes, feature flag flips | Top sources of incident causation |
| External vendor status pages screenshotted | Their pages may go offline or update retroactively |

**Rules:**

- Paste evidence into the incident record as you find it: do not rely on dashboards still showing the same window 48 hours later.
- Strip PII from captured payloads before pasting (`security.md` § Data Handling). Use opaque IDs and masked values.
- Link every captured artifact from the postmortem; orphan evidence is lost.

---

## Agent Telemetry

When agents run as part of automated workflows (CI, scheduled jobs, hosted runners), log enough to debug failures without re-running. Optional in interactive sessions; useful in unattended ones.

| Capture | Where | Notes |
|---|---|---|
| Session ID, timestamp, turn count | `.claude/usage.jsonl` (one JSON line per session-end) | The `Stop` hook payload provides session_id + transcript_path |
| Active agent (best-effort) | Same file | Grepped from the transcript: see `harness/telemetry.sh` |
| Dominant model + token totals | Same file (`model`, `tokens.{input,output,cache_creation,cache_read}`) | Summed from the transcript JSONL the Stop payload points at; requires `jq` |
| Story/plan/audit reference handled | Same file (when agent records it explicitly) | Lets you tie agent runs back to artifacts |
| Approval gates triggered and outcome | Out of scope for the basic hook | Requires the agent itself to log; not in the v1 hook |

**Scope note (operational, not financial).** Token totals reflect the transcript and are accurate for comparing agents/sessions; they won't match the provider's billing to the cent (cache pricing, service tier, rounding differ). Use for spotting Opus-on-everything and budgeting context. Use provider's billing export for invoicing.

**Harness scope.** Token capture reads the Claude Code transcript JSONL. Other harnesses (Cursor, Copilot, Continue) write different formats: those adopters get timestamp/session_id/turns but no `tokens` block. Correct degraded behaviour, not a bug.

### Wire-up

`ai-playbook deploy --tool claude` copies `harness/telemetry.sh`, makes it executable, and merges the `hooks.Stop` command into `.claude/settings.json`. Existing settings are preserved. If the JSON is malformed, deploy leaves it untouched, writes a `.broken-<timestamp>` copy, and reports the recovery step.

1. Run `ai-playbook deploy --agent all --tool claude` without `--no-harness`.
2. Run any agent. After session end, check `.claude/usage.jsonl`: one line per session.
3. Read via `/status`: slash command parses last 5 sessions, prints alongside tier and active agent.

For local-only or custom settings, copy the block from `harness/settings.example.json` into `.claude/settings.local.json`. Hook calls `${CLAUDE_PROJECT_DIR}/harness/telemetry.sh`.

Hook never blocks the agent: it silently degrades to "log what we can, skip what we cannot" if `jq` is missing or the transcript is unreadable.

### Reading the log

```bash
# Sessions per agent in the last week
jq -r 'select(.timestamp > "'$(date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)'") | .active_agent' \
  .claude/usage.jsonl | sort | uniq -c | sort -rn

# Average turns per agent
jq -r '[.active_agent, .turns] | @tsv' .claude/usage.jsonl \
  | awk '{count[$1]++; sum[$1]+=$2} END {for (a in count) printf "%s\t%.1f\n", a, sum[a]/count[a]}'

# Total output tokens per agent: find the Opus-on-trivial-work hotspots
jq -r 'select(.tokens != null) | [.active_agent, .tokens.output] | @tsv' .claude/usage.jsonl \
  | awk '{sum[$1]+=$2} END {for (a in sum) printf "%s\t%d\n", a, sum[a]}' | sort -k2 -rn

# Cache-hit ratio (cache_read / (cache_creation + cache_read)) per agent: high is good
jq -r 'select(.tokens != null) | [.active_agent, .tokens.cache_creation, .tokens.cache_read] | @tsv' \
  .claude/usage.jsonl | awk '{c[$1]+=$2; r[$1]+=$3} END {for (a in c) {t=c[a]+r[a]; printf "%s\t%.0f%%\n", a, (t>0?100*r[a]/t:0)}}'
```

Adopters needing per-message cost should pair this hook with provider billing export: keep operational (this hook) separate from financial (the provider).
