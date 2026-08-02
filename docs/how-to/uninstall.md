# How to uninstall the playbook from a project

Goal: remove every file and setting that `ai-playbook deploy` and `ai-playbook init` wrote into a project, and optionally remove the CLI itself.

If you only need to undo the most recent deploy, run `ai-playbook rollback --tool <tool>` instead: it restores the previous overlay snapshot and keeps the playbook installed. See [CLI Reference § Rollback deployment](../cli-reference.md#rollback-deployment). This guide is for full removal.

## Prerequisites

- Know which tool target the project uses (`claude`, `copilot`, `codex`, `cursor`, or `kiro`). Check `.playbook-version` or run `ai-playbook status --tool <tool>`.
- A clean Git working tree, so every deletion below is reviewable before you commit it.

## What deploy creates

| Surface | Claude | Copilot | Codex | Cursor | Kiro |
|---|---|---|---|---|---|
| Overlay dirs (agents, knowledge base, skills, templates) | `.claude/agents/`, `.claude/knowledge-base/`, `.claude/skills/`, `.claude/templates/` | `.github/agents/`, `.github/knowledge-base/`, `.github/skills/`, `.github/templates/` | `.codex/agents/`, `.codex/knowledge-base/`, `.agents/skills/`, `.codex/templates/` | `.cursor/agents/`, `.cursor/knowledge-base/`, `.cursor/skills/`, `.cursor/templates/` | `.kiro/agents/`, `.kiro/knowledge-base/`, `.kiro/skills/`, `.kiro/templates/` |
| Commands | `.claude/commands/` | `.github/prompts/` | none | `.cursor/commands/` | none |
| Rules file | `CLAUDE.md` | `.github/copilot-instructions.md` | `AGENTS.md` | `.cursor/rules/ai-playbook.mdc` | `.kiro/steering/rules.md` |
| MCP config | `.claude/settings.json` | `.vscode/mcp.json` | `.codex/config.toml` | `.cursor/mcp.json` | `.kiro/settings/mcp.json` |

Every tool also gets the same tool-independent surfaces:

- Harness files: `Makefile`, `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `.github/workflows/security.yml`, `.github/dependabot.yml`, `harness/check-teachback.sh`, `harness/telemetry.sh`, `harness/read-budget.sh`, `harness/settings.example.json`.
- Deployment record and backups: `.playbook-version`, `.playbook-backup/`.
- A managed `.gitignore` block (if you ran `ai-playbook artifact-policy local`).
- Claude: a telemetry `Stop` hook entry in `.claude/settings.json`, plus local state in `.claude/usage.jsonl` and `.claude/read-budget/`.
- Codex: a telemetry `SessionEnd` hook entry in `.codex/hooks.json`, plus local state in `.codex/usage.jsonl`.

Two surfaces commonly contain adopter edits: the rules file (`CLAUDE.md` and its per-tool equivalents) and the harness files (`Makefile`, `.pre-commit-config.yaml`, and the CI workflows in particular). **Review those before deleting**: your own additions live in the same files.

## Steps

The examples use the Claude target; substitute paths from the table above for other tools.

### 1. Remove the managed `.gitignore` block

```bash
ai-playbook artifact-policy shared
```

This removes only the playbook-managed block (between `# ai-playbook artifacts (managed)` and `# end ai-playbook artifacts`) and preserves the rest of `.gitignore`. If you never ran `artifact-policy local`, the command reports there is nothing to remove.

### 2. Remove telemetry hooks and local state

```bash
ai-playbook telemetry disable --tool claude
ai-playbook telemetry disable --tool codex
```

Run the command for each tool used by the project. It removes only the playbook's `Stop` or `SessionEnd` entry and preserves other hooks and settings. Then delete the privacy-minimal local aggregates if you do not want to keep them:

```bash
rm -f .claude/usage.jsonl .claude/usage-*.jsonl .claude/usage-*.jsonl.gz
rm -f .codex/usage.jsonl .codex/usage-*.jsonl .codex/usage-*.jsonl.gz
rm -rf .claude/read-budget/
```

### 3. Remove the MCP server entry

Deploy writes an MCP server entry only when `.ai-playbook.toml` sets `[issue-tracker] provider = "jira"`. If your MCP config file (see the table above) contains a playbook-added server, remove that entry by hand and keep the rest of the file. If the file contains nothing else your team added, delete the file.

### 4. Delete the overlay directories, commands, and rules file

Review the rules file first: teams often append project rules to the deployed `CLAUDE.md`. Move anything you wrote yourself to a new home before deleting.

```bash
rm -rf .claude/agents .claude/knowledge-base .claude/skills .claude/templates .claude/commands
rm CLAUDE.md
```

### 5. Delete the harness files

Same caution: these are starter copies your team may have extended, and the `Makefile` and `.github/workflows/ci.yml` in particular often carry project-specific targets and steps. Review each file, keep what you own, then delete the rest:

```bash
rm -f Makefile .pre-commit-config.yaml
rm -f .github/workflows/ci.yml .github/workflows/security.yml .github/dependabot.yml
rm -rf harness/
```

If pre-commit hooks were installed, also run `pre-commit uninstall` before deleting `.pre-commit-config.yaml`, or reinstall against your own config afterwards.

### 6. Delete the deployment record and backups

```bash
rm -f .playbook-version
rm -rf .playbook-backup/
```

### 7. Decide what happens to workflow artifacts

`ai-playbook init` created `stories/`, `research/`, `plans/`, `audits/`, `reviews/`, and `incidents/`, plus a starter `.ai-playbook.toml`. The artifact directories hold your team's work, not playbook content: keep them, archive them, or delete them deliberately. Delete `.ai-playbook.toml` (and any local pack directories it references) only if nothing else consumes them.

### 8. Uninstall the CLI (optional)

The steps above clean one project. The CLI itself is installed per machine:

```bash
uv tool uninstall ai-playbook
# or: pipx uninstall ai-playbook
# or: pip uninstall ai-playbook
```

### 9. Verify

Before removing the CLI, confirm the project is clean:

```bash
ai-playbook doctor --tool claude   # expect: nothing deployed (exit code 1)
git status                         # expect: only the deletions you made above
```

Review the diff, then commit the removal as one change.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `doctor` still reports a deployment | `.playbook-version` still present | Delete it (step 6) and rerun `doctor` |
| A tool hook file changed unexpectedly | `telemetry disable` removed the selected playbook hook entry | Expected: review the diff and commit |
| Pre-commit fails after removal | Hooks still installed for the deleted config | Run `pre-commit uninstall`, or point pre-commit at your own config |
| `.gitignore` still lists `stories/` | Managed block was edited by hand and lost its markers | Delete the playbook lines from `.gitignore` manually |

## Related Docs

- [CLI Reference § Rollback deployment](../cli-reference.md#rollback-deployment): the lighter alternative that keeps the playbook installed.
- [CLI Reference § Deploy agents](../cli-reference.md#deploy-agents): the authoritative list of what deploy writes.
- [CLI Reference § Manage local telemetry hooks](../cli-reference.md#manage-local-telemetry-hooks): details of the hooks that step 2 removes.
- [Known Limitations](../limitations.md): copy-based deploy drift, the reason `.playbook-version` exists.
