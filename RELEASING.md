# Releasing

How to cut a new version of ai-playbook.

## Pre-release checklist

1. All CI checks pass on `main`
2. `CHANGELOG.md` has an `[Unreleased]` section with all changes since last release; deprecations listed under `### Deprecated` per [`docs/deprecation-policy.md`](docs/deprecation-policy.md)
3. No open issues tagged `blocker`
4. Coverage gate green (`uv run pytest --cov=src --cov-fail-under=95`)
5. Any breaking change to a covered surface (CLI, agent IDs, config schema, KB paths, deployment layout) has gone through the deprecation cycle described in [`docs/deprecation-policy.md`](docs/deprecation-policy.md), or is justified by an ADR that explicitly skips the cycle
6. If testing against a project deployed with the previous version, `ai-playbook upgrade-check --tool claude` exits non-zero before redeploy and `0` after the new wheel deploys

## Steps

```bash
# 1. Move unreleased changes to a versioned section
# Edit CHANGELOG.md: rename [Unreleased] contents to [X.Y.Z] - YYYY-MM-DD

# 2. Bump version in pyproject.toml
# Edit: version = "X.Y.Z"

# 3. Commit the release
git add CHANGELOG.md pyproject.toml
git commit -m "chore: release vX.Y.Z"

# 4. Build locally before publishing a tag
rm -rf dist/
uv build
uvx twine==6.2.0 check dist/*

# 5. Verify the built wheel installs and deploys cleanly (clean venv)
venv=$(mktemp -d)/v
uv venv "$venv"
uv pip install --python "$venv/bin/python" dist/ai_playbook-X.Y.Z-py3-none-any.whl
"$venv/bin/ai-playbook" list
target=$(mktemp -d)
"$venv/bin/ai-playbook" deploy --agent all --tool claude -t "$target" --no-mcp
ls "$target/.claude/agents/"   # confirm all 8 agents
ls "$target/.claude/skills/"   # confirm host-adapter is shipped
"$venv/bin/ai-playbook" doctor --tool claude -t "$target"
"$venv/bin/ai-playbook" upgrade-check --tool claude -t "$target"  # exit 0 confirms freshly deployed

# 6. Tag only after local verification
git tag -a vX.Y.Z -m "Release vX.Y.Z"

# 7. Push main and the tag
git push origin main
git push origin vX.Y.Z
```

## Publish to PyPI

Publishing is automated. The `release.yml` workflow runs on every `v*` tag push and:

1. Builds the wheel and sdist
2. Generates a CycloneDX SBOM (`dist/sbom.cdx.json`)
3. Generates SLSA build provenance attestations
4. Signs the distribution artifacts with Sigstore
5. Attaches signed distributions + the CycloneDX SBOM to the GitHub release
6. Publishes to PyPI via [Trusted Publishing](https://docs.pypi.org/trusted-publishers/) after signing succeeds (no API tokens: GitHub OIDC)

### First-time setup only

1. Register PyPI account at https://pypi.org/account/register/
2. Configure Trusted Publishing for the project:
   - Go to https://pypi.org/manage/account/publishing/
   - Click "Add a new pending publisher"
   - PyPI Project Name: `ai-playbook`
   - Owner: `meenumathew`
   - Repository: `ai-playbook`
   - Workflow filename: `release.yml`
   - Environment name: `pypi`
3. In the GitHub repo, create an environment named `pypi` (Settings → Environments). Optionally restrict it to tag pushes.

After that, the only step to release is pushing a tag: no tokens, no `.pypirc`, no manual `uv publish`.

### Cutting a release

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

The workflow handles the rest. Watch it at `github.com/meenumathew/ai-playbook/actions`.

### Verify

```bash
uv tool install ai-playbook==X.Y.Z          # uv-first
# or:  pip install ai-playbook==X.Y.Z       # universal fallback
```

To verify the Sigstore signature on a downloaded wheel:

```bash
uvx sigstore verify identity \
  --bundle ai_playbook-X.Y.Z-py3-none-any.whl.sigstore.json \
  --cert-identity 'https://github.com/meenumathew/ai-playbook/.github/workflows/release.yml@refs/tags/vX.Y.Z' \
  --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
  ai_playbook-X.Y.Z-py3-none-any.whl
```

If the publish fails on a wheel-already-exists error, you cannot re-publish the same version: bump to `X.Y.Z+1` and try again. PyPI versions are immutable by design.

## Post-publish recovery

Once a wheel is on PyPI, you cannot replace it: only ship a follow-up version. The recovery options are ranked by severity.

### Critical bug discovered after publish

Use this path when a release ships and adopters then hit a real defect (broken deploy, crash on common input, regression). Goal: stop new installs of the bad version, ship a fix fast.

1. **Yank the bad release on PyPI.** A yanked version is hidden from the resolver's default selection but stays installable when explicitly pinned. This protects new adopters without breaking anyone who already pinned `==X.Y.Z`.

   Yanking is a PyPI web UI operation; there is no CLI for it (twine supports only `register`, `check`, `upload`). Log in to pypi.org → project page → Manage → Releases → select `X.Y.Z` → **Yank**, and set the reason to `Fix lands in X.Y.(Z+1): see https://github.com/meenumathew/ai-playbook/issues/<id>` so pip's yank warning points adopters at the fix.

2. **Cut the patch.** Follow `## Steps` above with `X.Y.(Z+1)`. CHANGELOG entry under `### Fixed` references the yanked version and the issue. Push the tag: the release workflow runs end-to-end.

3. **Update GitHub release notes.** The yanked release stays visible on GitHub but mark its notes with `**YANKED: install X.Y.(Z+1)**` at the top.

4. **Notify adopters** via the channels listed in `SECURITY.md § Response` if the bug is security-relevant. For functional bugs, the changelog entry is the announcement.

### Security vulnerability discovered after publish

Follow [`SECURITY.md`](SECURITY.md) end-to-end (private advisory, fix in a feature branch, optional embargo). When ready to release, take the **Security release path** below: it skips parts of `## Pre-release checklist` that aren't safe to delay.

### Security release path (compressed checklist)

A security release may compress some pre-release checks because the priority is "ship the fix fast enough that the advisory is useful". Items still required:

- [ ] All tests pass on the security branch
- [ ] The fix is covered by at least one new test that proves the bug is no longer present
- [ ] CHANGELOG.md `### Fixed` (or `### Security`) entry describes the bug abstractly without weaponising the disclosure
- [ ] Coverage gate green
- [ ] Sigstore signature attaches as usual

Items that can be deferred to a follow-up patch (X.Y.Z+1 within 7 days):

- Deprecation-cycle compliance for any covered surface the fix had to touch: record an ADR explicitly skipping the cycle per [`docs/deprecation-policy.md`](docs/deprecation-policy.md)
- Documentation of any new or changed surface: note in CHANGELOG, follow up with full docs in the next non-security release

### Tag handling

Git tags are not deletable from a publish posture: they are a permanent record of "this commit was tagged at this time". Even when a release is yanked from PyPI, the tag stays. **Do not delete or move tags.** If a tag points at a commit you wish you hadn't shipped, the answer is always "ship a higher version", never "rewrite history".

### What you cannot recover

- The wheel that was uploaded. PyPI is append-only by design; the bad bytes are visible to anyone who pins to that version. Yanking hides it from the default resolver but preserves the historical record.
- The Sigstore signature that was minted at publish time. It stays valid for the wheel even after yanking.
- The SLSA build provenance. Same: historical record, not retractable.

## OpenSSF Best Practices Badge

Self-attestation questionnaire: free, ~30 minutes, awards a `passing` / `silver` / `gold` badge.

1. Go to https://www.bestpractices.dev/en/projects/new
2. Sign in with GitHub, point at this repo
3. Walk the questionnaire: most rows already pass thanks to existing CI, SECURITY.md, CONTRIBUTING.md, license, tests
4. Once approved, add the badge to `README.md` next to the existing CI, CodeQL, and OpenSSF Scorecard badges.

## Versioning

Follows [Semantic Versioning](https://semver.org/):

- **PATCH** (1.x.Z): bug fixes, typo corrections, knowledge base clarifications
- **MINOR** (1.Y.0): new agents, new CLI commands, new knowledge base files, new language support
- **MAJOR** (X.0.0): breaking changes to CLI interface, agent file format, or deployment structure

## Post-release

1. Add a fresh `## [Unreleased]` section to `CHANGELOG.md`
2. Bump `pyproject.toml` to the next planned version (e.g., `1.1.0` for the next minor) so unreleased commits build with a forward-looking version
