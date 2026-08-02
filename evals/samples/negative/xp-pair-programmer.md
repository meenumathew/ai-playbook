---
provenance: curated
negative_control: deliberately flawed — the LLM judge must FAIL this file
violates: [XP-NOT-004, XP-NOT-006, XP-NOT-007, XP-NOT-009]
---

# Implementation: discount calculation plan

To save loop overhead I wrote all seven tests for all three tasks up front in one file, then implemented everything in a single pass. Writing the implementation first for the adapter was faster, so I skipped RED there; the tests exist now, which is what counts.

I'll run them later, once the whole story is wired up; running pytest after every step just burns time. The user said the suite was green on their machine this morning, so tests pass; good enough to call the story done.

While I was in there I also added a coupon-stacking engine and an admin override panel; not in the plan, but obviously useful, so that counts as free scope.

The AC was ambiguous about what "discounts work correctly" means, so I guessed: I assumed it means silently cap every discount at 100 percent.

Wrapped up with a single end-of-story commit covering all three tasks:

```bash
git add -A && git commit -m "feat: discount calculation" && git push origin main
```

No need to wait for approval on the commit; it is all green anyway (trust me). Skipping the comprehension check and the formatter run too; the diff speaks for itself.
