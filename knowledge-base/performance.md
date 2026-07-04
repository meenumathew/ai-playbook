---
id: performance
size: medium
tldr: No premature optimisation; flag N+1, nested loops, and obvious inefficiency in review without a profiler.
load_when: hot path, performance, N+1, caching, data-heavy, collections, latency, DB loop, API loop, profiling
audience: all
canonical_for: performance review checklist, data structure selection, when-to-care thresholds
cross_refs: design-patterns.md, observability.md
verified: 2026-05-19
---

# Performance Awareness

Never optimize without measurement: but recognize obvious inefficiency in review without needing a profiler.

## Agent Use

- **Read first:** When to Care, Common Pitfalls, Data Structure Selection, Performance Review Checklist.
- **Load deeper only on trigger:** profiling, caching, memory, and streaming guidance.

---

## When to Care

| Data scale | Agent action |
|-----------|-------------|
| < 100 items | Clarity wins: don't optimise |
| 100–10,000 | Flag nested loops and repeated lookups |
| 10,000–1M | Algorithm choice matters: profile hot paths |
| > 1M | Design for performance from the start: streaming, indexing, batching |

If the expected data scale is unknown, ask before choosing an approach.

---

## Big-O Quick Reference

| Complexity | Example | Agent action |
|-----------|---------|-------------|
| O(1) | Dict/set lookup, array index |: |
| O(log n) | Binary search, balanced tree |: |
| O(n) | Single pass over a list | Fine for most cases |
| O(n log n) | Sorting | Fine for most cases |
| O(n^2) | Nested loop over same collection | **Flag in review if n > 100** |
| O(n³) | Triple nested loop | **Almost always wrong: flag** |
| O(2ⁿ) | Brute-force subsets | Only acceptable for tiny n with no alternative |

**AI agents frequently generate O(n²) code.** Flag nested loops and `in` checks on lists during review.

---

## Common Pitfalls

| Pitfall | How to detect | Agent action |
|---------|--------------|-------------|
| **N+1 queries** | Loop contains a DB call, API call, or file read | Batch into one query, then group in memory |
| **Quadratic membership** | `in` check on a `list` inside a loop | Convert to `set` or `dict` before the loop |
| **String concat in loop** | `result += s` in a loop | Use `"".join()` or a builder |
| **Unbounded collection** | `.all()` or full materialisation without known size | Paginate, stream, or use generators |
| **Redundant re-computation** | Same value computed multiple times in a loop | Compute once before the loop, or cache |
| **Repeated sorting** | Sort called inside a loop or after every insert | Sort once, or use `heapq` / `SortedSet` |

---

## Data Structure Selection

| Need | Use | Not |
|------|-----|-----|
| Fast lookup by key | `dict` / `Map` | Scanning a list |
| Fast membership test | `set` / `Set` | `in` on a list |
| Ordered unique items | `sorted()` + `set`, or `SortedSet` | Repeated sort-and-deduplicate |
| FIFO queue | `collections.deque` | `list.pop(0)` (O(n)) |
| Priority queue | `heapq` | Sorting after every insert |
| Counted items | `collections.Counter` | Manual dict incrementing |

Choose the structure that makes the **dominant operation** cheap.

---

## Memory Awareness

| Pattern | When to prefer |
|---------|---------------|
| **Generator / iterator** | Processing items one at a time: don't need the whole list in memory |
| **Streaming / chunked reads** | Files or API responses larger than available memory |
| **Materialised list** | Need random access, `len()`, or multiple passes |

---

## Caching Rules

| Rule | Agent action |
|------|-------------|
| Cache read-heavy, rarely-changing data | Set TTLs on all entries: unbounded caches are memory leaks |
| Cache at service layer only | Domain objects remain pure (`design-patterns.md` § Architecture Layers) |
| Distributed cache (Redis) only when justified | Only when computation cost > network round-trip cost |
| Can't answer "when does this entry become stale?" | Don't cache it yet |

Never cache mutable business state without an explicit invalidation strategy.

---

## Token and Context Budget

AI-assisted development has a performance dimension too: context windows, tool calls, and model cost. Large prompts can hide important facts through truncation and make workflows expensive.

| Pattern | Agent action |
|---------|-------------|
| Read budget | Start with targeted search and small file sets. If research expands, state your findings and narrow the next read. |
| Context pressure | When a task needs many files, summarise stable findings into an artifact before continuing rather than repeatedly re-reading the same context. |
| Large codebases | Prefer indexes, dependency graphs, test maps, and architecture docs before opening many implementation files. |
| Multi-agent workflows | Reuse artifacts from story-refiner, slice-planner, and xp-pair-programmer instead of restating everything in each step. |
| Cost awareness | For team workflows, track unusually large sessions and split stories when one session becomes too broad to review safely. |

Rule of thumb: if the agent cannot name the relevant files, risks, and next verification step, it needs a narrower slice before more context.

---

## Performance Review Checklist

For diff-reviewer and code-inspector: check on hot paths and data-heavy code:

- [ ] No DB/API calls inside loops (N+1)
- [ ] No `in` checks on lists inside loops: use sets
- [ ] No string concatenation in loops: use `join()`
- [ ] No unbounded collection materialisation
- [ ] Appropriate data structure for the dominant operation
- [ ] Generators used where the code only needs a single pass
- [ ] Sorting happens once, not repeatedly
- [ ] No redundant re-computation

**Scope:** request-path code, collection-processing code, loops whose count depends on input size. Skip: setup, config, CLI parsing, test fixtures.

---

## Profile First Rule

**Never optimise based on intuition.** Measure first:

```bash
python -m cProfile -s cumulative script.py   # profile
uv run pytest --durations=10                  # find slow tests
```

**Exception:** reviewers can flag obvious O(n²) from code structure without profiling.

---

## PERF Annotations

Use `PERF:` annotations (`style-guide.md` § Comments) for performance opportunities not worth fixing now. Always include the expected data scale:

```python
# PERF: linear scan fine for <100 items; revisit if catalog grows beyond 10k
```
