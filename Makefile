# AI Playbook repository quality gates.

SHELL := /bin/sh
.DEFAULT_GOAL := help

PYTHON_PATHS := src/ tests/ evals/ tools/
SHELL_SCRIPTS := harness/check-teachback.sh harness/telemetry.sh harness/read-budget.sh
# Keep in sync with the shellcheck-py rev in .pre-commit-config.yaml.
SHELLCHECK := uvx --from shellcheck-py==0.11.0.1 shellcheck
PRE_COMMIT := uvx pre-commit==4.3.0

.PHONY: quality quality-no-docs format format-check lint typecheck test test-fast eval-structure eval-calibrate eval-validate shellcheck docs-lint kb-frontmatter claude-md-size agent-size security help

quality: format-check lint typecheck shellcheck docs-lint kb-frontmatter claude-md-size agent-size eval-structure eval-calibrate eval-validate test

# Same as quality minus docs-lint — escape hatch when Vale is not installed.
quality-no-docs: format-check lint typecheck shellcheck kb-frontmatter claude-md-size agent-size eval-structure eval-calibrate eval-validate test

format:
	uv run ruff format $(PYTHON_PATHS)

format-check:
	uv run ruff format --check $(PYTHON_PATHS)

lint:
	uv run ruff check $(PYTHON_PATHS)

typecheck:
	uv run pyright

test:
	uv run pytest tests/ -q --cov=src --cov-fail-under=95

test-fast:
	uv run pytest tests/ -q --no-cov

eval-structure:
	uv run python evals/run_eval.py check-structure

eval-calibrate:
	uv run python evals/run_eval.py calibrate

eval-validate:
	uv run python evals/run_eval.py validate-samples

shellcheck:
	$(SHELLCHECK) $(SHELL_SCRIPTS)

docs-lint:
	$(PRE_COMMIT) run markdownlint-cli2 --all-files
	$(PRE_COMMIT) run vale --all-files

kb-frontmatter:
	uv run python tools/check-kb-frontmatter.py

claude-md-size:
	uv run python tools/check-claude-md-size.py

agent-size:
	uv run python tools/check-agent-size.py

# Mirrors CI's security jobs (same pinned versions) so a contributor can catch
# secret/dependency/SAST findings before pushing. Not part of `quality`:
# pip-audit needs network access, and `quality` stays offline-runnable.
security:
	$(PRE_COMMIT) run detect-private-key --all-files
	$(PRE_COMMIT) run gitleaks --all-files
	uv export --no-hashes --no-dev --no-emit-project > /tmp/runtime-requirements.txt
	uvx pip-audit==2.10.0 --strict --requirement /tmp/runtime-requirements.txt
	uvx bandit==1.9.4 -r src/ -ll -ii
	uvx bandit==1.9.4 -r tests/ evals/ -ll -ii --skip B101

help:
	@echo "AI Playbook repo targets:"
	@echo "  quality         format-check + lint + typecheck + shellcheck + docs-lint + evals + tests"
	@echo "  quality-no-docs quality without docs-lint (when Vale is not installed)"
	@echo "  format          format Python sources, tests, evals, and tools"
	@echo "  format-check    verify Python formatting"
	@echo "  lint            run Ruff lint checks"
	@echo "  typecheck       run Pyright"
	@echo "  test            run pytest with coverage gate"
	@echo "  test-fast       run pytest without coverage"
	@echo "  shellcheck      lint shipped shell harness scripts"
	@echo "  docs-lint       run markdownlint and Vale over docs"
	@echo "  kb-frontmatter  validate KB and skill frontmatter contract"
	@echo "  claude-md-size  enforce CLAUDE.md size budget (RFC-0001)"
	@echo "  agent-size      enforce per-agent-file size budgets (token ratchet)"
	@echo "  security        secret scan + pip-audit + bandit (mirrors CI; needs network)"
	@echo "  eval-structure  verify eval files parse"
	@echo "  eval-calibrate  verify structural eval calibration"
	@echo "  eval-validate   verify committed eval samples"
