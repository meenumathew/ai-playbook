# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly.

**Do not open a public issue with vulnerability details, proof-of-concept payloads, secrets, or exploit steps.**

Use GitHub's private [Security Advisories](https://docs.github.com/en/code-security/security-advisories/repository-security-advisories/creating-a-repository-security-advisory) feature. If private advisories are unavailable, open a public issue that asks the maintainer to provide a private reporting channel, but do not include technical details until that private channel exists.

## Scope

This project has two security-relevant surfaces:

- The **Python CLI runtime** deploys local markdown/config files. It does not ask for, store, or transmit provider credentials, and it does not call tracker, notifier, host, or model APIs during deploy, diff, doctor, status, or rollback commands.
- The **deployed playbook content** is a set of markdown skill contracts for the user's AI tool. Those contracts may instruct the tool to use user-configured MCP servers, provider CLIs/APIs, notifier webhooks, or optional eval judge workflows. Credentials for those integrations stay outside the CLI and are configured by the adopter.

The CLI does not execute arbitrary code from agent markdown files.

## Threat Model

This threat model scopes reports: what counts as a vulnerability vs. an enhancement.

## Standards Alignment

This repository uses three security checklists as review inputs:

- **OWASP secure coding:** validate all config and path input at the CLI boundary, use structured parsers for TOML/JSON, refuse path traversal and symlink writes, avoid shell execution in runtime code, keep `.env` files ignored, and run secret, dependency, static-analysis, type, lint, and test gates in CI.
- **OWASP Top 10 for LLM Applications:** treat issue text, PR descriptions, pasted logs, pack content, and model output as untrusted data; defend against prompt injection, system prompt disclosure, sensitive information disclosure, supply-chain prompt tampering, excessive agency, and unbounded consumption through agent instructions, approval gates, read budgets, drift evals, workflow timeouts, and deployment drift checks.
- **OpenSSF Scorecard:** run Scorecard on push, branch-protection updates, weekly schedule, and manual dispatch; upload SARIF; pin GitHub Actions by full SHA; use least-privilege workflow permissions; run CodeQL, Dependabot, secret scanning, dependency scanning, release provenance, SBOM generation, and Sigstore signing.

Host-side controls such as branch protection, required reviews, and repository rulesets are part of the OpenSSF Scorecard posture but are configured in GitHub, not in this repository.

### In-scope attacks (security triage)

| Attack | Asset at risk | Defense in place |
|--------|---------------|------------------|
| **CLI path traversal**: `deploy --target` writes outside the intended directory | User filesystem | `paths.py` + `fs.py` enforce that writes resolve under the resolved project root; backup/restore preserve permissions |
| **Malicious pack content**: third-party pack overrides core agents with hostile prompts | AI tool behaviour, downstream code | Override warnings on deploy, `doctor` reports overlays, pack paths must stay inside the adopter repo, packs are UTF-8 text overlays with no code execution at deploy time, users opt in via `.ai-playbook.toml` |
| **Supply chain compromise**: a transitive dependency ships malicious code | Build & runtime | This-repo posture (does not transfer automatically to adopters): SHA-pinned GitHub Actions and SHA-pinned pre-commit `rev:` entries (Dependabot updates both weekly), `pip-audit --strict` and Bandit on every PR *and* every release tag, CodeQL SAST on push/PR/cron, Sigstore signing + SLSA build provenance on release artifacts, CycloneDX SBOM attached to every GitHub release, PyPI publishing via Trusted Publishing (no API tokens). **Adopter posture:** the deployed `.pre-commit-config.yaml` ships gitleaks + detect-private-key; `harness/ci.yml` runs `make quality` which the project owns; `harness/security.yml` is a drop-in template that adds CodeQL, Scorecard, gitleaks, and Dependency Review with the same SHA pins. **Artifact integrity ≠ dependency-resolution integrity:** Sigstore/SLSA/SBOM authenticate the wheel that PyPI serves; they do not protect resolution of transitive dependencies at install time: that is mitigated by `pip-audit` in CI and Dependabot, not by signing. |
| **Prompt injection via pasted content**: issue tracker text or pasted logs hijack agent behaviour | AI tool behaviour, code modifications | Documented in `knowledge-base/security.md` § Prompt Injection: instruction-boundary delimiters, conflict flagging, agent file tampering checks, untrusted-input rule in `CLAUDE.md` |
| **Secret leakage in commits or logs**: accidentally committed credentials | User credentials | Gitleaks + detect-private-key in the deployed pre-commit config; CodeQL SAST in CI; `never log str(e)` rule; CWE-209 error response pattern |
| **System prompt leakage** under social engineering | Agent integrity | `knowledge-base/security.md` § System Prompt Disclosure: decline verbatim, link to public files |
| **Unbounded resource consumption**: runaway agent loops | User compute/cost | Agent prompts enforce per-agent read budgets (CLAUDE.md § Shared Rules § Read budget); `knowledge-base/security.md` § Resource Consumption Limits documents cost/token caps, tool-call circuit breakers, and recursion limits for adopters to wire into AI tool hooks/settings |
| **Tampering with deployed agent files** outside version control | AI tool behaviour | `doctor` command detects drift; `diff` shows changes; agent files are git-tracked |

### Out of scope (not triaged as security)

- **Bugs in user-authored agent prompts**: the playbook ships a vocabulary, not a guarantee. If a user writes an agent that does something risky, that is a workflow concern.
- **Compromise of the user's AI tool itself** (Claude Code, Copilot, Kiro): defense is the vendor's responsibility.
- **Network-level attacks on PyPI / GitHub / model APIs**: handled by upstream providers.
- **Local privilege escalation**: the CLI runs as the invoking user; the project does not defend against an attacker who already has shell access.
- **Cost overruns from legitimate use**: the consumption limits are guardrails, not guarantees; users are responsible for their model API spend.

## Supported Versions

| Version | Supported |
|---------|-----------|
| 1.x     | Yes       |
| 0.x     | No (pre-release; upgrade to 1.x) |

## Response

The maintainer aims to acknowledge reports within 48 hours and provide a fix or mitigation plan within 7 days for confirmed vulnerabilities. Fixes ship as patch releases (`1.x.y`) with a security advisory on GitHub.

A confirmed vulnerability can override the [deprecation cycle](docs/deprecation-policy.md): security fixes may remove or change a covered surface in a single release without the normal warning window. The security advisory and `CHANGELOG.md` record the skip.

### Security release path

A security release follows the [`RELEASING.md`](RELEASING.md) runbook with two adjustments:

1. **Compressed pre-release checklist.** The `## Pre-release checklist` is reduced to the items needed to prove correctness; the rest can defer to a follow-up patch within 7 days. The compressed list lives in [`RELEASING.md`](RELEASING.md) under "Security release path (compressed checklist)".
2. **Coordinated disclosure.** The advisory is drafted in a private GitHub Security Advisory before the patch ships, then published the moment the patched wheel lands on PyPI. Reporters who chose private disclosure are credited unless they opt out.

For embargoed vulnerabilities (third-party report with a coordinated disclosure window):

- Develop the fix in a private fork or a private GitHub branch.
- Do not push the fix to a public branch until the embargo window opens.
- The release tag and the advisory go live in the same minute: never tag-then-publish-then-advisory.

If the vulnerability requires changing a covered surface (e.g. removing a deployed-file path) and there is no time for a deprecation cycle, file a same-day ADR explaining the skip per [`docs/deprecation-policy.md`](docs/deprecation-policy.md) § Skipping the cycle. The ADR is the durable record that adopters can search later.
