---
name: notifier
description: 'Pluggable adapter for outbound notifications (Slack, email, generic webhook) so release-captain and incident-responder can ping humans without embedding a vendor SDK'
user-invocable: false
license: MIT
---

# Notifier: Pluggable Outbound Notifications

## When to Use

Any agent pinging humans about a playbook event: release shipped, smoke failed, SEV1, postmortem ready. Replaces direct `curl` / SDK calls so agents work on any notifier.

Used by: release-captain (smoke result, release shipped), incident-responder (severity classified, resolved, postmortem ready).

**Default is `none`**: no notifications until adopters opt in. External side effects require explicit configuration.

**Implementation boundary:** this is an agent operation contract, not a Python runtime notifier shipped by `src/deploy_ai_playbook/`. The CLI deploys this markdown; adopters satisfy the contract with their configured webhook, mailer, or no-op provider.

## Supported Providers

| Provider | Provider key | Wire | Auth |
|---|---|---|---|
| Slack (incoming webhook) | `slack` | `curl` POST to webhook URL | Webhook URL in `SLACK_WEBHOOK_URL` env var |
| Email (sendmail / msmtp / direct SMTP) | `email` | `curl` against an SMTP gateway, or local `sendmail` | `EMAIL_SMTP_URL` (e.g. `smtps://user:pass@host:465`) and `EMAIL_FROM`, `EMAIL_TO` |
| Generic webhook (custom: e.g. Mattermost, Discord, internal bot) | `webhook` | `curl` POST to URL with JSON body | `WEBHOOK_URL` env var; optional `WEBHOOK_AUTH_HEADER` |
| Off | `none` | (no-op) |: |

PagerDuty, Opsgenie, platform-specific paging: out of scope. Integration surface (incident lifecycle, escalation policies) is far bigger than a webhook. Hand off to existing on-call systems at the human layer.

## Configuration

In `.ai-playbook.toml` (full schema: `templates/.ai-playbook.toml.example`):

```toml
[notifier]
provider = "slack"                # slack | email | webhook | none (default)

# Per-event routing: agents call notify(event, ...) and the skill maps event to channel.
# Channels are provider-specific keys; for slack these are channel hints in the message,
# for webhook these are routing fields in the JSON body.
[notifier.events]
release_shipped     = "#deploys"
smoke_warn          = "#deploys"
smoke_fail          = "#oncall"
incident_sev1       = "#oncall"
incident_sev2       = "#oncall"
incident_resolved   = "#deploys"
postmortem_ready    = "#engineering"

# Severity floor: events below this severity are suppressed. Useful in
# noisy CI environments. Floor levels: debug | info | warn | error.
#
# WARNING: setting floor too high silently drops routine records. With
# floor = "warn" you lose `release_shipped`, `incident_resolved`, and
# `postmortem_ready` (all severity = info). The release tag and the
# incident record remain the source of truth: but no one gets pinged.
floor = "info"
```

Env vars (`SLACK_WEBHOOK_URL`, etc.) live outside the config file: never commit secrets.

## Operations

One operation. Agents call it; skill resolves provider + routing.

### `notify(event, message, severity, context=None)`

| Argument | Type | Notes |
|---|---|---|
| `event` | string | Canonical event name from the table below: used to route via `[notifier.events]` |
| `message` | string | Plain-text body, ≤ 280 chars for chat, longer for email. Format: `{verb}: {subject}: {one-line detail}`. Must pass § Sanitization before any provider call. |
| `severity` | enum | `debug` / `info` / `warn` / `error`. Suppressed if below the configured floor. |
| `context` | dict (optional) | Routing metadata only. Slack: `{ "channel": "#override", "thread_ts": "..." }`. Webhook: `{ "route": "deploys" }`. Email: `{ "to_extra": ["bcc@..."] }`. No raw issue bodies, logs, diffs, stack traces, or provider responses. |

### Canonical event names

| Event | Emitted by | Severity | Message template |
|---|---|---|---|
| `release_shipped` | release-captain Phase 6 | info | `Released vX.Y.Z: merged <ref>, tagged <tag>, smoke <status>` |
| `smoke_warn` | release-captain Phase 5 | warn | `Smoke WARN on vX.Y.Z: <signal> <metric>` |
| `smoke_fail` | release-captain Phase 5 | error | `Smoke FAIL on vX.Y.Z: <signal> <metric>; rollback in progress` |
| `incident_sev1` | incident-responder Phase 1 | error | `SEV1 INC-YYYY-MM-DD-slug: <symptom>; on-call paged` |
| `incident_sev2` | incident-responder Phase 1 | warn | `SEV2 INC-YYYY-MM-DD-slug: <symptom>` |
| `incident_resolved` | incident-responder Phase 2 | info | `Resolved INC-YYYY-MM-DD-slug after Hh Mm: <one-line cause>` |
| `postmortem_ready` | incident-responder Phase 3 | info | `Postmortem ready for INC-YYYY-MM-DD-slug: <one-line summary>` |

Adopters add new events in their adopter pack: never hardcode event names in agent files.

## Sanitization

Outbound notification payloads cross a trust boundary. Before calling any provider:

1. Build messages from allowlisted fields only: event name, artifact ID, PR/MR ref, tag, severity, status, and a short human-written summary.
2. Never send raw issue bodies, PR descriptions, logs, diffs, stack traces, customer identifiers, or provider response bodies.
3. Redact common sensitive shapes in both `message` and `context`: bearer/API tokens, credentials, email addresses, URLs, and Slack control tokens (`@channel`, `@here`, `<...>`).
4. Keep `context` provider-specific and allowlisted; drop unknown keys instead of forwarding arbitrary JSON.
5. If redaction changes the message materially, append `redacted` rather than the removed value.

`knowledge-base/security.md` § Data Handling. This section is canonical for what counts as sensitive. Agents must summarize external text before notification; this skill must reject or redact anything that still looks raw.

## Provider Implementations

Pseudocode below shows the wire call. Each adapter receives `event`, `message`, `severity`, optional `context`: snippets assume these are bound to shell vars (`event="$1"`, etc.) before the `curl`.

### Slack adapter

```bash
# notify(event, message, severity): arguments bound to $event, $message, $severity.
# Channel routing: look up [notifier.events].<event> to get a channel hint
# (e.g. "#oncall"), then resolve it to a per-channel webhook env var by
# upper-casing and prefixing: "#oncall" -> SLACK_WEBHOOK_URL_ONCALL.
# If the per-channel var is unset, fall back to SLACK_WEBHOOK_URL.

channel="$(toml_get notifier.events."$event")"      # e.g. "#oncall"
case "$channel" in
  "#deploys") webhook="${SLACK_WEBHOOK_URL_DEPLOYS:-${SLACK_WEBHOOK_URL:-}}" ;;
  "#oncall") webhook="${SLACK_WEBHOOK_URL_ONCALL:-${SLACK_WEBHOOK_URL:-}}" ;;
  *) webhook="${SLACK_WEBHOOK_URL:-}" ;;
esac

curl -fsS -X POST -H 'Content-Type: application/json' \
  --data "$(printf '{"text": "[%s] %s"}' "$severity" "$message")" \
  "$webhook"
```

- Single-channel: only `SLACK_WEBHOOK_URL`. Multi-channel: add `SLACK_WEBHOOK_URL_DEPLOYS`, `SLACK_WEBHOOK_URL_ONCALL`. Mapping is mechanical: channel hint in `[notifier.events]` becomes the suffix.
- Slack rate-limits webhooks at ~1/sec. Rarely an issue except bursty incidents.

### Email adapter

```bash
# notify(event, message, severity): arguments bound to $event, $message, $severity.

printf 'From: %s\nTo: %s\nSubject: [%s] %s\n\n%s\n' \
  "$EMAIL_FROM" "$EMAIL_TO" "$severity" "$event" "$message" \
  | curl -fsS --url "$EMAIL_SMTP_URL" \
    --mail-from "$EMAIL_FROM" --mail-rcpt "$EMAIL_TO" \
    --upload-file -
```

- Email is high-latency. Use for postmortems and digest events, not real-time pages.
- `EMAIL_TO` should be a distribution list, not an individual: alerts are blameless.

### Webhook adapter

```bash
# notify(event, message, severity, context): arguments bound to shell vars.
# context_json is the JSON-serialized sanitized context allowlist, or "null" if absent.

curl -fsS -X POST -H 'Content-Type: application/json' \
  ${WEBHOOK_AUTH_HEADER:+-H "$WEBHOOK_AUTH_HEADER"} \
  --data "$(jq -nc \
    --arg event "$event" \
    --arg severity "$severity" \
    --arg message "$message" \
    --argjson context "${context_json:-null}" \
    '{event: $event, severity: $severity, message: $message, context: $context}')" \
  "$WEBHOOK_URL"
```

- Endpoint owns the format. Mattermost, Discord, internal bots, observability platforms: anything that accepts JSON POST. Do not forward arbitrary context keys.
- Add `WEBHOOK_AUTH_HEADER='Authorization: Bearer xxx'` if auth required.
- `jq` safely escapes the message: never inline user strings into JSON via `printf`.

### `none` adapter

```text
(no-op: stdout: "Notifier off: would have sent event <event>.")
```

Default. Safe for first-time adopters and noisy CI environments.

## Approval Gate

This is the notifier-specific gate for outbound side effects; the general playbook rule lives in `CLAUDE.md` § Shared Rules § Approval gate.

| Severity | Approval gate |
|---|---|
| `debug` / `info` | None: send |
| `warn` | None: send |
| `error` | **For `incident_sev1` only:** the agent must say `Notifying #oncall via slack about SEV1. Say 'notify' to proceed.` and wait for the explicit signal. SEV1 pings are external side effects with on-call impact. Other `error` events (smoke_fail) do not gate, because their on-call cost is bounded. |

## Untrusted Input

`event`, `message`, and `context` originate from agent state: but issue titles, PR descriptions, log excerpts, and user input may flow through. `CLAUDE.md` § Shared Rules § Untrusted input applies. Strip or escape Slack-control characters (`<>`, `@channel`) and HTML for email. The skill rejects or redacts unsafe payloads; agents should still avoid pasting raw external content into the message.

## Failure Modes

| Failure | Response |
|---|---|
| Provider env var missing | `Notifier provider <provider> requires <ENV_VAR>. Skipping.` Continue. |
| Sanitizer rejects payload | Print `Notification payload rejected by sanitizer for <event>.` Do not include the rejected content. Continue. |
| `curl` non-2xx | Print status/category only. Do not print provider response body. No retry. Continue. |
| Endpoint timeout (default 5s) | Print timeout. Continue. |
| `none` provider | `Notifier off: would have sent event <event>.` Continue. |

The notifier never blocks the agent. The original artifact (release tag, postmortem) is the source of truth, not the ping.

## Adding a New Provider

1. Add row to supported-providers with wire mechanism + auth.
2. Add Adapter section with the exact `curl` call.
3. Add detection in configuration.
4. Add sensitive env vars to `docs/limitations.md`.
5. Allow the new CLI in your tool's command permissions if one is needed (Claude Code: `.claude/settings.local.json`; Copilot/Kiro: the equivalent permission setting). Slack/email/webhook use `curl`, already allowed.

## Related

- `knowledge-base/design-patterns.md` § Layer 1: Vendor-Neutral Operation IDs. The playbook-wide rule this skill instantiates: `notify(event, ...)` with canonical event names is the stable contract, Slack / email / webhook / `none` are interchangeable backends.
- `agents/release-captain.agent.md`: primary consumer for release events.
- `agents/incident-responder.agent.md`: primary consumer for incident events.
- `skills/host-adapter/SKILL.md`: sibling vendor-neutral skill for git-host ops.
- `knowledge-base/observability.md` § Agent Telemetry: the notifier is operational notification; that file covers the *measurement* side.
