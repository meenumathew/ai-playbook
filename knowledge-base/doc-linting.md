---
id: doc-linting
size: medium
tldr: Docs are code; Vale + markdownlint + lychee; fix, do not suppress.
load_when: docs, vale, markdownlint, lychee, doc lint fail, Diataxis
audience: docs-maintainer, diff-reviewer
canonical_for: doc lint tool stack, doc lint scope by file type
cross_refs: style-guide.md
verified: 2026-07-02
---

# Documentation Linting

Docs are code. Lint them like code.

## Agent Use

- **Read first:** Tool Stack, Running Locally, Scope by File Type, When docs-maintainer Writes.
- **Load deeper only on trigger:** adding new Vale rules or changing Diataxis voice checks.

---

## Tool Stack

| Tool | What it checks | Config file |
|------|---------------|-------------|
| **Vale** | Style: passive voice, weasel words, readability, Diataxis quadrant voice | `.vale.ini` |
| **markdownlint** | Format: heading levels, blank lines, code block labels, list spacing | `.markdownlint.jsonc` |
| **lychee** | Links: broken cross-references between markdown files | `.lychee.toml` |

Vale and markdownlint run in this repo's docs-quality CI job. All three tools
are fast enough for local hooks. Wire them into `make lint` or your chosen hook
framework.

---

## Running Locally

```bash
# Style check
uv run pre-commit run vale --all-files

# Format check
markdownlint-cli2 "docs/**/*.md"

# Link check (internal only, no network)
lychee --no-progress --offline "docs/**/*.md"

# Fix auto-fixable format issues
markdownlint-cli2 "docs/**/*.md" --fix
```

### Inspecting the active rule set

When a check surprises you, ask Vale what rules apply before arguing with the
alert:

```bash
# Print the resolved config (all active checks across all sections)
vale ls-config

# Show every alert for one file with the rule name attached
vale --output=line <file.md>
```

`ls-config` is the fastest way to confirm whether a rule is active, off,
or running at a different severity than you expected. Useful when an adopter
inherits the config and wants to know what their gate actually enforces.

---

## Reference Notes

The sections below are for maintaining the documentation lint setup. Load only when changing rules or fixing documentation-lint failures.

### Vale Rules

#### Playbook rules (all markdown)

<!-- vale Playbook.Contractions = NO -->
<!-- vale Playbook.ProfessionalTone = NO -->
<!-- vale Playbook.DisplayNames = NO -->
| Rule | What it catches |
|------|----------------|
| `PassiveVoice` | `is being`, `was performed`, `has been`: prefer active voice |
| `Weasels` | `obviously`, `simply`, `basically`, `easily`: be specific |
| `NoEmDash` | Em dashes: rewrite with natural punctuation or split the sentence |
| `Headings` | Inconsistent heading capitalization |
| `Acronyms` | Acronyms used without first-use expansion |
| `Contractions` | Casual contractions such as `don't`, `can't`, `won't`: warning only, because quoted examples can be intentional |
| `FleschKincaid` | Adopter-facing docs with a Flesch-Kincaid grade level greater than 12: warning only, because technical terms can skew the score |
| `ProfessionalTone` | Casual or unclear phrases such as `stuff`, `gotchas`, `hardcoding fine`, `the AI did it`: blocking |
| `DisplayNames` | Unprofessional role labels in frontmatter `name:` or `description:` values, such as `ninja` or `rockstar`: blocking |
<!-- vale Playbook.Contractions = YES -->
<!-- vale Playbook.ProfessionalTone = YES -->
<!-- vale Playbook.DisplayNames = YES -->

These rules apply to maintained Playbook prose, including root docs, `docs/`,
`knowledge-base/`, `agents/`, `commands/`, and `skills/`. Eval fixtures stay
excluded because they intentionally contain adversarial and quoted language.

The readability metric is opt-in for adopter-facing docs (`docs/**/*.md`,
`README.md`, and `CONTRIBUTING.md`). Agent files, skills, templates, knowledge-base files, evals, and changelogs keep it off because dense operational terms,
placeholders, fixtures, and release-note bullets create noisy scores.

Agent files still relax passive-voice and Diataxis rules because they use
imperative operational wording. Frontmatter must preserve professional display names and descriptions. Preserve stable agent `id:` values unless a migration
plan updates commands, evals, docs, and tests together.

#### Diataxis rules (docs/ only)

<!-- vale Google.We = NO -->
| Rule | Applied to | What it catches |
|------|-----------|----------------|
| `TutorialVoice` | `docs/getting-started.md`, tutorials | Theory language such as the reason is or under the hood in step-by-step content |
| `HowToVoice` | `docs/how-to/` | Teaching language such as learn this first or understand why in task-focused content |
| `ReferenceVoice` | `docs/cli-reference.md`, `docs/limitations.md` | Advisory language such as you should or we recommend in factual content |
| `ExplanationVoice` | `docs/architecture.md`, `docs/references.md` | Step-by-step commands ("run the following") in conceptual content |
<!-- vale Google.We = YES -->

---

### Adding New Rules

#### Custom Vale rule

Create a YAML file in `.vale/styles/Playbook/` or `.vale/styles/Diataxis/`:

```yaml
extends: existence
message: "Describe the problem with '%s'."
level: warning
tokens:
  - 'pattern to match'
```

#### Accepted vocabulary

Add domain terms to `.vale/styles/config/vocabularies/Playbook/accept.txt` so they do not trigger spelling warnings.

#### Rejected vocabulary

Add terms to `.vale/styles/config/vocabularies/Playbook/reject.txt` to flag them as errors (inclusive language violations, deprecated terms).

---

### Scope by File Type

| File pattern | Style enforced | Diataxis enforced |
|-------------|---------------|-------------------|
| `docs/**/*.md` | Yes | Yes (per quadrant) |
| `knowledge-base/**/*.md` | Yes | Explanation only |
| `CLAUDE.md`, `README.md` | Yes | No (not a quadrant doc) |
| `agents/**/*.md` | Yes | No (instructional) |
| `templates/**/*.md` | Relaxed | No |
| `evals/**/*.md` | No | No |

---

### When docs-maintainer Writes

After saving any doc, the agent runs:

1. `vale <file>`: must pass with 0 errors; review warnings before finalizing
2. `markdownlint-cli2 <file>`: must pass with 0 errors

If either command fails, fix before reporting complete.

---

### Installation

```bash
# macOS
brew install vale markdownlint-cli2 lychee

# Optional pre-commit hooks
pre-commit install
```
