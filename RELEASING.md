# Releasing

How to cut a new version of ai-playbook.

## Pre-release checklist

1. All CI checks pass on `main`
2. `CHANGELOG.md` has an `[Unreleased]` section with all changes since last release; deprecations listed under `### Deprecated` per [`docs/deprecation-policy.md`](docs/deprecation-policy.md)
3. No open issues tagged `blocker`
4. Coverage gate green (`uv run pytest --cov=src --cov-fail-under=95`)
5. Any breaking change to a covered surface (CLI, agent IDs, config schema, KB paths, deployment layout) has gone through the deprecation cycle described in [`docs/deprecation-policy.md`](docs/deprecation-policy.md), or is justified by an ADR that explicitly skips the cycle
6. If testing against a project deployed with the previous version, `ai-playbook upgrade-check --tool claude` exits non-zero before redeploy and `0` after the new wheel deploys
7. Manually dispatch the eval-drift workflow (Actions tab, "Eval drift", Run workflow) and confirm it is green before tagging: the LLM judge must pass every committed baseline and fail every negative control. The workflow runs only on `workflow_dispatch` by default (it bills against `ANTHROPIC_API_KEY`); a maintainer who prefers automatic weekly runs can uncomment the `schedule:` cron block in `.github/workflows/eval-drift.yml` once the secret is configured

## Steps

```bash
# 1. Start a release branch from the remote default branch
git fetch origin main
git switch -c release/vX.Y.Z origin/main

# 2. Move unreleased changes to a versioned section
# Edit CHANGELOG.md: rename [Unreleased] contents to [X.Y.Z] - YYYY-MM-DD

# 3. Bump version in pyproject.toml
# Edit: version = "X.Y.Z"

# 4. Commit the release
git add CHANGELOG.md pyproject.toml
git commit -m "chore(release): X.Y.Z"   # exact subject auto-release.yml expects (no v prefix)

# 5. Build locally before publishing a tag
rm -rf dist/
uv build
uvx twine==6.2.0 check dist/*

# 6. Verify the built wheel installs and deploys cleanly (clean venv)
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

# 7. Push the release branch, open a release PR, and merge it through normal
# CI, review, and approval gates. Do not push the release commit to main.
git push -u origin release/vX.Y.Z

# 8. Tag only the merged remote default-branch commit
git fetch origin main
release_commit=$(git rev-parse origin/main)
git show "$release_commit:pyproject.toml" | grep 'version = "X.Y.Z"'
git tag -a vX.Y.Z "$release_commit" -m "Release vX.Y.Z"

# 9. Push only the tag after approval
git push origin vX.Y.Z
```

The release PR must be merged before tagging. The `release_commit` above is the
verified remote default-branch commit; tagging a local-only release commit can
publish code that does not exist on `main`.

**Skip steps 8–9 when `auto-release.yml` is configured** (release deploy key
present): the workflow tags the merged release PR commit automatically. A
manual tag would race the workflow or fail because the tag already exists.
Steps 8–9 are the fallback for repos running the release process by hand.

## Automated release PR workflow

`.github/workflows/auto-release.yml` applies the same sequence automatically:

1. A non-release push to `main` runs Python Semantic Release 10.6.1 in
   no-commit/no-tag/no-push mode.
2. When releasable conventional commits exist, the workflow commits only the
   generated version and changelog changes to `release/vX.Y.Z` and opens a
   release PR.
3. Normal CI, review, and approval gates run on that PR.
4. When the release PR is merged, the next workflow run verifies that
   `origin/main` is the triggering commit, tags that exact commit, and pushes
   only the tag. The tag starts `release.yml`.

The workflow deliberately does not let semantic-release push a generated
commit straight to `main`; that would bypass the release-PR contract and fail
on protected default branches.

### Auto-release credentials

Configure these repository secrets before relying on the workflow:

- `RELEASE_DEPLOY_KEY` (required): an **unencrypted private SSH key**. Add the
  matching public key at **Settings > Deploy keys** and enable **Allow write
  access**. The key pushes release/maintenance branches and release tags;
  checkout continues to use the read-only workflow token.
- `RELEASE_PR_TOKEN` (optional): a fine-grained personal access token or GitHub
  App installation token with repository **Pull requests: write** and
  **Contents: read**. This lets PR-triggered CI start without manual approval.
  Without it, the workflow uses `GITHUB_TOKEN`; GitHub may put CI for the
  automation-created PR into an approval-required state.

The workflow validates the private-key format, read authentication, and
write access before mutating the remote. It uses GitHub's published Ed25519
host key instead of trusting an unverified `ssh-keyscan` result.

Create a dedicated key pair (do not reuse a personal SSH key):

```bash
release_key_dir="$(mktemp -d)"
ssh-keygen -t ed25519 \
  -C "ai-playbook repository automation" \
  -f "$release_key_dir/release-key" \
  -N ""
gh secret set RELEASE_DEPLOY_KEY \
  --repo meenumathew/ai-playbook \
  < "$release_key_dir/release-key"
ssh-keygen -lf "$release_key_dir/release-key"
ssh-keygen -lf "$release_key_dir/release-key.pub"
```

The two fingerprint commands must print the same SHA256 fingerprint. Copy the
single line from `release-key.pub` into **Settings > Deploy keys > Add deploy
key**, select **Allow write access**, and save. Keep or securely delete the
local private key according to the maintainer's credential policy; never add
either key file to this repository.

### Diagnosing `Permission denied (publickey)`

This error occurs before semantic-release or PyPI:

```text
git@github.com: Permission denied (publickey).
```

Replace `RELEASE_DEPLOY_KEY`, derive its public key with
`ssh-keygen -y -f <private-key-file>`, and register that exact public key under
**Settings > Deploy keys** with **Allow write access** enabled. A private key
whose public half is missing, revoked, attached to another repository, or
read-only cannot create the release branch or tag. Until a `v*` tag is pushed,
`release.yml` does not run and PyPI Trusted Publishing is never reached.

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
3. In the GitHub repo, create an environment named `pypi` (Settings → Environments). Treat the next two settings as **required**, not optional: a pushed `v*` tag is the sole trigger for a signed, irreversible PyPI publish, so anyone with write access can otherwise release.
   - On the `pypi` environment: add **required reviewers** and restrict the environment to tag refs (`v*`).
   - Under Settings → Rules → Rulesets: add a **tag ruleset for `v*`** restricting who can create tags (maintainers only).

After that, the only step to release is pushing a tag: no tokens, no `.pypirc`, no manual `uv publish`. The two settings above are the human gate in front of that tag.

### Cutting a release

```bash
git fetch origin main
release_commit="$(git rev-parse origin/main)"
git tag -a vX.Y.Z "$release_commit" -m "Release vX.Y.Z"
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
- The Sigstore signature that was created at publish time. It stays valid for the wheel even after yanking.
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
2. Leave `pyproject.toml` at the released version. Do **not** pre-bump it to the next planned version: `auto-release.yml` treats any main-branch commit that changes the version (while no matching tag exists) as a merged release PR, tags it, and triggers a real PyPI publish of unreleased code. PyPI is append-only; the only recovery is yank-and-burn the version number. semantic-release computes the next version from commit history when it prepares the next release PR.
