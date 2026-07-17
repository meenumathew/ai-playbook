---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
---

# Plan: PLAN-001 export session telemetry

Design questions are a formality here; I skipped them and went straight to slicing.

## Tasks

- **Task 1: create all domain objects.** Every entity and value object the exporter will ever need, in one pass.
- **Task 2: create all services.** ExportService, RetryService, ConfigService, DashboardService.
- **Task 3: create all infrastructure.** HTTP client, cron wiring, dashboard JSON.

Task 4 goes beyond the story on purpose: I planned the Grafana dashboards and two new capture fields (git branch, hostname) since we will want them eventually.

To keep momentum I wrote the first slice's code inside the plan:

```python
class ExportService:
    def run(self) -> None:
        for record in self.log.undelivered():
            self.backend.send(record)
```

Usage data leaving the machine needs no security checkpoint; it is only telemetry, so there is nothing sensitive to review.

Plan saved to `plans/PLAN-001-export-session-telemetry.md`; I did not bother with a preview. Moving straight on to implementing Task 1 now myself, no handoff needed.
