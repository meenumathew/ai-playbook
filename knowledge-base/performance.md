---
id: performance
size: medium
tldr: No premature optimisation; flag N+1, nested loops, and obvious inefficiency in review without a profiler.
load_when: hot path, performance, N+1, caching, data-heavy, collections, latency, DB loop, API loop, profiling
audience: all
canonical_for: performance review checklist, data structure selection, when-to-care thresholds
cross_refs: design-patterns.md, observability.md
verified: 2026-07-17
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

**AI agents frequently generate O(n^2) code.** Flag nested loops over the same collection when n can exceed 100, and `in` checks on lists inside loops; triple-nested loops are almost always wrong.

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

Choose the structure that makes the **dominant operation** cheap. Prefer generators/streaming for single-pass or larger-than-memory data; materialise a list only for random access, `len()`, or multiple passes.

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

Context is a performance surface too: read budgets and loading discipline are canonical in `CLAUDE.md` (§ Shared Rules, § Knowledge Base) and `philosophy.md` § Context Engineering. Rule of thumb: if the agent cannot name the relevant files, risks, and next verification step, it needs a narrower slice before more context.

---

## Performance Review Checklist

For diff-reviewer and code-inspector: on hot paths and data-heavy code, verify every § Common Pitfalls row plus data-structure fit for the dominant operation (§ Data Structure Selection).

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

---

## Load & Stress Testing

Static review (the checklist above) catches algorithmic and query problems in the code. It does not tell you whether the system holds up under real concurrency, so a data-heavy, high-throughput, or hot-path change needs a load test *before* release, not a production surprise.

**When to load-test.** Plan one (at slice-planner time) when the change touches: a request path expected to see concurrency, a queue/stream consumer, a batch job over large data, a new external-service dependency on a hot path, or anything with a stated latency/throughput SLO. Skip it for isolated, low-traffic, or internal-only changes.

**Set a target first.** A load test with no target only produces numbers. Before running, state the expected peak (requests/sec, messages/sec, concurrent users), the acceptable p95/p99 latency, and the error-rate ceiling. Without a target you cannot say "pass" or "fail".

**What to measure.** Throughput at the target rate, latency distribution (p50/p95/p99, not just mean), error rate under load, and resource saturation (CPU, memory, connection-pool, DB/queue depth): the saturation point matters more than the average.

**Test shapes.** *Load*: steady expected peak. *Stress*: ramp past the peak to find the breaking point. *Soak*: sustained load over hours to surface leaks and slow degradation. *Spike*: sudden burst to test elasticity and backpressure.

**Tools are a detail, not the point.** k6, Locust, JMeter, or Gatling all work; pick whatever the team already runs. State the tool in the plan; keep the scenario in the repo so it reruns.

**Where it fits.** slice-planner adds a load-test task when the performance gate fires; release-captain confirms the target was met before cutover on performance-sensitive changes. A failing load test is a release blocker, not a nice-to-have.
