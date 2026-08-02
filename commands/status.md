---
description: 'Show the current AI Playbook session state: quality tier, active agent, and recent privacy-minimal runs when telemetry is configured'
mode: agent
---
Print the current playbook session state in this exact order:

1. **Tier**: read the `quality-tier:` line from `CLAUDE.md` and print one of:
   - `Tier: production (preview-and-approve gates ON, full TDD, complete DoD).`
   - `Tier: prototype (approval gates skipped, save-and-summarize, lean artifacts).`

2. **Active agent**: if a single agent role has been adopted in this session, name it. Otherwise print `Active agent: none. Call story-refiner / slice-planner / xp-pair-programmer / diff-reviewer / release-captain / incident-responder / code-inspector / docs-maintainer to start.`

3. **Loaded artifacts**: list any of these that the current session has loaded:
   - story (`stories/STORY-NNN-*.md`)
   - research (`research/RESEARCH-NNN-*.md`)
   - plan (`plans/PLAN-NNN-*.md`)
   - audit (`audits/AUDIT-*.md`)
   - review (`reviews/REVIEW-NNN-*.md`)
   - incident (`incidents/INC-*.md`)

4. **Recent telemetry**: select the current host's local log:
   `.claude/usage.jsonl` for Claude or `.codex/usage.jsonl` for Codex. If the
   host is unknown, use whichever exists; if both exist, combine and select
   the five newest events by `timestamp`. Print the source with each summary:

   ```text
   <timestamp>  <source>  <agent>  turns=<N>
   ```

   Never print raw JSON or any host-supplied identifiers. If the file does not exist, print: `Telemetry: no runs recorded yet: deploy with the harness enabled and run an agent.`

5. **Read budget**: if the active agent declares a read cap, report the count consumed in the current session against the cap (e.g. `Read budget: 12 / 20 (60%)`).

Keep the output tight: one line per item, no markdown headings, no commentary. The user runs `/status` to scan, not to read.

$ARGUMENTS
