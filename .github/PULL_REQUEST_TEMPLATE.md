## Summary

<!-- What changed and why? Keep it brief: 1-3 bullet points. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Agent behavior change
- [ ] Knowledge base update
- [ ] CLI change

## Checklist

- [ ] Tests pass (`uv run pytest tests/ -v`)
- [ ] Lint clean (`uv run ruff check src/ tests/ evals/`)
- [ ] Format clean (`uv run ruff format --check src/ tests/ evals/`)
- [ ] Type check passes (`uv run pyright`)
- [ ] Eval structure valid (`uv run python evals/run_eval.py check-structure`)
- [ ] Updated evals if agent behavior changed
- [ ] Updated docs if user-facing behavior changed

## Test plan

<!-- How can a reviewer verify this works? -->
