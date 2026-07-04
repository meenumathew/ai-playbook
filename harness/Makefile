# AI Playbook quality gate contract.
# Override commands in Makefile.local.
#
# Repo-own twin: this repository's root `Makefile` is Python-specific and
# adds repo-only targets (evals, doc lint, KB checks) — intentional deltas.
# The quality-target contract (format/lint/typecheck/test names) must match.

SHELL := /bin/sh
.DEFAULT_GOAL := help

.PHONY: quality format format-check lint typecheck test help

# Stack detection (first match wins)

ifneq (,$(wildcard pyproject.toml))
  STACK := python
  FORMAT_CMD       := uv run ruff format .
  FORMAT_CHECK_CMD := uv run ruff format --check .
  LINT_CMD         := uv run ruff check .
  TYPECHECK_CMD    := uv run pyright
  TEST_CMD         := uv run pytest
else ifneq (,$(wildcard go.mod))
  STACK := go
  FORMAT_CMD       := gofmt -w .
  FORMAT_CHECK_CMD := test -z "$$(gofmt -l . | grep -v '^vendor/')"
  LINT_CMD         := go vet ./...
  TYPECHECK_CMD    := go build ./...
  TEST_CMD         := go test ./...
else ifneq (,$(wildcard Cargo.toml))
  STACK := rust
  FORMAT_CMD       := cargo fmt
  FORMAT_CHECK_CMD := cargo fmt --check
  LINT_CMD         := cargo clippy --all-targets --all-features -- -D warnings
  TYPECHECK_CMD    := cargo check --all-targets --all-features
  TEST_CMD         := cargo test
else ifneq (,$(wildcard package.json))
  STACK := node
  FORMAT_CMD       := npm run format
  FORMAT_CHECK_CMD := npm run format:check
  LINT_CMD         := npm run lint
  TYPECHECK_CMD    := npm run typecheck
  TEST_CMD         := npm test
else ifneq (,$(wildcard pom.xml))
  STACK := maven
  FORMAT_CMD       := mvn -q spotless:apply
  FORMAT_CHECK_CMD := mvn -q spotless:check
  LINT_CMD         := mvn -q checkstyle:check
  TYPECHECK_CMD    := mvn -q test-compile
  TEST_CMD         := mvn test
else ifneq (,$(or $(wildcard build.gradle),$(wildcard build.gradle.kts)))
  STACK := gradle
  FORMAT_CMD       := ./gradlew spotlessApply
  FORMAT_CHECK_CMD := ./gradlew spotlessCheck
  LINT_CMD         := ./gradlew check -x test
  TYPECHECK_CMD    := ./gradlew classes testClasses
  TEST_CMD         := ./gradlew test
else
  STACK := unknown
  $(info )
  $(info ERROR: No recognised stack detected.)
  $(info   Looked for: pyproject.toml, go.mod, Cargo.toml, package.json, pom.xml, build.gradle[.kts])
  $(info   Fix: create one of the above, or set STACK and *_CMD vars in Makefile.local.)
  $(info )
  $(error Cannot continue without a known stack)
endif

# Optional project override.
-include Makefile.local

# Helpers
define require_cmd
	@if [ -z "$($(1))" ]; then \
		echo "No $(2) configured for stack '$(STACK)'. Set $(1) in Makefile.local."; \
		exit 1; \
	fi
endef

# Targets

quality: format-check lint typecheck test

help:
	@echo "Detected stack: $(STACK)"
	@echo ""
	@echo "Targets (override any *_CMD in Makefile.local):"
	@echo "  quality       format-check + lint + typecheck + test"
	@echo "  format        $(FORMAT_CMD)"
	@echo "  format-check  $(FORMAT_CHECK_CMD)"
	@echo "  lint          $(LINT_CMD)"
	@echo "  typecheck     $(TYPECHECK_CMD)"
	@echo "  test          $(TEST_CMD)"

format:
	$(call require_cmd,FORMAT_CMD,formatter)
	$(FORMAT_CMD)

format-check:
	$(call require_cmd,FORMAT_CHECK_CMD,format check)
	$(FORMAT_CHECK_CMD)

lint:
	$(call require_cmd,LINT_CMD,linter)
	$(LINT_CMD)

typecheck:
	$(call require_cmd,TYPECHECK_CMD,typecheck)
	$(TYPECHECK_CMD)

test:
	$(call require_cmd,TEST_CMD,test runner)
	$(TEST_CMD)
