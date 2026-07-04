# How To Set Up Your Project Management Tool

## Goal

Configure your AI tool to fetch work items directly from Jira, GitHub Issues/Projects, GitLab Issues, Bitbucket SaaS Issues, or Linear so agents can resolve tracker references without manual paste.

The playbook is project-management-tool agnostic: Jira Stories, GitHub issues or Project items, GitLab issues, Bitbucket issues, Linear issues, and pasted tickets all become provider-neutral work items at the boundary. Agents then write or load a playbook story artifact under `stories/`, with `issue-ref:` preserving the original tracker identity.

## Prerequisites

- AI Playbook deployed: `ai-playbook deploy --agent all --tool <tool>`
- Credentials for your project-management tool or issue tracker, as listed below.

| Tool | Credential |
|---|---|
| Jira | Atlassian account with project access |
| GitHub Issues/Projects | `gh` CLI installed and authenticated (`gh auth login`) |
| GitLab Issues | `glab` CLI authenticated (`glab auth login`), or GitLab MCP configured |
| Bitbucket SaaS | Bearer token with issue read access, exported as `BITBUCKET_TOKEN` |
| Linear | Linear API key, or Linear MCP configured |

## Steps

### Option A: Jira (Atlassian MCP)

`ai-playbook deploy` configures the Atlassian MCP automatically **when `.ai-playbook.toml` declares `[issue-tracker]` with `provider = "jira"`**. Set that first (see the config example below), then deploy. Without a declared provider, deploy skips MCP setup entirely: the playbook never pushes a tracker-specific server into a project that did not ask for it.

```toml
[issue-tracker]
provider = "jira"
```

| Tool | Config location | Auth |
|------|-----------------|------|
| Claude | `.claude/settings.json` | Browser prompt on first fetch |
| Copilot | `.vscode/mcp.json` | Browser prompt on first fetch |
| Cursor | `.cursor/mcp.json` | Browser prompt on first fetch |
| Kiro | `.kiro/settings/mcp.json` | Browser prompt on first fetch |

To add the MCP entry manually:

```bash
claude mcp add --transport http atlassian https://mcp.atlassian.com/mcp
```

To skip MCP during deploy: `ai-playbook deploy --agent all --tool claude --no-mcp`.

### Option B: GitHub Issues/Projects

You need no setup. Agents call `gh issue view` directly for issues. For GitHub Projects, provide the linked issue reference when possible; project fields are metadata, while the linked issue is the stable implementation work item.

Verify auth:

```bash
gh auth status
```

If unauthenticated: `gh auth login`.

### Option C: GitLab Issues

Authenticate `glab`. Agents call `glab issue view <iid>` directly. You need no MCP wiring.

```bash
glab auth status
```

For self-hosted GitLab:

```bash
glab auth login --hostname gitlab.example.com
```

For token-only environments, configure GitLab MCP or authenticate `glab` outside the agent process. See `skills/issue-fetch/SKILL.md § GitLab Adapter`.

### Option D: Bitbucket SaaS Issues

Bitbucket SaaS has no first-party CLI for issues. The `issue-fetch` skill calls the [REST v2.0 API](https://developer.atlassian.com/cloud/bitbucket/rest/api-group-issue-tracker/) with a bearer token that has issue read access:

```bash
export BITBUCKET_TOKEN=xxxxxxxxxxxx
```

Bitbucket Server / Data Center is not supported: see [ADR-0001](../adr/0001-bitbucket-server-not-supported.md).

### Option E: Linear

Configure the Linear MCP, or set:

```bash
export LINEAR_API_KEY=lin_api_xxxxx
```

For full MCP setup, see [Linear MCP docs](https://linear.app/docs/mcp).

### Option F: No Tool (Manual Paste)

You need no configuration. When an agent asks for work item details, paste:

- Title
- Description
- Acceptance criteria
- Relevant comments

This is also the automatic fallback when any MCP or CLI fetch fails.

### Verify

```text
Use story-refiner: PROJ-1234
```

The agent should fetch and display the work item title and description. If it asks you to paste instead, the integration is not configured correctly.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not fetch issue` | MCP not configured or auth expired | Re-run `ai-playbook deploy` or re-authenticate |
| Browser prompt loops | Atlassian session expired | Sign out and back in to Atlassian in the browser |
| `gh: command not found` | GitHub CLI not installed | Install from <https://cli.github.com/> |
| `glab: command not found` | GitLab CLI not installed | Install from <https://gitlab.com/gitlab-org/cli> |
| Bitbucket returns 401 | Token missing, expired, or missing issue read access | Regenerate the token with issue read access |
| Linear returns 401 | API key invalid or expired | Regenerate at Linear Settings → API |

## Related

- [CLI Reference § Deploy](../cli-reference.md#deploy-agents): `--no-mcp` flag and MCP config locations
- [Invoke Agents](invoke-agents.md): using work item and tracker references when invoking agents
