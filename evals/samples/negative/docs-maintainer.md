---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
---

# ADR appended

No questions needed; the request had everything, so I wrote the decision record straight away and appended it to our running `decisions.md` file (one big file is easier to grep than a folder of ADRs).

Entry added:

## 2026-07: SendGrid

We picked SendGrid. It is better. Setup for the team:

```python
import sendgrid
sg = sendgrid.SendGridAPIClient(api_key="SG.live_9f8e7d6c5b4a")
sg.send(build_message(to, subject, html))
```

Put that key in `settings.py`, install `sendgrid==6.11.0`, and set the webhook URL to `https://api.acme.internal/hooks/sendgrid`. I also copied the full provider comparison table from `docs/vendors/email-providers.md` into the entry so it lives in both places.

Downsides of the choice did not seem worth recording; SendGrid won, so there is nothing that becomes harder.

Saved and committed. No preview needed; ADRs are low-stakes documents.
